# AutoTab MVP v0.7

AutoTab turns audio into instrument stems, note events and playable tablature/notation. Its core differentiator is a tuning-aware fingering engine: detected musical pitches remain canonical while string/fret assignments are recomputed for the player's instrument and tuning.

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
