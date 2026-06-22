"""Riff feature extraction and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger

import numpy as np

from rifflock.utils.errors import AudioProcessingError

FEATURE_EXTRACTION_FAILURE_MESSAGE = "The riff recording could not be processed."
MIN_AUDIO_DURATION_SECONDS = 1.0
SILENCE_PEAK_THRESHOLD = 1e-4
NOISE_FLATNESS_THRESHOLD = 0.5
MEL_BAND_COUNT = 13
CHROMA_COUNT = 12


@dataclass(frozen=True)
class RiffFeatureTemplate:
    """Comparable numeric riff template derived from recorded audio."""

    vector: np.ndarray
    sample_rate: int


class RiffFeatureExtractionService:
    """Normalize recorded audio and extract a stable comparison vector."""

    def __init__(self, *, logger: Logger | None = None) -> None:
        self._logger = logger

    def extract(self, samples: np.ndarray, sample_rate: int) -> RiffFeatureTemplate:
        audio = self._validate_audio(samples, sample_rate)
        normalized = self._normalize_audio(audio)
        flatness = self._spectral_flatness(normalized)
        if flatness >= NOISE_FLATNESS_THRESHOLD:
            raise AudioProcessingError(
                "The riff recording is too noisy. Please try again in a quieter environment.",
                log_message="Riff feature extraction rejected excessively noisy audio input.",
            )

        self._log_start(sample_rate, normalized.size, flatness)
        try:
            mel_summary = self._mel_band_summary(normalized, sample_rate)
            chroma = self._chroma_summary(normalized, sample_rate)
            envelope = self._envelope(normalized)
            onset_delta = np.maximum(np.diff(envelope), 0.0)
            temporal = np.array(
                [
                    float(envelope.mean()),
                    float(envelope.std()),
                    float(self._zero_crossing_rate(normalized)),
                    float(self._spectral_centroid(normalized, sample_rate)),
                    float(self._spectral_bandwidth(normalized, sample_rate)),
                    float(flatness),
                    float(onset_delta.mean()) if onset_delta.size else 0.0,
                    float(onset_delta.std()) if onset_delta.size else 0.0,
                ],
                dtype=np.float32,
            )
        except Exception as error:
            self._log_failure(error)
            raise AudioProcessingError(
                FEATURE_EXTRACTION_FAILURE_MESSAGE,
                log_message=f"Riff feature extraction failed with {type(error).__name__}.",
            ) from error

        vector = np.concatenate([mel_summary, chroma, temporal]).astype(np.float32)
        self._log_success(vector.size)
        return RiffFeatureTemplate(vector=vector, sample_rate=sample_rate)

    def _validate_audio(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        audio = np.asarray(samples, dtype=np.float32)
        if audio.ndim != 1:
            raise AudioProcessingError(
                FEATURE_EXTRACTION_FAILURE_MESSAGE,
                log_message="Riff feature extraction rejected non-mono audio input.",
            )
        if audio.size == 0 or sample_rate <= 0:
            raise AudioProcessingError(
                FEATURE_EXTRACTION_FAILURE_MESSAGE,
                log_message="Riff feature extraction rejected empty or invalid audio input.",
            )
        if not np.isfinite(audio).all():
            raise AudioProcessingError(
                FEATURE_EXTRACTION_FAILURE_MESSAGE,
                log_message="Riff feature extraction rejected non-finite audio input.",
            )
        if audio.size < int(sample_rate * MIN_AUDIO_DURATION_SECONDS):
            raise AudioProcessingError(
                "The riff recording is too short.",
                log_message="Riff feature extraction rejected audio shorter than minimum duration.",
            )
        if float(np.max(np.abs(audio))) < SILENCE_PEAK_THRESHOLD:
            raise AudioProcessingError(
                "The riff recording is too quiet. Please play the riff again.",
                log_message="Riff feature extraction rejected silent audio input.",
            )
        return audio

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        peak = float(np.max(np.abs(audio)))
        return (audio / peak).astype(np.float32)

    def _mel_band_summary(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        spectrum = np.abs(np.fft.rfft(audio)) ** 2
        frequencies = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate)
        bands = np.geomspace(40.0, sample_rate / 2, MEL_BAND_COUNT + 1)
        values: list[float] = []
        for start, end in zip(bands[:-1], bands[1:]):
            mask = (frequencies >= start) & (frequencies < end)
            if not np.any(mask):
                values.append(0.0)
                continue
            values.append(float(np.log1p(spectrum[mask].mean())))
        return np.asarray(values, dtype=np.float32)

    def _chroma_summary(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        spectrum = np.abs(np.fft.rfft(audio))
        frequencies = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate)
        chroma = np.zeros(CHROMA_COUNT, dtype=np.float64)
        valid = frequencies > 0
        if np.any(valid):
            midi = np.round(69 + 12 * np.log2(frequencies[valid] / 440.0)).astype(int)
            chroma_indices = np.mod(midi, CHROMA_COUNT)
            np.add.at(chroma, chroma_indices, spectrum[valid])
        total = chroma.sum()
        if total > 0:
            chroma /= total
        return chroma.astype(np.float32)

    def _envelope(self, audio: np.ndarray, frame_size: int = 2048) -> np.ndarray:
        usable = audio[: audio.size - (audio.size % frame_size)]
        if usable.size == 0:
            usable = audio
        frames = usable.reshape(-1, frame_size) if usable.size >= frame_size else usable.reshape(1, -1)
        return np.sqrt(np.mean(np.square(frames), axis=1)).astype(np.float32)

    def _zero_crossing_rate(self, audio: np.ndarray) -> float:
        crossings = np.count_nonzero(np.diff(np.signbit(audio)))
        return crossings / max(audio.size - 1, 1)

    def _spectral_centroid(self, audio: np.ndarray, sample_rate: int) -> float:
        magnitude = np.abs(np.fft.rfft(audio))
        frequencies = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate)
        total = magnitude.sum()
        if total <= 0:
            return 0.0
        return float(np.sum(frequencies * magnitude) / total)

    def _spectral_bandwidth(self, audio: np.ndarray, sample_rate: int) -> float:
        magnitude = np.abs(np.fft.rfft(audio))
        frequencies = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate)
        total = magnitude.sum()
        if total <= 0:
            return 0.0
        centroid = self._spectral_centroid(audio, sample_rate)
        return float(np.sqrt(np.sum(((frequencies - centroid) ** 2) * magnitude) / total))

    def _spectral_flatness(self, audio: np.ndarray) -> float:
        power = np.abs(np.fft.rfft(audio)) ** 2
        power = np.maximum(power, 1e-12)
        geometric_mean = float(np.exp(np.mean(np.log(power))))
        arithmetic_mean = float(np.mean(power))
        return geometric_mean / arithmetic_mean

    def _log_start(self, sample_rate: int, sample_count: int, flatness: float) -> None:
        if self._logger is None:
            return
        self._logger.info(
            "Starting riff feature extraction sample_rate=%s sample_count=%s flatness=%.4f",
            sample_rate,
            sample_count,
            flatness,
        )

    def _log_success(self, vector_size: int) -> None:
        if self._logger is None:
            return
        self._logger.info(
            "Riff feature extraction completed vector_size=%s",
            vector_size,
        )

    def _log_failure(self, error: Exception) -> None:
        if self._logger is None:
            return
        self._logger.warning(
            "Riff feature extraction failed error_type=%s",
            type(error).__name__,
        )
