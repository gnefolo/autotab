# Milestone 3 - Polyphonic Fingering Engine

AutoTab v0.3 treats near-simultaneous AMT note onsets as a single musical event instead of optimizing each note as a fake arpeggio.

## Implemented

- onset clustering with a configurable tolerance (default 35 ms)
- duplicate-pitch cleanup by confidence
- legal string/fret positions per note and tuning
- chord voicing enumeration with one note per string
- maximum fret-span constraint
- intrinsic playability cost for compact shapes
- preference for useful open strings
- penalties for skipped strings and awkward open/high-fret mixtures
- dynamic programming across successive voicings
- `chord_index` in TAB output
- the full audio pipeline now invokes the polyphonic optimizer

## Key invariant

The transcription stores pitch independently from fingering. Changing tuning recomputes string/fret assignments without changing the detected pitches or rerunning AMT.

## Current limitations

- no barre/finger-number model yet
- no explicit chord-name recognition yet
- onset tolerance is fixed rather than tempo-adaptive
- overlapping sustained notes are grouped by onset only
- no technique-aware fingering cost yet
- candidate pruning is heuristic, capped at 256 voicings per group

## Acceptance examples

### Drop D open power chord

Pitches: D2, A2, D3

Expected playable shape:

```text
D|--0--
A|--0--
D|--0--
```

Internally this is strings 0/1/2 at fret 0 (strings are indexed low-to-high).

### Impossible voicing

Seven distinct simultaneous pitches on a six-string guitar are rejected instead of being silently mapped to an invalid TAB.
