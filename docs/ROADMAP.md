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


## Milestone 17 - Guitar AMT Consensus & Cleanup - DONE (v0.17 baseline)
- run three Basic Pitch passes for guitar with sensitive, balanced and conservative thresholds
- cluster same-pitch events across runs within a 70 ms onset tolerance
- keep notes supported by at least two passes
- retain single-pass events only at very high confidence
- merge timing/duration using median estimates
- derive consensus confidence from model agreement + AMT confidence
- remove short low-confidence micro-notes
- collapse near-duplicate retriggers
- cap impossible simultaneous guitar polyphony to six notes
- expose the active transcription engine in UI/API diagnostics
- keep bass, piano and drums on their existing dedicated paths
- tests cover consensus, timing merge, confidence, duplicate suppression and impossible polyphony

This milestone targets precision first: fewer false notes and fewer AMT artifacts on sparse guitar recordings.

Remaining hardening: benchmark consensus against verified ground truth, guitar-specific learned AMT, calibration by playing style, direct single-instrument bypass mode, repeated-riff consensus and section re-analysis.


## Milestone 18 - Repeated Riff Consistency - DONE (v0.18 baseline)
- detect short repeated guitar phrases using rhythm + pitch context
- compare repeated occurrences with one wildcard note position
- require at least three independent phrase occurrences
- correct only low-confidence pitch outliers
- preserve high-confidence musical variations
- preserve large pitch changes that may represent a real variation
- apply corrections before fingering/TAB generation
- expose riff correction count in API/UI diagnostics
- tests cover low-confidence correction and variation preservation

Remaining hardening: phrase segmentation from beat/downbeat structure, transposition-aware motif matching, duration/onset consensus, repeated-chord consistency and section-level re-analysis.


## Milestone 19 - Dual Guitar Source Selection - DONE (v0.19 baseline)
- run preferred Demucs six-stem separation and also collect the four-stem `other` source as `guitar_alt`
- transcribe both guitar-source candidates with the same v0.17 consensus+cleanup AMT
- score source quality using consensus confidence, low-confidence ratio, micro-note ratio, note density and completeness
- choose the more stable guitar source before riff consistency/fingering
- keep deterministic tie-breaking toward the dedicated six-stem guitar source
- expose selected source and candidate scores in the UI
- retain both source stems in the mixer for manual listening comparison
- tests cover noisy-source rejection, empty-candidate rejection and deterministic ties

This milestone is particularly targeted at sparse recordings such as voice + guitar, where the four-stem `other` source can sometimes preserve guitar attacks better than the six-stem dedicated guitar output.

Remaining hardening: benchmark source selection against verified ground truth, learn source-quality scoring from data, allow manual source override, cache dual-separation outputs, and compare additional separators.


## Milestone 20 - Refine Transcription Workflow - DONE (v0.20 baseline)
- add post-analysis guitar retranscription without rerunning Demucs
- AMT profiles: precise, balanced and sensitive
- precise profile raises thresholds and cleanup strictness to reduce false positives
- sensitive profile lowers thresholds to recover more notes
- allow source mode: auto, dedicated six-stem guitar, alternate four-stem guitar source
- rebuild confidence diagnostics after refinement
- rebuild Rhythm Guitar / Lead Guitar inferred parts after refinement
- refresh tuning suggestions against the new canonical note events
- expose the active AMT profile through transcription engine metadata
- preserve source selection and repeated-riff consistency after refinement
- tests cover preset construction and strictness ordering

This milestone adds the expert override workflow observed in mature transcription products while preserving AutoTab's simple default flow: upload -> analyze -> optionally refine -> setup -> generate TAB.

Remaining hardening: asynchronous refinement jobs, A/B compare between refinements, automatic profile recommendation, section-only retranscription, model ensembles beyond Basic Pitch and persistent refinement history.


## Milestone 21 - Fix This Section - DONE (v0.21 baseline)
- reanalyze only a selected low-confidence guitar window without rerunning Demucs
- extract the requested section from the already-separated guitar source with FFmpeg
- use the currently selected precise/balanced/sensitive AMT profile
- optionally force auto / guitar / guitar_alt / other source
- replace only note events whose onset falls inside the selected window
- preserve the rest of the song unchanged
- rerun repeated-riff consistency after local replacement
- refresh confidence diagnostics and inferred Rhythm/Lead parts
- expose one-click section repair actions directly on weak-confidence windows
- cap a local refinement request at 30 seconds
- tests cover safe note-window replacement semantics

This milestone turns the confidence map from a passive diagnostic into an actionable correction workflow.

Remaining hardening: asynchronous section jobs, automatic mode recommendation per weak window, A/B preview before accepting a section replacement, undo/redo for section refinements, and guitar-specific second-opinion models.


## Milestone 22 - Songsterr-style Score Playhead - DONE (v0.22 baseline)
- add a dedicated high-contrast vertical playhead over the rendered score/TAB
- drive playback visuals with requestAnimationFrame instead of relying only on audio timeupdate
- advance the OSMD cursor incrementally during normal playback
- rebuild cursor position only on seek/backward jumps
- auto-scroll the score when the current event leaves the comfortable viewport
- show the active chord/event and current string:fret fingering in a now-playing badge
- target the actual OSMD SVG cursor ids (cursorImg-*) with a visible native-cursor fallback
- keep an overlay fallback visible even if OSMD exposes the cursor DOM late

Remaining hardening: click-to-seek directly on rendered notation, beat-level interpolation between note onsets, multi-staff playhead geometry and mobile viewport tuning.


## Milestone 23 - Guitar-Specific AMT Second Opinion - DONE (v0.23 baseline)
- integrate an optional pretrained guitar-specific transcription adapter based on hf-midi-transcription
- keep it opt-in rather than replacing the default polyphonic Basic Pitch consensus
- add launcher flag: --ml --guitar-model
- compare primary and guitar-specific note events with pitch + onset agreement
- report primary support ratio, secondary support ratio and model-agreement F1
- persist disagreement diagnostics per job
- expose second-opinion controls and agreement metrics in the post-analysis UI
- surface model availability through ML diagnostics
- tests cover exact agreement, pitch disagreements and onset tolerance

The guitar-specific model is treated as a second opinion because its published usage is strongest on solo/monophonic material; it is not automatically trusted for dense chordal strumming.

Remaining hardening: benchmark on verified AutoTab corpus, section-level second opinion, confidence calibration, polyphonic guitar-specific models with direct tablature output, and safe ensemble fusion.
