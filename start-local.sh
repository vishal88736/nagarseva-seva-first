#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$PROJECT_DIR/nagarseva"
WEB_DIR="$APP_DIR/website"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
LOG_DIR="$PROJECT_DIR/.runtime/local"

command -v npm >/dev/null || { echo 'Node.js and npm are required.' >&2; exit 1; }
if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v uv >/dev/null; then
    uv venv --python 3.12 "$APP_DIR/.venv"
  elif command -v python3.12 >/dev/null; then
    python3.12 -m venv "$APP_DIR/.venv"
  else
    echo 'Install uv or Python 3.12, then run this launcher again.' >&2
    exit 1
  fi
fi

"$PYTHON_BIN" - <<'PY'
import socket
for port in (8000, 5173):
    with socket.socket() as server:
        try:
            server.bind(('127.0.0.1', port))
        except OSError as exc:
            raise SystemExit(f'Cannot use localhost:{port}: {exc}. Free this port before launching.')
PY

REQUIREMENTS_SHA="$("$PYTHON_BIN" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$APP_DIR/model/requirements-urban.txt")"
if [[ ! -f "$APP_DIR/.venv/.urban-requirements" ]] || [[ "$(cat "$APP_DIR/.venv/.urban-requirements")" != "$REQUIREMENTS_SHA" ]]; then
  if command -v uv >/dev/null; then
    uv pip install --python "$PYTHON_BIN" -r "$APP_DIR/model/requirements-urban.txt"
  else
    "$PYTHON_BIN" -m pip install -r "$APP_DIR/model/requirements-urban.txt"
  fi
  printf '%s' "$REQUIREMENTS_SHA" > "$APP_DIR/.venv/.urban-requirements"
fi

LOCK_SHA="$("$PYTHON_BIN" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$WEB_DIR/package-lock.json")"
if [[ ! -x "$WEB_DIR/node_modules/.bin/vite" ]] || [[ ! -f "$WEB_DIR/node_modules/.urban-lock" ]] || [[ "$(cat "$WEB_DIR/node_modules/.urban-lock")" != "$LOCK_SHA" ]]; then
  npm --prefix "$WEB_DIR" ci
  printf '%s' "$LOCK_SHA" > "$WEB_DIR/node_modules/.urban-lock"
fi

mkdir -p "$LOG_DIR"
SERVICE_PIDS=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${SERVICE_PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${SERVICE_PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$APP_DIR"
"$PYTHON_BIN" -m uvicorn model.api.urban:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
SERVICE_PIDS+=("$!")
cd "$WEB_DIR"
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort > "$LOG_DIR/web.log" 2>&1 &
SERVICE_PIDS+=("$!")

"$PYTHON_BIN" - "${SERVICE_PIDS[@]}" <<'PY'
import json, os, sys, time, urllib.request
pids = [int(pid) for pid in sys.argv[1:]]
for attempt in range(120):
    try:
        for pid in pids:
            os.kill(pid, 0)
        with urllib.request.urlopen('http://127.0.0.1:8000/urban/health', timeout=1) as response:
            assert json.load(response)['status'] == 'ok'
        with urllib.request.urlopen('http://127.0.0.1:5173', timeout=1) as response:
            assert response.status == 200
        break
    except ProcessLookupError:
        raise SystemExit('A server exited. Check .runtime/local/api.log and web.log.')
    except Exception:
        time.sleep(.5)
else:
    raise SystemExit('Local startup timed out. Check .runtime/local/api.log and web.log.')
PY

printf '\nUrbanSaarthi: http://localhost:5173\nAPI docs: http://localhost:8000/docs\nPress Ctrl+C to stop both servers. Logs: %s\n\n' "$LOG_DIR"
wait -n "${SERVICE_PIDS[@]}"
