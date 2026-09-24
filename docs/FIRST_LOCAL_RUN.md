# First local run

## Standard UI/API

```bash
./start-autotab.sh
```

The standard launcher can use Python 3.10 or newer.

## Full song analysis on Apple Silicon

Spotify Basic Pitch officially supports Apple Silicon with Python 3.10. AutoTab therefore uses a separate `apps/api/.venv-ml` environment for full audio analysis and leaves the normal Python 3.12 environment untouched.

Install Python 3.10 once:

```bash
brew install python@3.10
```

Then:

```bash
./start-autotab.sh --ml
```

The launcher will ensure `ffmpeg` and `libsndfile` are available through Homebrew, install pinned Basic Pitch/Demucs versions, verify both imports, then start the API and web app.

Expected startup:

```text
[AutoTab] Using python3.10 (Python 3.10)
[AutoTab] Full audio-analysis stack: READY
```

## Why not Python 3.12 for ML on Apple Silicon?

Basic Pitch 0.4.0 documents Apple Silicon support specifically on Python 3.10. Using Python 3.12 can trigger TensorFlow/ONNX dependency backtracking and pip `resolution-too-deep`.

## Updating

```bash
git pull origin main
./start-autotab.sh --ml
```
