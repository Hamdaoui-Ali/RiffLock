"""Riff enrollment service for enabling owner 2FA."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from logging import Logger
from typing import Callable

import numpy as np

from rifflock.audio.features import RiffFeatureExtractionService, RiffFeatureTemplate
from rifflock.audio.recording import MicrophoneRecordingService
from rifflock.auth.passwords import PasswordService
from rifflock.models import OwnerAccountRecord, RiffTemplateRecord
from rifflock.storage import OwnerAccountRepository, RiffTemplateRepository
from rifflock.utils.errors import AuthenticationError

RIFF_TEMPLATE_VERSION = 1
REQUIRED_RIFF_RECORDINGS = 3


@dataclass(frozen=True)
class RiffEnrollmentResult:
    owner_account: OwnerAccountRecord
    riff_template: RiffTemplateRecord
    template: RiffFeatureTemplate


class RiffEnrollmentService:
    """Record, aggregate, and persist the owner riff template."""

    def __init__(
        self,
        owner_repository: OwnerAccountRepository,
        riff_template_repository: RiffTemplateRepository,
        recording_service: MicrophoneRecordingService,
        feature_extraction_service: RiffFeatureExtractionService,
        *,
        password_service: PasswordService | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._owner_repository = owner_repository
        self._riff_template_repository = riff_template_repository
        self._recording_service = recording_service
        self._feature_extraction_service = feature_extraction_service
        self._password_service = password_service or PasswordService()
        self._logger = logger

    def enroll(
        self,
        owner_account_id: int,
        password_confirmation: str,
        *,
        before_recording: Callable[[int, int], None] | None = None,
    ) -> RiffEnrollmentResult:
        owner_account = self._owner_repository.get_by_id(owner_account_id)
        if owner_account is None:
            raise AuthenticationError(
                "Password confirmation failed.",
                log_message="Riff enrollment rejected because owner account does not exist.",
            )
        if not self._password_service.verify_password(password_confirmation, owner_account.password_hash):
            raise AuthenticationError(
                "Password confirmation failed.",
                log_message="Riff enrollment rejected because password confirmation failed.",
            )

        templates: list[RiffFeatureTemplate] = []
        for attempt_index in range(REQUIRED_RIFF_RECORDINGS):
            if before_recording is not None:
                before_recording(attempt_index + 1, REQUIRED_RIFF_RECORDINGS)
            recording = self._recording_service.record()
            templates.append(
                self._feature_extraction_service.extract(
                    recording.samples,
                    recording.sample_rate,
                )
            )

        reference_template = self._build_reference_template(templates)
        saved_template = self._save_template(owner_account.id, reference_template, len(templates))
        updated_owner = self._enable_riff_2fa(owner_account)
        self._log_success(owner_account_id, len(templates))
        return RiffEnrollmentResult(
            owner_account=updated_owner,
            riff_template=saved_template,
            template=reference_template,
        )

    def _build_reference_template(self, templates: list[RiffFeatureTemplate]) -> RiffFeatureTemplate:
        if len(templates) < REQUIRED_RIFF_RECORDINGS:
            raise AuthenticationError(
                "Riff enrollment could not be completed.",
                log_message="Riff enrollment rejected because too few templates were provided.",
            )
        sample_rate = templates[0].sample_rate
        vectors = []
        chroma_sequences = []
        onset_counts = []
        for template in templates:
            if template.sample_rate != sample_rate:
                raise AuthenticationError(
                    "Riff enrollment could not be completed.",
                    log_message="Riff enrollment rejected because template sample rates do not match.",
                )
            vectors.append(np.asarray(template.vector, dtype=np.float32))
            if template.chroma_sequence is None:
                raise AuthenticationError(
                    "Riff enrollment could not be completed.",
                    log_message="Riff enrollment rejected because chroma sequence is missing.",
                )
            chroma_sequences.append(np.asarray(template.chroma_sequence, dtype=np.float32))
            onset_counts.append(int(template.onset_count))

        first_shape = vectors[0].shape
        if any(vector.shape != first_shape for vector in vectors[1:]):
            raise AuthenticationError(
                "Riff enrollment could not be completed.",
                log_message="Riff enrollment rejected because template shapes do not match.",
            )
        first_chroma_shape = chroma_sequences[0].shape
        if any(sequence.shape != first_chroma_shape for sequence in chroma_sequences[1:]):
            raise AuthenticationError(
                "Riff enrollment could not be completed.",
                log_message="Riff enrollment rejected because chroma sequence shapes do not match.",
            )

        return RiffFeatureTemplate(
            vector=np.mean(np.stack(vectors, axis=0), axis=0).astype(np.float32),
            sample_rate=sample_rate,
            chroma_sequence=np.mean(np.stack(chroma_sequences, axis=0), axis=0).astype(np.float32),
            onset_count=int(round(float(np.mean(onset_counts)))),
            sample_templates=tuple(templates),
        )

    def _save_template(
        self,
        owner_account_id: int,
        template: RiffFeatureTemplate,
        recording_count: int,
    ) -> RiffTemplateRecord:
        timestamp = _utc_now()
        existing = self._riff_template_repository.get_by_owner_account_id(owner_account_id)
        record = RiffTemplateRecord(
            id=None if existing is None else existing.id,
            owner_account_id=owner_account_id,
            template_version=RIFF_TEMPLATE_VERSION,
            template_data=serialize_riff_template(template),
            recording_count=recording_count,
            created_at=timestamp if existing is None else existing.created_at,
            updated_at=timestamp,
        )
        return self._riff_template_repository.save(record)

    def _enable_riff_2fa(self, owner_account: OwnerAccountRecord) -> OwnerAccountRecord:
        return self._owner_repository.save(
            OwnerAccountRecord(
                id=owner_account.id,
                email=owner_account.email,
                password_hash=owner_account.password_hash,
                password_policy_version=owner_account.password_policy_version,
                riff_2fa_enabled=True,
                created_at=owner_account.created_at,
                updated_at=_utc_now(),
            )
        )

    def _log_success(self, owner_account_id: int, recording_count: int) -> None:
        if self._logger is None:
            return
        self._logger.info(
            "Riff enrollment completed owner_account_id=%s recording_count=%s",
            owner_account_id,
            recording_count,
        )


def serialize_riff_template(template: RiffFeatureTemplate) -> bytes:
    return json.dumps(
        _serialize_template_payload(template, include_samples=True),
        separators=(",", ":"),
    ).encode("utf-8")


def deserialize_riff_template(template_data: bytes) -> RiffFeatureTemplate:
    payload = json.loads(template_data.decode("utf-8"))
    return _deserialize_template_payload(payload)


def _serialize_template_payload(
    template: RiffFeatureTemplate,
    *,
    include_samples: bool,
) -> dict:
    payload = {
        "sample_rate": template.sample_rate,
        "vector": np.asarray(template.vector, dtype=np.float32).tolist(),
        "chroma_sequence": (
            np.asarray(template.chroma_sequence, dtype=np.float32).tolist()
            if template.chroma_sequence is not None
            else None
        ),
        "onset_count": int(template.onset_count),
    }
    if include_samples:
        payload["sample_templates"] = [
            _serialize_template_payload(sample, include_samples=False)
            for sample in template.sample_templates
        ]
    return payload


def _deserialize_template_payload(payload: dict) -> RiffFeatureTemplate:
    chroma_sequence = payload.get("chroma_sequence")
    return RiffFeatureTemplate(
        vector=np.asarray(payload["vector"], dtype=np.float32),
        chroma_sequence=(
            None
            if chroma_sequence is None
            else np.asarray(chroma_sequence, dtype=np.float32)
        ),
        onset_count=int(payload.get("onset_count", 0)),
        sample_rate=int(payload["sample_rate"]),
        sample_templates=tuple(
            _deserialize_template_payload(sample)
            for sample in payload.get("sample_templates", [])
        ),
    )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
