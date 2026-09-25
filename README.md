# AutoTab MVP v0.25

AutoTab turns audio into instrument stems, note events and playable tablature/notation. Its core differentiator is a tuning-aware fingering engine: detected musical pitches remain canonical while string/fret assignments are recomputed for the player's instrument and tuning.

## One-command local start

### First run

Requirements already installed on your computer:

- Python 3.10+
- Node.js 18+
- npm
- Git

Clone the repository once:

```bash
git clone https://github.com/gnefolo/autotab.git
cd autotab
```

Then start AutoTab:

```bash
./start-autotab.sh
```

The launcher:

1. creates `apps/api/.venv` when missing;
2. installs API dependencies on the first run;
3. installs frontend packages when `node_modules` is missing;
4. checks ports 8000 and 3000;
5. starts FastAPI and Next.js;
6. opens `http://localhost:3000` automatically when possible;
7. stops both processes when you press `Ctrl+C`.

For the **full audio-analysis stack** including Basic Pitch + Demucs:

```bash
./start-autotab.sh --ml
```

The ML install is intentionally opt-in because PyTorch/Demucs is substantially heavier than the UI/API setup.

Useful options:

```bash
./start-autotab.sh --no-open
./start-autotab.sh --ml --no-open
./start-autotab.sh --help
```

## Working vertical slice

1. Upload audio + background-job API
2. Replaceable source-separation adapter (Demucs baseline)
3. Stem -> note events via Basic Pitch adapter
4. Canonical `NoteEvent` representation
5. Polyphonic guitar/bass fingering engine
6. Tuning-aware re-tabbing
7. **Rhythm quantization in musical ticks**
8. **MusicXML standard notation + TAB export**
9. Browser upload + job polling + notation metadata

## Rhythm / notation engine

AutoTab now converts second-based note events into a score-ready timeline:

- optional BPM override + onset-based fallback estimation
- configurable time signature with 4/4 fallback
- 480 divisions per quarter note
- sixteenth-note default quantization grid
- chord-safe onset quantization
- measure construction
- cross-bar ties
- standard staff + TAB staff
- tuning metadata + string/fret notation
- generated `score.musicxml` per analysis job

The `/notation` endpoint can also run `notes -> fingering -> quantization -> MusicXML` directly, making the score engine testable without ML inference.

## Test the core

```bash
python -m unittest discover -s packages/music_engine/tests -p 'test_*.py' -v
python -m unittest discover -s packages/audio_pipeline/tests -p 'test_*.py' -v
```

## Run API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs`.

## Run web scaffold

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Architecture principle

Source separation and AMT are replaceable infrastructure. AutoTab's proprietary layer is the conversion from musical transcription to realistic, playable, tuning-aware instrument fingering, followed by notation that preserves that fingering.

## Practice player

The next milestone is the Songsterr-like browser experience: render `score.musicxml`, synchronize the score cursor with audio, mix stems, change speed, loop A/B and edit notes/fingering interactively.

## Milestone 5 — Practice Player

The web client now renders generated MusicXML with OpenSheetMusicDisplay and adds:

- synchronized standard notation + tablature viewer;
- original-audio playback;
- playback speed from 0.5x to 2x;
- A/B loop markers;
- score cursor following playback;
- instant retuning from an existing transcription;
- API endpoints for MusicXML, source audio and separated stems.

Retuning does **not** rerun source separation or AMT. AutoTab reuses canonical note events, recalculates playable fingering, requantizes them against the existing tempo map and emits a new MusicXML score.

### Run the player

```bash
cd apps/web
npm install
npm run dev
```

The API defaults to `http://localhost:8000`. Override with `NEXT_PUBLIC_AUTOTAB_API`.


## Milestone 6
- Pitch-curve aware technique hints (bend/vibrato).
- Conservative legato/slide candidates.
- Browser stem mixer with volume, mute and solo.
- Master/stem transport synchronization.

## Milestone 7 — Guitar Intelligence
- chord and inversion recognition
- probable barre detection
- first-pass finger assignment
- capo-aware fingering
- 7/8-string presets
- custom 4–8 string tunings
- Easy / Rhythm / Lead / Original-like fingering profiles
- `POST /intelligence` API and intelligent retune controls


## Milestone 8 — Human Correction Loop
- note-level string/fret editor
- physically validated fingering corrections
- constrained local re-optimization around the edited chord
- persistent correction history per job
- regenerated MusicXML after every correction
- aggregate prediction → correction dataset endpoint for future learned ranking


## Milestone 9 — Learned Fingering Ranker
- pairwise linear ranker trained from human corrections
- deterministic, dependency-free training
- learned position preference blended with heuristic playability cost
- adjustable learned-ranker strength
- automatic deterministic fallback when no trained model exists
- ranker train/status API
- player controls to train, enable and tune the learned ranker


## Milestone 10 — Tuning Intelligence & Auto Setup

AutoTab now evaluates tuning compatibility after transcription, before the user generates the final TAB.

