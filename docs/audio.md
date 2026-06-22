# Riff Audio and Feature Extraction

Last updated: 2026-06-22
Source issue: `HAM-133` / `RLD-029`

## Purpose

This document explains how RiffLock records, validates, transforms, and compares riff audio for optional 2FA.

The riff is an authentication factor only. It is not used directly as an encryption key.

## Recording flow

The MVP recording pipeline is:

1. capture mono microphone input
2. validate sample rate and duration
3. reject silence or clearly invalid input
4. normalize the signal
5. extract a stable comparison vector
6. serialize the enrolled template for storage

## Validation rules

The current extraction pipeline rejects audio when:

- the recording is not mono
- the sample array is empty
- the sample rate is invalid
- the signal contains non-finite values
- the duration is shorter than the minimum supported threshold
- the peak level is effectively silent
- the spectral flatness indicates excessively noisy audio

These checks help prevent weak or low-quality riff samples from becoming enrolled templates.

## Feature extraction approach

The current `RiffFeatureExtractionService` builds a single numeric vector from three groups of features.

### 1. Mel-style band summary

- compute FFT-based power values
- divide the frequency range into geometric bands
- summarize average energy per band
- log-scale the band energy values

This captures broad timbral structure without depending on exact raw samples.

### 2. Chroma summary

- compute spectral magnitudes
- map frequencies to pitch classes
- fold them into 12 chroma bins
- normalize the total energy

This gives the comparison pipeline a pitch-class fingerprint that is useful for guitar riffs.

### 3. Temporal and spectral summary

The current vector also includes:

- envelope mean
- envelope standard deviation
- zero-crossing rate
- spectral centroid
- spectral bandwidth
- spectral flatness
- onset-delta mean
- onset-delta standard deviation

These features help represent articulation, brightness, noisiness, and attack behavior.

## Comparison model

Enrollment stores a template built from multiple recordings. Verification extracts a fresh vector and compares it against the enrolled template using the similarity service and the configured threshold.

The acceptance threshold comes from app settings rather than UI hardcoding.

## Security and privacy rules

- raw audio is not used as an encryption key
- raw audio is not written to logs
- sensitive audio-derived data should not be exposed in user-facing errors
- if stored, template material must remain under local app control

## Limitations

- this is a pragmatic MVP signal-comparison approach, not a biometric identity guarantee
- noisy rooms, weak microphones, and inconsistent playing can reduce reliability
- feature design may evolve in future template versions
