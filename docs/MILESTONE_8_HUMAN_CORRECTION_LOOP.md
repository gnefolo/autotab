# Milestone 8 — Editor + Human Correction Loop (v0.8)

AutoTab now turns user corrections into constrained fingering decisions and reusable learning data.

## Implemented

- note-level TAB correction editor in the practice player
- editable string + fret for any generated TAB note
- physical validation: corrected string/fret must produce the same canonical MIDI pitch
- correction anchors that the optimizer must respect
- local re-optimization window around the corrected chord
- distant chords frozen to avoid song-wide fingering changes
- immediate MusicXML regeneration after a correction
- refreshed chord / barre / finger intelligence after a correction
- persistent per-job correction history as JSONL
- latest correction wins for the same chord/pitch
- correction count surfaced in the player
- correction history endpoint
- aggregate correction dataset endpoint for future ML training
- tests for valid anchors, invalid anchors and frozen distant chords

## API

`POST /jobs/{job_id}/corrections`

Example:

```json
{
  "tuning": "guitar_standard",
  "profile": "original_like",
  "capo": 0,
  "chord_index": 12,
  "pitch": 64,
  "string_index": 4,
  "fret": 5,
  "neighborhood_radius": 2
}
```

`GET /jobs/{job_id}/corrections` returns the job correction history.

`GET /corrections/dataset` aggregates all persisted prediction → correction records.

## Learning-data contract

Each correction stores:

- job id
- chord index
- canonical pitch
- predicted string/fret
- corrected string/fret
- tuning name
- capo
- playing profile
- UTC timestamp

This is intentionally simple and append-only. A later learned ranker can consume these records together with surrounding note/chord context.

## Important invariant

A user edit changes fingering, not musical pitch. If a requested string/fret does not sound the same canonical pitch, the API rejects it with HTTP 422.

## Next hardening

- direct click-to-edit mapping from rendered OSMD noteheads/TAB glyphs
- undo/redo rather than history clear only
- persistent database instead of local JSONL
- richer training context: neighboring notes, tempo, chord label, technique hints, source confidence
- learned candidate ranker trained from accepted corrections
