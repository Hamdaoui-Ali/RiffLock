"""Key derivation and encrypted key-vault services."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from rifflock.models import KeyVaultRecord
from rifflock.storage import KeyVaultRepository
from rifflock.utils.errors import AuthenticationError, CryptoOperationError

DATA_KEY_LENGTH = 32
SALT_LENGTH = 16
NONCE_LENGTH = 12
VAULT_VERSION = 1
ENCRYPTION_ALGORITHM = "AES-256-GCM"
KDF_ALGORITHM = "Argon2id"

DEFAULT_KDF_PARAMETERS = {
    "time_cost": 3,
    "memory_cost": 65536,
    "parallelism": 4,
    "hash_len": 32,
}


@dataclass(frozen=True)
class KeyVaultBundle:
    """In-memory result for a newly wrapped data key."""

    data_key: bytes
    record: KeyVaultRecord


class KeyVaultService:
    """Generate, protect, store, and unlock the app data key."""

    def __init__(self, repository: KeyVaultRepository | None = None) -> None:
        self._repository = repository

    def generate_data_key(self) -> bytes:
        return os.urandom(DATA_KEY_LENGTH)

    def create_key_vault_record(self, owner_account_id: int, password: str) -> KeyVaultBundle:
        data_key = self.generate_data_key()
        salt = os.urandom(SALT_LENGTH)
        nonce = os.urandom(NONCE_LENGTH)
        wrapping_key = self._derive_wrapping_key(password, salt)
        ciphertext = AESGCM(wrapping_key).encrypt(nonce, data_key, None)
        timestamp = _utc_now()

        record = KeyVaultRecord(
            id=None,
            owner_account_id=owner_account_id,
            vault_version=VAULT_VERSION,
            encryption_algorithm=ENCRYPTION_ALGORITHM,
            kdf_algorithm=KDF_ALGORITHM,
            kdf_parameters=json.dumps(DEFAULT_KDF_PARAMETERS, sort_keys=True),
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return KeyVaultBundle(data_key=data_key, record=record)

    def store_new_key_vault(self, owner_account_id: int, password: str) -> KeyVaultBundle:
        if self._repository is None:
            raise CryptoOperationError(
                "Unable to create the protected key vault.",
                log_message="KeyVaultService repository missing for store_new_key_vault.",
                security_sensitive=True,
            )

        bundle = self.create_key_vault_record(owner_account_id, password)
        saved_record = self._repository.save(bundle.record)
        return KeyVaultBundle(data_key=bundle.data_key, record=saved_record)

    def unlock_data_key(self, password: str, record: KeyVaultRecord) -> bytes:
        try:
            wrapping_key = self._derive_wrapping_key(password, record.salt, record.kdf_parameters)
            return AESGCM(wrapping_key).decrypt(record.nonce, record.ciphertext, None)
        except InvalidTag as error:
            raise AuthenticationError(
                "Unable to unlock protected data.",
                log_message="Key vault unlock failed due to invalid password or corrupted vault.",
                security_sensitive=True,
            ) from error

    def reprotect_data_key(
        self,
        current_password: str,
        new_password: str,
        record: KeyVaultRecord,
    ) -> KeyVaultRecord:
        data_key = self.unlock_data_key(current_password, record)
        salt = os.urandom(SALT_LENGTH)
        nonce = os.urandom(NONCE_LENGTH)
        wrapping_key = self._derive_wrapping_key(new_password, salt)
        ciphertext = AESGCM(wrapping_key).encrypt(nonce, data_key, None)

        return KeyVaultRecord(
            id=record.id,
            owner_account_id=record.owner_account_id,
            vault_version=record.vault_version,
            encryption_algorithm=record.encryption_algorithm,
            kdf_algorithm=record.kdf_algorithm,
            kdf_parameters=json.dumps(DEFAULT_KDF_PARAMETERS, sort_keys=True),
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            created_at=record.created_at,
            updated_at=_utc_now(),
        )

    def _derive_wrapping_key(
        self,
        password: str,
        salt: bytes,
        kdf_parameters_json: str | None = None,
    ) -> bytes:
        parameters = (
            json.loads(kdf_parameters_json)
            if kdf_parameters_json is not None
            else DEFAULT_KDF_PARAMETERS
        )
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=parameters["time_cost"],
            memory_cost=parameters["memory_cost"],
            parallelism=parameters["parallelism"],
            hash_len=parameters["hash_len"],
            type=Type.ID,
        )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
