# Milestone 2 - Real audio pipeline

The repository now contains production-shaped adapters instead of hard-wiring ML libraries into the API.

## Runtime path

```text
POST /tracks
  -> persist uploaded file
  -> create background job
  -> Separator adapter
     -> Demucs baseline OR passthrough in dev
  -> BasicPitchTranscriber
  -> NoteEvent[]
  -> tuning-aware fingering optimizer
  -> artifacts/jobs/<job_id>/result.json
  -> GET /jobs/<job_id>
```

## Why adapters matter

Demucs is a baseline, not a permanent architectural dependency. The same `Separator` interface can later host a RoFormer implementation without changing API or product code.

`BasicPitchTranscriber` also hides Basic Pitch behind a stable internal interface so guitar-specific AMT models can be benchmarked later.

## Local ML setup

```bash
cd packages/audio_pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-ml.txt
```

For a clean single-guitar recording you can bypass source separation during development by posting `dev_passthrough=true`. This isolates transcription and fingering quality from source-separation quality.

## API workflow

1. `POST /tracks` multipart fields:
   - `file`: audio
   - `tuning`: e.g. `guitar_drop_d`
   - `dev_passthrough`: `true` for isolated guitar audio
2. Poll `GET /jobs/{job_id}` until `completed` or `failed`.

## Next engineering target

The next high-value step is **polyphonic fingering**. The current optimizer treats notes sequentially. Real guitar chords require grouping simultaneous notes into candidate voicings and optimizing those voicings across time.
