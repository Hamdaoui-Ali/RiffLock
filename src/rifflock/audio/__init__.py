"""Audio domain package."""

from rifflock.audio.compare import (
    COMPARISON_FAILURE_MESSAGE,
    RiffComparisonResult,
    RiffSimilarityService,
)
from rifflock.audio.enrollment import (
    REQUIRED_RIFF_RECORDINGS,
    RIFF_TEMPLATE_VERSION,
    RiffEnrollmentResult,
    RiffEnrollmentService,
    deserialize_riff_template,
    serialize_riff_template,
)
from rifflock.audio.features import (
    CHROMA_COUNT,
    FEATURE_EXTRACTION_FAILURE_MESSAGE,
    MEL_BAND_COUNT,
    MIN_AUDIO_DURATION_SECONDS,
    NOISE_FLATNESS_THRESHOLD,
    RiffFeatureExtractionService,
    RiffFeatureTemplate,
    SILENCE_PEAK_THRESHOLD,
)
from rifflock.audio.recording import (
    RECORDING_CHANNELS,
    RECORDING_DTYPE,
    RECORDING_FAILURE_MESSAGE,
    AudioRecording,
    MicrophoneRecordingService,
)

__all__ = [
    "AudioRecording",
    "CHROMA_COUNT",
    "COMPARISON_FAILURE_MESSAGE",
    "FEATURE_EXTRACTION_FAILURE_MESSAGE",
    "MEL_BAND_COUNT",
    "MicrophoneRecordingService",
    "MIN_AUDIO_DURATION_SECONDS",
    "NOISE_FLATNESS_THRESHOLD",
    "RECORDING_CHANNELS",
    "RECORDING_DTYPE",
    "RECORDING_FAILURE_MESSAGE",
    "REQUIRED_RIFF_RECORDINGS",
    "RiffComparisonResult",
    "RiffEnrollmentResult",
    "RiffEnrollmentService",
    "RiffFeatureExtractionService",
    "RiffFeatureTemplate",
    "RiffSimilarityService",
    "RIFF_TEMPLATE_VERSION",
    "SILENCE_PEAK_THRESHOLD",
    "deserialize_riff_template",
    "serialize_riff_template",
]
