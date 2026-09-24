# Architecture

## Product principle

The canonical representation is **not MIDI**. MIDI is an import/export format. Internally the app stores note events + timing + confidence + instrument/tuning metadata, then computes a playable fingering.

## Services

```text
Browser / Next.js
      |
      v
FastAPI orchestration API
      |
      +--> Object storage (original + stems)
      +--> Postgres (projects, tracks, note events, user edits)
      +--> Redis queue
              |
              v
          GPU worker
          1. normalize audio
          2. source separation
          3. instrument recognition
          4. audio-to-note transcription
          5. beat/tempo map
          6. rhythmic quantization
          7. fingering optimizer
          8. MusicXML + JSON artifacts
```

## Separation strategy

Keep a `Separator` interface. The initial baseline can use Demucs because it is easy to integrate and proven, but the original Meta repository is archived. Do not hard-wire the product to it. Add RoFormer-family implementations behind the same interface.

## Transcription strategy

Start with Basic Pitch on isolated monophonic/polyphonic stems. Keep an `AMTTranscriber` interface so guitar-specific models can be benchmarked later.

## Core entity

```json
{
  "track_id": "uuid",
  "instrument": "electric_guitar",
  "tempo_map": [{"time": 0.0, "bpm": 124.0}],
  "notes": [
    {
      "pitch": 62,
      "start": 1.203,
      "duration": 0.420,
      "velocity": 93,
      "confidence": 0.94,
      "string_index": 3,
      "fret": 7,
      "techniques": []
    }
  ]
}
```

## Why tuning changes do not require re-transcription

The detected pitch events are invariant. Changing tuning only changes the set of legal `(string, fret)` positions and therefore reruns the fingering optimizer.

## Next optimizer milestone: polyphony

Group events whose onsets overlap within a tolerance. Generate candidate chord voicings with constraints:
- one note per string;
- no duplicate string assignment;
- maximum hand span;
- optional barre detection;
- preserve bass note/voice leading;
- penalize large position changes between consecutive chords.

Solve with dynamic programming over candidate voicings.
