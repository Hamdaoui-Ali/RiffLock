"""Microphone recording service for riff enrollment and verification."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from typing import Any

import numpy as np

from rifflock.config import AudioSettings
from rifflock.utils.errors import AudioProcessingError

RECORDING_CHANNELS = 1
RECORDING_DTYPE = "float32"
RECORDING_FAILURE_MESSAGE = (
    "Microphone recording failed. Check microphone permissions and device availability."
)


@dataclass(frozen=True)
class AudioRecording:
    """A captured mono recording and its associated settings."""

    samples: np.ndarray
    sample_rate: int
    duration_seconds: int


class MicrophoneRecordingService:
    """Record mono audio from the default input device using sounddevice."""

    def __init__(
        self,
        audio_settings: AudioSettings,
        *,
        sounddevice_module: Any | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._audio_settings = audio_settings
        self._sounddevice = sounddevice_module or _import_sounddevice()
        self._logger = logger

    def record(self) -> AudioRecording:
        frame_count = self._audio_settings.duration_seconds * self._audio_settings.sample_rate
        self._log_start(frame_count)

        try:
            raw_recording = self._sounddevice.rec(
                frame_count,
                samplerate=self._audio_settings.sample_rate,
                channels=RECORDING_CHANNELS,
                dtype=RECORDING_DTYPE,
            )
            self._sounddevice.wait()
        except Exception as error:
            self._log_failure(error)
            raise AudioProcessingError(
                RECORDING_FAILURE_MESSAGE,
                log_message=f"Microphone recording failed with {type(error).__name__}.",
            ) from error

        samples = np.asarray(raw_recording, dtype=np.float32).reshape(-1)
        self._log_success(samples.size)
        return AudioRecording(
            samples=samples,
            sample_rate=self._audio_settings.sample_rate,
            duration_seconds=self._audio_settings.duration_seconds,
        )

    def _log_start(self, frame_count: int) -> None:
        if self._logger is None:
            return
        self._logger.info(
            "Starting microphone recording duration_seconds=%s sample_rate=%s frame_count=%s",
            self._audio_settings.duration_seconds,
            self._audio_settings.sample_rate,
            frame_count,
        )

    def _log_success(self, sample_count: int) -> None:
        if self._logger is None:
            return
        self._logger.info(
            "Microphone recording completed sample_count=%s sample_rate=%s",
            sample_count,
            self._audio_settings.sample_rate,
        )

    def _log_failure(self, error: Exception) -> None:
        if self._logger is None:
            return
        self._logger.warning(
            "Microphone recording failed error_type=%s",
            type(error).__name__,
        )


def _import_sounddevice():
    import sounddevice

    return sounddevice
