#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$PROJECT_DIR/nagarseva"
WEB_DIR="$APP_DIR/website"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
API_PORT="${URBANSAARTHI_API_PORT-8000}"
WEB_PORT="${URBANSAARTHI_WEB_PORT-5173}"
validate_port() {
  local name="$1" value="$2"
  if [[ ! "$value" =~ ^[0-9]{1,5}$ ]] || (( 10#$value < 1 || 10#$value > 65535 )); then
    printf '%s must be an integer from 1 to 65535.\n' "$name" >&2
    exit 1
  fi
}
validate_port URBANSAARTHI_API_PORT "$API_PORT"
validate_port URBANSAARTHI_WEB_PORT "$WEB_PORT"
API_PORT=$((10#$API_PORT))
WEB_PORT=$((10#$WEB_PORT))
if [[ "$API_PORT" == "$WEB_PORT" ]]; then
  echo 'URBANSAARTHI_API_PORT and URBANSAARTHI_WEB_PORT must be different.' >&2
  exit 1
fi
LOG_DIR="$PROJECT_DIR/.runtime/local/$API_PORT-$WEB_PORT"
export NAGARSEVA_API_TARGET="http://127.0.0.1:$API_PORT"

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

"$PYTHON_BIN" - "$API_PORT" "$WEB_PORT" <<'PY'
import socket, sys
for port in map(int, sys.argv[1:]):
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('127.0.0.1', port))
        except OSError as exc:
            raise SystemExit(f'Cannot use localhost:{port}: {exc}. Choose unused URBANSAARTHI_API_PORT and URBANSAARTHI_WEB_PORT values; existing listeners are left untouched.')
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
"$PYTHON_BIN" -m uvicorn model.api.urban:app --host 127.0.0.1 --port "$API_PORT" > "$LOG_DIR/api.log" 2>&1 &
SERVICE_PIDS+=("$!")
cd "$WEB_DIR"
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$WEB_PORT" --strictPort > "$LOG_DIR/web.log" 2>&1 &
SERVICE_PIDS+=("$!")

"$PYTHON_BIN" - "$API_PORT" "$WEB_PORT" "${SERVICE_PIDS[@]}" <<'PY'
import json, os, sys, time, urllib.request
api_port, web_port = map(int, sys.argv[1:3])
pids = [int(pid) for pid in sys.argv[3:]]
for attempt in range(120):
    try:
        for pid in pids:
            os.kill(pid, 0)
        with urllib.request.urlopen(f'http://127.0.0.1:{api_port}/urban/health', timeout=1) as response:
            assert json.load(response)['status'] == 'ok'
        with urllib.request.urlopen(f'http://127.0.0.1:{web_port}', timeout=1) as response:
            assert response.status == 200
        with urllib.request.urlopen(f'http://127.0.0.1:{web_port}/api/urban/data/health', timeout=1) as response:
            assert json.load(response)['status'] == 'ok'
        break
    except ProcessLookupError:
        raise SystemExit(f'A server exited. Check .runtime/local/{api_port}-{web_port}/api.log and web.log.')
    except Exception:
        time.sleep(.5)
else:
    raise SystemExit(f'Local startup timed out. Check .runtime/local/{api_port}-{web_port}/api.log and web.log.')
PY

printf '\nUrbanSaarthi: http://localhost:%s\nAPI docs: http://localhost:%s/docs\nPress Ctrl+C to stop both servers. Logs: %s\n\n' "$WEB_PORT" "$API_PORT" "$LOG_DIR"
wait -n "${SERVICE_PIDS[@]}"