- ranks guitar or bass tuning presets from canonical transcribed notes;
- measures weighted playable-note coverage;
- penalizes notes below the instrument range;
- uses low-position and open-string evidence as ergonomic tie-breakers;
- exposes `GET /jobs/{job_id}/tuning-suggestions`;
- shows suggestions only after audio analysis;
- keeps the decision with the user: a suggestion is selected, never silently applied;
- clearly labels the result as compatibility inference, not proof of the original recorded tuning.

The intended flow is now:

`Upload & Analyze -> Tuning / Instrument Setup -> Generate TAB -> Practice & Correct`.


## Milestone 11 — Multi-Instrument Intelligence

AutoTab now keeps independent pitched-instrument transcriptions after source separation.

- guitar baseline: Demucs `other` -> Basic Pitch guitar range;
- bass: Demucs `bass` -> Basic Pitch bass range;
- canonical note events are stored independently in `result.tracks`;
- the user chooses Guitar or Bass after analysis;
- tuning suggestions are computed from the selected part;
- changing part, tuning, profile or capo regenerates TAB without rerunning Demucs or Basic Pitch;
- correction histories are isolated by instrument part;
- the learned fingering ranker remains guitar-only until a bass-specific model is trained.

The current baseline intentionally does not claim Guitar 1 / Guitar 2 separation: Demucs `other` remains the guitar source until a guitar-specialized separator/classifier is introduced.


## Milestone 12 — Six-Stem Guitar Routing

AutoTab now prefers the official Demucs `htdemucs_6s` model, which provides six stems: drums, bass, other, vocals, piano and guitar.

- `guitar.wav` is used directly for guitar transcription when available;
- `bass.wav` continues to feed the bass transcription path;
- `piano.wav` is exposed in the mixer but is not sent to the string-fingering engine;
- if `htdemucs_6s` fails, AutoTab automatically falls back to `htdemucs`;
- the legacy `other.wav` guitar baseline remains available under that fallback;
- diagnostics report the preferred and fallback separation models.

This milestone improves source quality without changing the user's flow: upload once, analyze once, then choose the instrument part and setup before generating TAB.


## Milestone 13 — Piano / Keys Score Mode

AutoTab now treats the six-stem Demucs `piano` source as a score-only instrument part.

- Piano / Keys appears alongside Guitar and Bass after analysis;
- the piano stem is transcribed with a wider Basic Pitch frequency range;
- selecting Piano hides string-specific controls such as tuning, capo, fingering profile and correction editor;
- the generated MusicXML contains standard notation only, with no TAB staff or string/fret technical notation;
- playback, score cursor, zoom and the existing practice workspace remain available;
- the piano stem remains independently controllable in the mixer.

This is an initial piano baseline. Grand staff, hand assignment, pedal inference and piano-specific transcription refinement remain future work.


## Milestone 14 — Drum Transcription Baseline

AutoTab now converts the separated `drums` stem into structured percussion events.

- onset detection runs directly on the isolated drum stem;
- spectral-band energy classifies events as kick, snare, hi-hat, tom or cymbal;
- events are mapped to General MIDI drum notes;
- Drums appears as a selectable post-analysis part;
- the generated score uses percussion-clef MusicXML and unpitched notation;
- quantized proxy events keep the score cursor synchronized with playback;
- tuning, capo and string-fingering controls are hidden in drum mode.

The current classifier is an explainable deterministic baseline and is designed to be replaced by a dedicated learned drum-transcription model later.


## Milestone 15 — Guitar Role Intelligence

AutoTab now derives two optional virtual guitar views from the same transcribed guitar stem:

- Rhythm Guitar: chordal/polyphonic onset groups and lower-register supporting material;
- Lead Guitar: higher-register, sustained and melodic singleton runs;
- both parts reuse the normal tuning, fingering, correction and learned-ranker workflow;
- the original full Guitar part remains available;
- role confidence and explanatory metadata are stored with each inferred part.

These are explicitly labeled as inferred parts. They are not claimed to be source-separated Guitar 1 / Guitar 2 audio stems.


## Milestone 16 — Accuracy Engine & Benchmark Suite

AutoTab now measures transcription quality before trying to optimize more downstream features.

- note-event precision, recall and F1;
- configurable onset tolerance;
- onset and duration MAE in milliseconds;
- false-positive / false-negative counts;
- per-part confidence summaries and 2-second weak-section windows;
- clickable confidence timeline before TAB generation and inside the practice workspace;
- direct audition of weak sections against the original audio;
- `GET /jobs/{job_id}/confidence`;
- `POST /jobs/{job_id}/benchmark`;
- persisted per-job benchmark results;
- dependency-free CLI benchmark runner in `scripts/benchmark_accuracy.py`;
- example ground-truth/prediction fixtures under `benchmarks/`;
- benchmark smoke-test in CI.

The current metrics establish the Basic Pitch baseline. The next accuracy work should compare guitar-specific AMT models and ensemble strategies against this same benchmark contract rather than choosing models by subjective impression.


## Milestone 17 — Guitar AMT Consensus & Cleanup

