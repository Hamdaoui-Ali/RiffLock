"""Riff template similarity comparison."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger

import numpy as np

from rifflock.audio.features import RiffFeatureTemplate
from rifflock.config import AudioSettings
from rifflock.utils.errors import AudioProcessingError

COMPARISON_FAILURE_MESSAGE = "The riff templates could not be compared."


@dataclass(frozen=True)
class RiffComparisonResult:
    """Similarity result using inverse normalized Euclidean distance.

    Score behavior:
    - `1.0` means identical templates
    - values closer to `0.0` mean larger distance
    - `passed` is derived from `score >= threshold`
    """

    score: float
    passed: bool
    threshold: float


class RiffSimilarityService:
    """Compare two riff templates using a configured similarity threshold."""

    def __init__(
        self,
        audio_settings: AudioSettings,
        *,
        logger: Logger | None = None,
    ) -> None:
        self._threshold = float(audio_settings.similarity_threshold)
        self._logger = logger

    def compare(
        self,
        stored_template: RiffFeatureTemplate,
        candidate_template: RiffFeatureTemplate,
    ) -> RiffComparisonResult:
        stored = self._validate_template(stored_template, "stored")
        candidate = self._validate_template(candidate_template, "candidate")
        if stored.shape != candidate.shape:
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message="Riff comparison rejected templates with mismatched shapes.",
            )

        distance = float(np.linalg.norm(stored - candidate))
        score = 1.0 / (1.0 + distance)
        passed = score >= self._threshold
        self._log_result(score, passed)
        return RiffComparisonResult(
            score=score,
            passed=passed,
            threshold=self._threshold,
        )

    def _validate_template(self, template: RiffFeatureTemplate, label: str) -> np.ndarray:
        if template.sample_rate <= 0:
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message=f"Riff comparison rejected {label} template with invalid sample rate.",
            )
        vector = np.asarray(template.vector, dtype=np.float32)
        if vector.ndim != 1 or vector.size == 0:
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message=f"Riff comparison rejected {label} template with invalid vector shape.",
            )
        if not np.isfinite(vector).all():
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message=f"Riff comparison rejected {label} template with non-finite values.",
            )
        return vector

    def _log_result(self, score: float, passed: bool) -> None:
        if self._logger is None:
            return
        self._logger.info(
            "Riff comparison completed score=%.4f passed=%s threshold=%.4f",
            score,
            passed,
            self._threshold,
        )
