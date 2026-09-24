# First local run

This is the shortest path if you have not run AutoTab before.

## 1. Prerequisites

Install:

- Git
- Python 3.10 or newer
- Node.js 18 or newer (includes npm)

On macOS, if you already have Homebrew:

```bash
brew install git python node
```

You do **not** need to create a Python environment or run `npm install` manually.

## 2. Clone AutoTab

```bash
git clone https://github.com/gnefolo/autotab.git
cd autotab
```

## 3. Start the application

To see the UI and run the API:

```bash
./start-autotab.sh
```

AutoTab will open:

- Web app: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

Use `Ctrl+C` in the terminal to stop everything.

## 4. Enable real song analysis

The source-separation/transcription stack is much heavier, so install it only when you are ready to analyze real audio:

```bash
./start-autotab.sh --ml
```

This installs Basic Pitch and Demucs into the same local virtual environment and then launches AutoTab normally.

## Troubleshooting

### Permission denied

If your local checkout lost executable permissions:

```bash
chmod +x start-autotab.sh
./start-autotab.sh
```

### Port already in use

AutoTab needs ports 3000 and 8000. The launcher stops before starting if one is already occupied.

### Update to the latest version

From the repository directory:

```bash
git pull origin main
./start-autotab.sh
```