The guitar path no longer trusts a single Basic Pitch pass.

- three passes are run with sensitive, balanced and conservative thresholds;
- same-pitch events are clustered within a 70 ms onset window;
- notes supported by at least two passes are retained;
- isolated notes survive only when confidence is very high;
- timing and duration are merged with median estimates;
- a conservative cleanup removes short low-confidence artifacts and near-duplicate retriggers;
- impossible clusters are capped to six simultaneous guitar notes;
- UI/API diagnostics expose the active transcription engine: `basic-pitch-3pass-consensus+cleanup`.

This baseline prioritizes precision over recall, targeting the false-note problem observed on sparse guitar recordings.


## Milestone 18 — Repeated Riff Consistency

AutoTab now compares repeated guitar phrases before fingering/TAB generation.

- short phrases are grouped by rhythm and surrounding pitch context;
- at least three independent occurrences are required;
- only low-confidence, small pitch disagreements are corrected;
- high-confidence or larger musical variations are preserved;
- diagnostics expose how many riff-consistency corrections were applied.

## Milestone 19 — Dual Guitar Source Selection

For sparse recordings, especially voice + guitar, AutoTab now compares two separation sources:

- `htdemucs_6s:guitar`;
- `htdemucs:other` exposed internally as `guitar_alt`.

Both candidates are transcribed with the same three-pass guitar consensus engine. AutoTab scores confidence stability, low-confidence ratio, micro-note artifacts, density and completeness, then selects the more stable source before riff cleanup and fingering. The UI shows the chosen source and both candidate scores.


## Milestone 20 — Refine Transcription Workflow

After the initial analysis, guitar transcription can now be refined without rerunning Demucs.

Available AMT profiles:
- **Precise**: stricter thresholds and cleanup, intended to reduce false positives;
- **Balanced**: the default three-pass consensus;
- **Sensitive**: looser thresholds, intended to recover more notes.

The user can also choose the guitar source:
- **Auto**: compare available sources and select the most stable;
- **guitar**: force the dedicated six-stem guitar source;
- **guitar_alt**: force the four-stem `other` source;
- **other**: legacy four-stem source when no dedicated guitar stem is available.

Refinement updates canonical guitar notes, confidence diagnostics, inferred Rhythm/Lead views, tuning suggestions, source-selection diagnostics and riff-consistency cleanup while preserving the already-computed separation artifacts.


## Milestone 21 — Fix This Section

Low-confidence windows are now actionable.

- click a weak section in the confidence map;
- audition it against the original audio;
- rerun only that short section with the selected Precise / Balanced / Sensitive profile;
- optionally force a specific guitar source;
- replace only events whose onset falls inside the chosen window;
- keep the rest of the transcription untouched;
- refresh confidence, riff consistency and inferred Rhythm/Lead views afterwards.

Section refinement is limited to 30 seconds and reuses the already-separated stems, so Demucs is not rerun.


## Milestone 22 — Songsterr-style Score Playhead

The score/TAB workspace now has a dedicated high-contrast vertical playhead.

- playback visuals run through `requestAnimationFrame`;
- OSMD cursor advancement is incremental during normal playback;
- seek/backward jumps rebuild cursor position safely;
- the viewport auto-scrolls as the active event changes system;
- a now-playing badge shows the active event and string:fret fingering;
- AutoTab targets OSMD's real `cursorImg-*` SVG cursor and keeps an overlay fallback visible if the cursor DOM is delayed.

## Milestone 23 — Guitar-Specific AMT Second Opinion

AutoTab can optionally compare its default guitar transcription with a pretrained guitar-specific model.

Install the optional model with:

```bash
./start-autotab.sh --ml --guitar-model
```

The second opinion:
- does not replace the main transcription automatically;
- uses the currently selected guitar source;
- compares exact MIDI pitch plus onset proximity;
- reports model-agreement F1 and support ratios for both engines;
- persists a disagreement report per job;
- is surfaced directly in the post-analysis accuracy panel.

The external guitar-specific model remains experimental and is treated as a second opinion rather than the default for polyphonic strumming.


## Milestone 24 — Disagreement-Aware Ensemble

AutoTab no longer treats model disagreement as a binary failure or blindly unions both transcriptions.

After running Guitar second opinion, the ensemble review:

- classifies events as confirmed, primary-only or secondary-only;
- validates disagreements against AMT confidence, note duration, physical guitar range, chord context and melodic neighbors;
- marks each disagreement as `keep`, `review` or `reject`;
- builds a conservative safe-note proposal;
- keeps review notes out of that proposal until the user verifies them;
- makes critical disagreements directly auditionable from the UI;
- applies the safe ensemble only after explicit user confirmation.

Endpoints:

```
POST /jobs/{job_id}/ensemble-review
POST /jobs/{job_id}/ensemble-apply
```

Applying the ensemble refreshes canonical guitar notes, confidence diagnostics, repeated-riff consistency and inferred Rhythm/Lead views. The default behavior remains non-destructive until the user chooses **Apply safe ensemble**.
