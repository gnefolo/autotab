#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"
VENV="$API_DIR/.venv"
CORE_MARKER="$VENV/.autotab-core-ready"
ML_MARKER="$VENV/.autotab-ml-ready"
INSTALL_ML=0
OPEN_BROWSER=1
API_PID=""
WEB_PID=""

usage() {
  cat <<'EOF'
AutoTab local launcher

Usage:
  ./start-autotab.sh [options]

Options:
  --ml        Install the optional Basic Pitch + Demucs ML stack.
  --no-open   Do not open the browser automatically.
  --help      Show this help.

Examples:
  ./start-autotab.sh
  ./start-autotab.sh --ml
EOF
}

for arg in "$@"; do
  case "$arg" in
    --ml) INSTALL_ML=1 ;;
    --no-open) OPEN_BROWSER=0 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $arg"; usage; exit 2 ;;
  esac
done

log() {
  printf '\n[AutoTab] %s\n' "$1"
}

fail() {
  printf '\n[AutoTab] ERROR: %s\n' "$1" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$2"
}

version_major() {
  printf '%s' "$1" | sed -E 's/[^0-9]*([0-9]+).*/\1/'
}

need_command node "Node.js 18+ is required. Install it from nodejs.org or with Homebrew: brew install node"
need_command npm "npm is required and normally ships with Node.js."

PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    VERSION="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    MAJOR="$(printf '%s' "$VERSION" | cut -d. -f1)"
    MINOR="$(printf '%s' "$VERSION" | cut -d. -f2)"
    if [ "$MAJOR" -gt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; }; then
      PYTHON_BIN="$candidate"
      PY_VERSION="$VERSION"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  fail "Python 3.10+ is required. Install Python 3.12 with: brew install python@3.12"
fi

log "Using $PYTHON_BIN (Python $PY_VERSION)"

NODE_VERSION="$(node --version)"
NODE_MAJOR="$(version_major "$NODE_VERSION")"
if [ "$NODE_MAJOR" -lt 18 ]; then
  fail "Node.js 18+ is required. Found $NODE_VERSION."
fi

port_busy() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

if port_busy 8000; then
  fail "Port 8000 is already in use. Stop the process using it and run AutoTab again."
fi
if port_busy 3000; then
  fail "Port 3000 is already in use. Stop the process using it and run AutoTab again."
fi

if [ ! -x "$VENV/bin/python" ]; then
  log "Creating Python virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV"
fi

if [ ! -f "$CORE_MARKER" ]; then
  log "Installing backend dependencies (first run)..."
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install -r "$API_DIR/requirements.txt"
  touch "$CORE_MARKER"
fi

if [ "$INSTALL_ML" -eq 1 ] && [ ! -f "$ML_MARKER" ]; then
  log "Installing optional ML dependencies. This is the heavy first-run step..."
  "$VENV/bin/python" -m pip install -r "$ROOT/packages/audio_pipeline/requirements-ml.txt"
  touch "$ML_MARKER"
fi

if [ ! -d "$WEB_DIR/node_modules" ]; then
  log "Installing frontend dependencies (first run)..."
  (cd "$WEB_DIR" && npm install)
fi

cleanup() {
  trap - INT TERM EXIT
  log "Stopping AutoTab..."
  if [ -n "$WEB_PID" ] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$API_PID" ] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  wait "$WEB_PID" >/dev/null 2>&1 || true
  wait "$API_PID" >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

log "Starting AutoTab API on http://localhost:8000 ..."
(
  cd "$API_DIR"
  exec "$VENV/bin/python" -m uvicorn app.main:app --reload --port 8000
) &
API_PID=$!

log "Starting AutoTab web app on http://localhost:3000 ..."
(
  cd "$WEB_DIR"
  exec npm run dev -- -p 3000
) &
WEB_PID=$!

wait_for_url() {
  local url="$1"
  local attempts=0
  if ! command -v curl >/dev/null 2>&1; then
    sleep 3
    return 0
  fi
  until curl -fsS "$url" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 60 ]; then
      return 1
    fi
    if ! kill -0 "$API_PID" >/dev/null 2>&1 || ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
      return 1
    fi
    sleep 1
  done
}

if wait_for_url "http://localhost:3000"; then
  log "AutoTab is ready: http://localhost:3000"
  printf '[AutoTab] API docs: http://localhost:8000/docs\n'
  if [ "$INSTALL_ML" -eq 0 ]; then
    printf '[AutoTab] ML stack not requested. For full audio analysis, restart with: ./start-autotab.sh --ml\n'
  fi
  if [ "$OPEN_BROWSER" -eq 1 ]; then
    if command -v open >/dev/null 2>&1; then
      open "http://localhost:3000" >/dev/null 2>&1 || true
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "http://localhost:3000" >/dev/null 2>&1 || true
    fi
  fi
else
  fail "AutoTab did not become ready. Check the backend/frontend errors printed above."
fi

log "Running. Press Ctrl+C to stop both frontend and backend."
wait
