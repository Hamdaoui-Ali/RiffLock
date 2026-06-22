from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from rifflock.audio import (
    FEATURE_EXTRACTION_FAILURE_MESSAGE,
    RiffFeatureExtractionService,
)
from rifflock.utils.errors import AudioProcessingError


def test_riff_feature_extraction_returns_numeric_template_for_dummy_audio() -> None:
    service = RiffFeatureExtractionService()

    template = service.extract(_sine_wave(sample_rate=22050, duration_seconds=2.0), 22050)

    assert isinstance(template.vector, np.ndarray)
    assert template.vector.dtype == np.float32
    assert template.vector.ndim == 1
    assert template.vector.size > 0
    assert template.sample_rate == 22050


def test_riff_feature_extraction_rejects_silence() -> None:
    service = RiffFeatureExtractionService()

    with pytest.raises(AudioProcessingError) as error:
        service.extract(np.zeros(22050, dtype=np.float32), 22050)

    assert error.value.user_message == "The riff recording is too quiet. Please play the riff again."


def test_riff_feature_extraction_rejects_too_short_audio() -> None:
    service = RiffFeatureExtractionService()

    with pytest.raises(AudioProcessingError) as error:
        service.extract(_sine_wave(sample_rate=22050, duration_seconds=0.2), 22050)

    assert error.value.user_message == "The riff recording is too short."


def test_riff_feature_extraction_has_stable_output_shape() -> None:
    service = RiffFeatureExtractionService()
    samples = _sine_wave(sample_rate=22050, duration_seconds=2.0)

    first = service.extract(samples, 22050)
    second = service.extract(samples, 22050)

    assert first.vector.shape == second.vector.shape
    assert np.allclose(first.vector, second.vector)


def test_riff_feature_extraction_rejects_invalid_audio_input() -> None:
    service = RiffFeatureExtractionService()

    with pytest.raises(AudioProcessingError) as error:
        service.extract(np.array([0.1, np.nan, 0.2], dtype=np.float32), 22050)

    assert error.value.user_message == FEATURE_EXTRACTION_FAILURE_MESSAGE


def test_riff_feature_extraction_rejects_extremely_noisy_audio() -> None:
    service = RiffFeatureExtractionService()
    rng = np.random.default_rng(1234)
    noisy = rng.normal(0.0, 1.0, 22050 * 2).astype(np.float32)

    with pytest.raises(AudioProcessingError) as error:
        service.extract(noisy, 22050)

    assert error.value.user_message == "The riff recording is too noisy. Please try again in a quieter environment."


def test_riff_feature_extraction_never_logs_raw_audio() -> None:
    logger = Mock()
    samples = _sine_wave(sample_rate=22050, duration_seconds=2.0)
    service = RiffFeatureExtractionService(logger=logger)

    service.extract(samples, 22050)

    for call in logger.method_calls:
        for argument in call.args:
            assert not isinstance(argument, np.ndarray)
            assert argument is not samples


def _sine_wave(*, sample_rate: int, duration_seconds: float, frequency: float = 440.0) -> np.ndarray:
    timeline = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * frequency * timeline)).astype(np.float32)
