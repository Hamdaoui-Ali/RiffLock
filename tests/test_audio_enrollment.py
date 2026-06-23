from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rifflock.audio import (
    REQUIRED_RIFF_RECORDINGS,
    RiffEnrollmentService,
    RiffFeatureTemplate,
    deserialize_riff_template,
)
from rifflock.auth import OwnerSetupRequest, OwnerSetupService
from rifflock.storage import OwnerAccountRepository, RiffTemplateRepository, KeyVaultRepository, initialize_database
from rifflock.utils.errors import AuthenticationError


def test_riff_enrollment_creates_reference_template_from_multiple_samples(tmp_path: Path) -> None:
    service, _, _ = _build_service(
        tmp_path,
        extracted_templates=[
            _template([1.0, 2.0, 3.0]),
            _template([2.0, 3.0, 4.0]),
            _template([3.0, 4.0, 5.0]),
        ],
    )

    result = service.enroll(1, "StrongPass123!")

    assert np.allclose(result.template.vector, np.array([2.0, 3.0, 4.0], dtype=np.float32))
    assert result.riff_template.recording_count == REQUIRED_RIFF_RECORDINGS
    assert result.owner_account.riff_2fa_enabled is True


def test_riff_enrollment_saves_template_and_enables_owner_flag(tmp_path: Path) -> None:
    service, owner_repository, riff_repository = _build_service(
        tmp_path,
        extracted_templates=[
            _template([1.0, 2.0, 3.0]),
            _template([1.5, 2.5, 3.5]),
            _template([2.0, 3.0, 4.0]),
        ],
    )

    result = service.enroll(1, "StrongPass123!")

    stored_owner = owner_repository.get_by_id(1)
    stored_template = riff_repository.get_by_owner_account_id(1)
    assert stored_owner is not None
    assert stored_owner.riff_2fa_enabled is True
    assert stored_template is not None
    decoded = deserialize_riff_template(stored_template.template_data)
    assert np.allclose(decoded.vector, result.template.vector)
    assert len(decoded.sample_templates) == REQUIRED_RIFF_RECORDINGS
    assert np.allclose(decoded.sample_templates[0].vector, np.array([1.0, 2.0, 3.0], dtype=np.float32))
    assert stored_template.recording_count == REQUIRED_RIFF_RECORDINGS
    assert b"raw-audio" not in stored_template.template_data


def test_riff_template_deserialization_supports_older_payloads_without_samples() -> None:
    decoded = deserialize_riff_template(
        b'{"sample_rate":22050,"vector":[1.0,2.0,3.0],"chroma_sequence":null,"onset_count":2}'
    )

    assert np.allclose(decoded.vector, np.array([1.0, 2.0, 3.0], dtype=np.float32))
    assert decoded.sample_templates == ()


def test_riff_enrollment_requires_password_confirmation(tmp_path: Path) -> None:
    service, owner_repository, riff_repository = _build_service(
        tmp_path,
        extracted_templates=[
            _template([1.0, 2.0, 3.0]),
            _template([1.0, 2.0, 3.0]),
            _template([1.0, 2.0, 3.0]),
        ],
    )

    with pytest.raises(AuthenticationError) as error:
        service.enroll(1, "WrongPass123!")

    assert error.value.user_message == "Password confirmation failed."
    assert owner_repository.get_by_id(1) is not None
    assert owner_repository.get_by_id(1).riff_2fa_enabled is False
    assert riff_repository.get_by_owner_account_id(1) is None


class _FakeRecordingService:
    def record(self):
        from rifflock.audio.recording import AudioRecording

        return AudioRecording(
            samples=np.array([0.25, 0.5, 0.75], dtype=np.float32),
            sample_rate=22050,
            duration_seconds=1,
        )


class _FakeFeatureExtractionService:
    def __init__(self, templates: list[RiffFeatureTemplate]) -> None:
        self._templates = templates
        self._index = 0

    def extract(self, samples, sample_rate):
        template = self._templates[self._index]
        self._index += 1
        return template


def _build_service(
    tmp_path: Path,
    *,
    extracted_templates: list[RiffFeatureTemplate],
) -> tuple[RiffEnrollmentService, OwnerAccountRepository, RiffTemplateRepository]:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    owner_repository = OwnerAccountRepository(database_path)
    key_vault_repository = KeyVaultRepository(database_path)
    riff_repository = RiffTemplateRepository(database_path)
    setup_service = OwnerSetupService(owner_repository, key_vault_repository)
    setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )
    return (
        RiffEnrollmentService(
            owner_repository=owner_repository,
            riff_template_repository=riff_repository,
            recording_service=_FakeRecordingService(),
            feature_extraction_service=_FakeFeatureExtractionService(extracted_templates),
        ),
        owner_repository,
        riff_repository,
    )


def _template(values: list[float]) -> RiffFeatureTemplate:
    vector = np.asarray(values, dtype=np.float32)
    return RiffFeatureTemplate(
        vector=vector,
        sample_rate=22050,
        chroma_sequence=np.tile(vector.reshape(-1, 1), (1, 2)),
        onset_count=2,
    )
