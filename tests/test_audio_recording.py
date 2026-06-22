from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from rifflock.audio import (
    RECORDING_CHANNELS,
    RECORDING_DTYPE,
    RECORDING_FAILURE_MESSAGE,
    MicrophoneRecordingService,
)
from rifflock.config import AudioSettings
from rifflock.utils.errors import AudioProcessingError


def test_microphone_recording_uses_sounddevice_and_returns_numeric_audio() -> None:
    sounddevice = Mock()
    sounddevice.rec.return_value = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
    service = MicrophoneRecordingService(
        AudioSettings(duration_seconds=1, sample_rate=3),
        sounddevice_module=sounddevice,
    )

    recording = service.record()

    sounddevice.rec.assert_called_once_with(
        3,
        samplerate=3,
        channels=RECORDING_CHANNELS,
        dtype=RECORDING_DTYPE,
    )
    sounddevice.wait.assert_called_once_with()
    assert isinstance(recording.samples, np.ndarray)
    assert np.allclose(recording.samples, np.array([0.1, 0.2, 0.3], dtype=np.float32))
    assert recording.sample_rate == 3
    assert recording.duration_seconds == 1


def test_microphone_recording_uses_duration_and_sample_rate_from_config() -> None:
    sounddevice = Mock()
    sounddevice.rec.return_value = np.zeros((16000, 1), dtype=np.float32)
    service = MicrophoneRecordingService(
        AudioSettings(duration_seconds=2, sample_rate=8000),
        sounddevice_module=sounddevice,
    )

    recording = service.record()

    sounddevice.rec.assert_called_once_with(
        16000,
        samplerate=8000,
        channels=RECORDING_CHANNELS,
        dtype=RECORDING_DTYPE,
    )
    assert recording.samples.size == 16000


def test_microphone_recording_wraps_device_failures_safely() -> None:
    sounddevice = Mock()
    sounddevice.rec.side_effect = PermissionError("device denied")
    logger = Mock()
    service = MicrophoneRecordingService(
        AudioSettings(duration_seconds=5, sample_rate=44100),
        sounddevice_module=sounddevice,
        logger=logger,
    )

    with pytest.raises(AudioProcessingError) as error:
        service.record()

    assert error.value.user_message == RECORDING_FAILURE_MESSAGE
    sounddevice.wait.assert_not_called()
    logger.warning.assert_called_once_with(
        "Microphone recording failed error_type=%s",
        "PermissionError",
    )


def test_microphone_recording_never_passes_raw_audio_to_logger() -> None:
    raw_audio = np.array([[0.5], [0.25]], dtype=np.float32)
    sounddevice = Mock()
    sounddevice.rec.return_value = raw_audio
    logger = Mock()
    service = MicrophoneRecordingService(
        AudioSettings(duration_seconds=1, sample_rate=2),
        sounddevice_module=sounddevice,
        logger=logger,
    )

    service.record()

    for call in logger.method_calls:
        for argument in call.args:
            assert not isinstance(argument, np.ndarray)
            assert argument is not raw_audio
