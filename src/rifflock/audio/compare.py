"""Riff template similarity comparison."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger

import librosa
import numpy as np

from rifflock.audio.features import RiffFeatureTemplate
from rifflock.config import AudioSettings
from rifflock.utils.errors import AudioProcessingError

COMPARISON_FAILURE_MESSAGE = "The riff templates could not be compared."
MIN_ONSET_RATIO = 0.4
MIN_SEQUENCE_SCORE_MARGIN = 0.05


@dataclass(frozen=True)
class RiffComparisonResult:
    """Similarity result for two riff templates."""

    score: float
    passed: bool
    threshold: float


class RiffSimilarityService:
    """Compare two riff templates using sequence alignment over chroma features."""

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
        enrolled_templates = (stored_template, *stored_template.sample_templates)
        results = [
            self._compare_single(enrolled_template, candidate_template)
            for enrolled_template in enrolled_templates
        ]
        return max(results, key=lambda result: result.score)

    def _compare_single(
        self,
        stored_template: RiffFeatureTemplate,
        candidate_template: RiffFeatureTemplate,
    ) -> RiffComparisonResult:
        stored_vector = self._validate_template(stored_template, "stored")
        candidate_vector = self._validate_template(candidate_template, "candidate")
        if stored_vector.shape != candidate_vector.shape:
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message="Riff comparison rejected templates with mismatched summary shapes.",
            )

        if stored_template.chroma_sequence is None or candidate_template.chroma_sequence is None:
            score = self._summary_score(stored_vector, candidate_vector)
            passed = score >= self._threshold
            self._log_result(score, passed, score, score, score)
            return RiffComparisonResult(score=score, passed=passed, threshold=self._threshold)

        stored_sequence = self._validate_chroma_sequence(stored_template, "stored")
        candidate_sequence = self._validate_chroma_sequence(candidate_template, "candidate")

        sequence_score = self._dtw_score(stored_sequence, candidate_sequence)
        summary_score = self._summary_score(stored_vector, candidate_vector)
        onset_score = self._onset_score(
            stored_template.onset_count,
            candidate_template.onset_count,
        )
        score = 0.85 * sequence_score + 0.05 * summary_score + 0.10 * onset_score
        passed = (
            score >= self._threshold
            and sequence_score >= max(0.0, self._threshold - MIN_SEQUENCE_SCORE_MARGIN)
            and onset_score >= MIN_ONSET_RATIO
        )
        self._log_result(score, passed, sequence_score, summary_score, onset_score)
        return RiffComparisonResult(
            score=score,
            passed=passed,
            threshold=self._threshold,
        )

    def _dtw_score(
        self,
        stored_sequence: np.ndarray,
        candidate_sequence: np.ndarray,
    ) -> float:
        cost, _ = librosa.sequence.dtw(
            X=stored_sequence,
            Y=candidate_sequence,
            metric="cosine",
        )
        path_length = max(stored_sequence.shape[1], candidate_sequence.shape[1], 1)
        normalized_cost = float(cost[-1, -1]) / float(path_length)
        return 1.0 / (1.0 + normalized_cost)

    def _summary_score(
        self,
        stored_vector: np.ndarray,
        candidate_vector: np.ndarray,
    ) -> float:
        distance = float(np.linalg.norm(stored_vector - candidate_vector) / np.sqrt(stored_vector.size))
        return 1.0 / (1.0 + distance)

    def _onset_score(self, stored_onsets: int, candidate_onsets: int) -> float:
        if stored_onsets <= 0 or candidate_onsets <= 0:
            return 0.0
        return min(stored_onsets, candidate_onsets) / max(stored_onsets, candidate_onsets)

    def _validate_chroma_sequence(
        self,
        template: RiffFeatureTemplate,
        label: str,
    ) -> np.ndarray:
        sequence = np.asarray(template.chroma_sequence, dtype=np.float32)
        if sequence.ndim != 2 or sequence.shape[0] != 12 or sequence.shape[1] == 0:
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message=f"Riff comparison rejected {label} template with invalid chroma sequence.",
            )
        if not np.isfinite(sequence).all():
            raise AudioProcessingError(
                COMPARISON_FAILURE_MESSAGE,
                log_message=f"Riff comparison rejected {label} template with non-finite chroma sequence.",
            )
        return sequence

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

    def _log_result(
        self,
        score: float,
        passed: bool,
        sequence_score: float,
        summary_score: float,
        onset_score: float,
    ) -> None:
        if self._logger is None:
            return
        self._logger.info(
            (
                "Riff comparison completed score=%.4f passed=%s threshold=%.4f "
                "sequence=%.4f summary=%.4f onset=%.4f"
            ),
            score,
            passed,
            self._threshold,
            sequence_score,
            summary_score,
            onset_score,
        )
