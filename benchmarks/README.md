# AutoTab accuracy benchmarks

Milestone 16 introduces a repeatable benchmark contract for automatic music transcription.

## Ground-truth format

Reference and prediction files are JSON arrays of canonical note events:

```json
[
  {
    "pitch": 60,
    "start": 0.0,
    "duration": 0.5,
    "confidence": 1.0
  }
]
```

A top-level object with a `notes` array is also accepted.

Required fields:
- `pitch`: MIDI pitch, 0-127
- `start`: onset in seconds
- `duration`: duration in seconds

Optional:
- `confidence`
- `velocity`
- `pitch_bends`

## Run locally

```bash
python scripts/benchmark_accuracy.py \
  benchmarks/example_reference.json \
  benchmarks/example_prediction.json
```

Use a stricter or looser onset window:

```bash
python scripts/benchmark_accuracy.py \
  benchmarks/example_reference.json \
  benchmarks/example_prediction.json \
  --onset-tolerance 0.05
```

Machine-readable output:

```bash
python scripts/benchmark_accuracy.py \
  benchmarks/example_reference.json \
  benchmarks/example_prediction.json \
  --json
```

## Current metrics

- note precision
- note recall
- note F1
- false positives
- false negatives
- onset mean absolute error in milliseconds
- duration mean absolute error in milliseconds

Pitch is exact-MIDI for a match. Onset must fall within the configured tolerance.

## Recommended benchmark set

Build a versioned set of 20-30 manually verified excerpts rather than full copyrighted songs. Include:
- clean electric guitar
- distorted rhythm guitar
- lead guitar
- fast solo
- acoustic strumming
- fingerpicking
- Drop D / Drop C# / Drop C
- 7-string guitar
- bass
- dense full-mix material after separation

Each excerpt should include:
- audio identifier / internal source reference
- instrument
- tuning
- BPM / meter if known
- reference note JSON
- optional verified string/fret TAB
- model/version used for predictions

Do not commit copyrighted commercial audio to the public repository.

## API

For an analyzed job:

```
POST /jobs/{job_id}/benchmark
```

Example request:

```json
{
  "part": "guitar",
  "onset_tolerance": 0.08,
  "reference": [
    {"pitch": 60, "start": 0.0, "duration": 0.5}
  ]
}
```

The result is persisted under the job artifact directory as `benchmark-{part}.json`.
