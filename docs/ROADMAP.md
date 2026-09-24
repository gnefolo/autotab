# Build Roadmap

## Milestone 1 - Core engine - DONE
- note-event model
- tuning presets
- legal string/fret generation
- monophonic dynamic-programming optimizer
- FastAPI contract
- upload UI scaffold

## Milestone 2 - Real audio pipeline - DONE (baseline)
- separator adapter
- Basic Pitch adapter
- stems + raw note events
- job model and progress polling

Remaining production hardening: FFmpeg normalization, GPU worker deployment, modern separator benchmark.

## Milestone 3 - Polyphonic TAB - DONE (v0.3 baseline)
- chord/onset clustering
- legal voicing generation
- unique-string constraint
- fret-span/playability constraints
- dynamic programming across voicings
- power-chord/open-string heuristics
- tuning-aware re-tab

## Milestone 4 - Musical timing / notation - DONE (v0.4 baseline)
- onset-derived BPM fallback + explicit override
- time-signature model with 4/4 fallback
- onset and duration quantization
- measures, rests and cross-bar ties
- standard notation + TAB MusicXML export
- tuning + string/fret metadata

Remaining production hardening: audio beat/downbeat tracker, tempo maps, tuplets/swing, multi-voice sustain, external MuseScore/OSMD visual QA.

## Milestone 5 - Songsterr-like viewer
- OSMD score + TAB
- audio cursor sync
- stem mixer
- playback speed
- A/B loop
- note/string/fret editor
- instant tuning switch

## Milestone 7 - Guitar intelligence - DONE (v0.7 baseline)
- chord naming and inversion detection
- barre recognition
- first-pass finger assignment
- style profiles: rhythm / lead / easy / original-like
- capo support
- 7/8-string guitar and custom tunings

Remaining hardening: harmonic context/key-aware spelling, richer extensions, finger biomechanics model and learned original-performance ranking.

## Milestone 7 - Techniques
- bend from pitch curves
- slide/glissando
- hammer-on / pull-off
- vibrato
- palm mute classifier
- harmonics

## Milestone 8 - Learning loop - DONE (v0.8 baseline)
- AI prediction + human correction history
- fingering choices by tuning/instrument/style
- constrained local re-optimization around human anchors
- persistent JSONL correction dataset
- aggregate training-data API

Remaining hardening: direct score-glyph editing, undo/redo, database persistence and richer context features.

## Milestone 9 - Learned Fingering Ranker - DONE (v0.9 baseline)
- pairwise preference learning from prediction → correction records
- lightweight linear model with deterministic training
- learned cost blended with heuristic playability
- adjustable ranker strength
- safe fallback when no model/data exists
- model train/status API
- player controls for training and activation

Remaining hardening: validation split/metrics, per-user and global models, richer contextual features, online learning and a nonlinear ranker once enough data exists.


## Milestone 5 — Practice player ✅
MusicXML viewer, synchronized audio cursor, speed controls, A/B loop and instant retuning are implemented in v0.5.

## Milestone 6 — Expressive guitar transcription
Next: technique detection (bend, slide, hammer-on/pull-off, palm mute), tempo maps and multi-stem practice mixer.
