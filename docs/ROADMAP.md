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


## Milestone 10 - Tuning Intelligence & Auto Setup - DONE (v0.10 baseline)
- post-transcription tuning compatibility ranking
- guitar/bass family filtering
- weighted playable-range coverage
- low-note incompatibility detection
- ergonomic scoring using minimum fret position and open strings
- explainable per-tuning diagnostics
- post-analysis tuning suggestions in Step 2
- user-controlled selection; no automatic tuning override
- IT/EN workflow preserved

Remaining hardening: infer likely recorded tuning from pitch-class/fretboard context, detect detuned reference pitch, use chord voicings and spectral/string-resonance evidence, and learn tuning priors from user corrections.


## Milestone 11 - Multi-Instrument Intelligence - DONE (v0.11 baseline)
- independent post-separation transcription for guitar and bass
- Demucs `other` routed to guitar baseline and `bass` routed to bass
- dedicated Basic Pitch frequency ranges for guitar and bass
- per-job `tracks` map with canonical notes per instrument part
- `GET /jobs/{job_id}/parts` API
- part-aware tuning suggestions
- part-aware retune / TAB regeneration without re-running separation or AMT
- part-scoped human correction history and corrected score files
- learned fingering ranker restricted to guitar baseline
- post-analysis Guitar / Bass selector in IT/EN UI

Remaining hardening: guitar-specific source separation, Guitar 1 / Guitar 2 identification, vocals/instrument classification, drum transcription, per-part tempo/voice handling, per-instrument technique models, and learned part recognition.


## Milestone 12 - Six-Stem Guitar Routing - DONE (v0.12 baseline)
- prefer official Demucs `htdemucs_6s` for drums, bass, other, vocals, piano and guitar
- automatic fallback to `htdemucs` when six-stem separation fails
- direct Guitar stem routing when `guitar.wav` is available
- legacy `other.wav` guitar fallback retained
- Bass stem routing preserved
- Piano stem exposed in the mixer but intentionally not sent to the string-fingering engine
- diagnostics expose preferred and fallback separation models
- tests verify direct guitar routing and piano stem availability

Remaining hardening: guitar-specific multi-guitar separation, Guitar 1 / Guitar 2 / lead-rhythm classification, piano score transcription, drum event transcription, and separator benchmarking on real songs.


## Milestone 13 - Piano / Keys Score Mode - DONE (v0.13 baseline)
- transcribe the six-stem Demucs `piano` source with a dedicated Basic Pitch range
- expose Piano / Keys as a selectable post-analysis part
- mark piano as a score-only part rather than a string-fingering part
- generate standard-notation-only MusicXML for piano
- keep playback, cursor sync, zoom and score workspace available
- hide tuning, capo, learned ranker and string/fret correction controls for piano
- keep piano stem in the mixer
- tests verify piano extraction and MusicXML without TAB staff

Remaining hardening: grand-staff split between treble/bass clefs, sustain pedal inference, hand assignment, voice separation, key-aware spelling, piano-specific quantization and benchmark against dedicated piano transcription models.


## Milestone 14 - Drum Transcription Baseline - DONE (v0.14 baseline)
- process the separated Demucs `drums` stem with a deterministic onset detector
- classify hits into kick, snare, hi-hat, tom and cymbal using spectral-band energy
- map detected hits to General MIDI drum notes
- expose Drums as a selectable post-analysis part
- generate percussion-clef MusicXML with unpitched drum notation
- keep score cursor synchronization through quantized proxy events
- hide tuning, capo and string-fingering controls for drums
- preserve the raw drum stem in the mixer
- tests cover spectral classification, pipeline integration and percussion MusicXML

Remaining hardening: replace heuristic classification with a dedicated drum transcription model, velocity estimation, open/closed hi-hat distinction, ride/crash separation, ghost notes, flams, rolls, triplets, tempo-map alignment and benchmark against annotated drum datasets.


## Milestone 15 - Guitar Role Intelligence - DONE (v0.15 baseline)
- infer virtual Rhythm Guitar and Lead Guitar parts from one transcribed guitar stem
- assign polyphonic onset groups to rhythm guitar
- assign higher-register, sustained and melodic singleton runs to lead guitar
- expose role confidence and explanation metadata
- clearly label role parts as inferred, not source-separated Guitar 1 / Guitar 2
- reuse guitar tuning intelligence, fingering engine, human corrections and learned ranker
- keep the original full Guitar part available alongside inferred role views
- tests cover chord-vs-melody role assignment and empty-input safety

Remaining hardening: true multi-guitar source separation, learned rhythm/lead classifier, phrase-level role tracking, handling harmonized leads, double-tracked guitars and confidence calibration against multitrack datasets.


## Milestone 16 - Accuracy Engine & Benchmark Suite - DONE (v0.16 baseline)
- objective note-event evaluation with precision, recall and F1
- exact-MIDI pitch matching with configurable onset tolerance
- onset and duration mean absolute error in milliseconds
- false-positive and false-negative counts
- per-part confidence summaries derived from AMT confidence
- 2-second confidence windows and weak-section detection
- clickable confidence timeline in setup and practice workspace
- pre-TAB audition of low-confidence sections against original audio
- `GET /jobs/{job_id}/confidence` API
- `POST /jobs/{job_id}/benchmark` API with persisted per-job metrics
- reusable `scripts/benchmark_accuracy.py` CLI
- documented JSON ground-truth contract and benchmark fixtures
- CI smoke-test for the benchmark runner

This milestone intentionally measures the current Basic Pitch baseline before replacing or ensembling it.

Remaining hardening: real verified benchmark corpus, guitar-specific AMT adapters, ensemble transcription, repeated-riff consistency, beat/downbeat alignment, calibration of confidence scores, string/fret ground-truth metrics and section-level re-analysis.
