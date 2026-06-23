from __future__ import annotations

import numpy as np
import pytest

from rifflock.audio import (
    COMPARISON_FAILURE_MESSAGE,
    RiffFeatureExtractionService,
    RiffFeatureTemplate,
    RiffSimilarityService,
)
from rifflock.config import AudioSettings
from rifflock.utils.errors import AudioProcessingError


def test_riff_similarity_exact_and_similar_templates_pass() -> None:
    service = RiffSimilarityService(AudioSettings(similarity_threshold=0.8))
    stored = _template([1.0, 2.0, 3.0, 4.0])
    exact = _template([1.0, 2.0, 3.0, 4.0])
    near = _template([1.02, 1.98, 3.01, 3.97])

    exact_result = service.compare(stored, exact)
    near_result = service.compare(stored, near)

    assert exact_result.score == pytest.approx(1.0)
    assert exact_result.passed is True
    assert near_result.score < exact_result.score
    assert near_result.passed is True


def test_riff_similarity_different_templates_fail() -> None:
    service = RiffSimilarityService(AudioSettings(similarity_threshold=0.8))

    result = service.compare(
        _template([1.0, 2.0, 3.0, 4.0]),
        _template([20.0, 18.0, 16.0, 14.0]),
    )

    assert result.score < 0.8
    assert result.passed is False


def test_riff_similarity_uses_best_enrolled_take_instead_of_only_average() -> None:
    service = RiffSimilarityService(AudioSettings(similarity_threshold=0.8))
    stored = RiffFeatureTemplate(
        vector=np.asarray([10.0, 10.0, 10.0, 10.0], dtype=np.float32),
        sample_rate=22050,
        sample_templates=(
            _template([1.0, 2.0, 3.0, 4.0]),
            _template([7.0, 7.0, 7.0, 7.0]),
        ),
    )

    result = service.compare(stored, _template([1.02, 2.01, 2.99, 4.0]))

    assert result.passed is True
    assert result.score > 0.95


def test_riff_similarity_accepts_same_notes_with_timing_and_level_variation() -> None:
    sample_rate = 22050
    extractor = RiffFeatureExtractionService()
    service = RiffSimilarityService(AudioSettings(similarity_threshold=0.8))
    stored = extractor.extract(
        _synthetic_riff(
            sample_rate=sample_rate,
            frequencies=[220.0, 247.0, 294.0, 330.0],
            durations=[0.35, 0.35, 0.40, 0.45],
        ),
        sample_rate,
    )
    same_notes = extractor.extract(
        _synthetic_riff(
            sample_rate=sample_rate,
            frequencies=[220.0, 247.0, 294.0, 330.0],
            durations=[0.42, 0.30, 0.46, 0.39],
            amplitude=0.35,
            start_silence_seconds=0.08,
        ),
        sample_rate,
    )
    different_notes = extractor.extract(
        _synthetic_riff(
            sample_rate=sample_rate,
            frequencies=[392.0, 440.0, 494.0, 523.0],
            durations=[0.42, 0.30, 0.46, 0.39],
            amplitude=0.35,
            start_silence_seconds=0.08,
        ),
        sample_rate,
    )

    assert service.compare(stored, same_notes).passed is True
    assert service.compare(stored, different_notes).passed is False


def test_riff_similarity_threshold_behavior_uses_configured_threshold() -> None:
    strict = RiffSimilarityService(AudioSettings(similarity_threshold=0.95))
    relaxed = RiffSimilarityService(AudioSettings(similarity_threshold=0.7))
    stored = _template([1.0, 2.0, 3.0, 4.0])
    candidate = _template([1.3, 2.0, 3.3, 4.0])

    strict_result = strict.compare(stored, candidate)
    relaxed_result = relaxed.compare(stored, candidate)

    assert strict_result.score == pytest.approx(relaxed_result.score)
    assert strict_result.threshold == pytest.approx(0.95)
    assert relaxed_result.threshold == pytest.approx(0.7)
    assert strict_result.passed is False
    assert relaxed_result.passed is True


def test_riff_similarity_rejects_invalid_templates() -> None:
    service = RiffSimilarityService(AudioSettings(similarity_threshold=0.8))

    with pytest.raises(AudioProcessingError) as invalid_values:
        service.compare(
            _template([1.0, 2.0, 3.0]),
            RiffFeatureTemplate(vector=np.array([1.0, np.nan, 3.0], dtype=np.float32), sample_rate=22050),
        )

    with pytest.raises(AudioProcessingError) as mismatched_shapes:
        service.compare(
            _template([1.0, 2.0, 3.0]),
            _template([1.0, 2.0]),
        )

    assert invalid_values.value.user_message == COMPARISON_FAILURE_MESSAGE
    assert mismatched_shapes.value.user_message == COMPARISON_FAILURE_MESSAGE


def _template(values: list[float]) -> RiffFeatureTemplate:
    return RiffFeatureTemplate(
        vector=np.asarray(values, dtype=np.float32),
        sample_rate=22050,
    )


def _synthetic_riff(
    *,
    sample_rate: int,
    frequencies: list[float],
    durations: list[float],
    amplitude: float = 0.5,
    start_silence_seconds: float = 0.0,
) -> np.ndarray:
    parts: list[np.ndarray] = []
    if start_silence_seconds > 0:
        parts.append(np.zeros(int(sample_rate * start_silence_seconds), dtype=np.float32))
    for frequency, duration in zip(frequencies, durations):
        timeline = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        envelope = np.minimum(np.linspace(0.0, 1.0, timeline.size), 1.0)
        envelope *= np.linspace(1.0, 0.75, timeline.size)
        parts.append((amplitude * envelope * np.sin(2 * np.pi * frequency * timeline)).astype(np.float32))
        parts.append(np.zeros(int(sample_rate * 0.03), dtype=np.float32))

    samples = np.concatenate(parts)
    target_length = sample_rate * 3
    if samples.size < target_length:
        samples = np.pad(samples, (0, target_length - samples.size))
    return samples[:target_length].astype(np.float32)
