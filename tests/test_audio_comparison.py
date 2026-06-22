from __future__ import annotations

import numpy as np
import pytest

from rifflock.audio import (
    COMPARISON_FAILURE_MESSAGE,
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


def test_riff_similarity_threshold_behavior_uses_configured_threshold() -> None:
    strict = RiffSimilarityService(AudioSettings(similarity_threshold=0.95))
    relaxed = RiffSimilarityService(AudioSettings(similarity_threshold=0.7))
    stored = _template([1.0, 2.0, 3.0, 4.0])
    candidate = _template([1.1, 2.0, 3.1, 4.0])

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
