# Milestone 6 — Technique hints + stem mixer

## Added

- Preserves Basic Pitch pitch-bend trajectories in canonical `NoteEvent` data.
- Conservative technique-hint layer for bend, vibrato and same-string legato/slide candidates.
- Hints are labelled as heuristic/candidate outputs, not asserted as ground truth.
- Practice player exposes original + separated stems with independent volume, mute and solo.
- Stem transports follow the master audio playhead and playback speed.

## Why hints first

Hammer-ons, pull-offs, slides and palm muting cannot be reliably inferred from MIDI pitch alone. v0.6 therefore keeps these suggestions explicitly probabilistic. A dedicated audio technique classifier remains a later R&D milestone.
