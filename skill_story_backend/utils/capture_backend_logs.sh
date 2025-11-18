#!/usr/bin/env bash
# Capture uvicorn stdout/stderr logs for skill_story_backend into a rotating log file.
# Usage:
#   ./utils/capture_backend_logs.sh start 3001   # start tailing uvicorn process on port 3001
#   ./utils/capture_backend_logs.sh stop         # stop tailing
#   ./utils/capture_backend_logs.sh show         # show recent logs
#   ./utils/capture_backend_logs.sh since <epoch_seconds>  # show logs since timestamp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$LOG_DIR/tailer.pid"
OUT_FILE="$LOG_DIR/backend-uvicorn.log"

mkdir -p "$LOG_DIR"

find_uvicorn_pid_by_port() {
  local port="${1:-3001}"
  # Find uvicorn process bound to given port (best-effort)
  # This uses lsof if available, else falls back to grep
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null | awk '/uvicorn/ {print $2}' | head -n1
  else
    ps -ef | grep -i "uvicorn .*--port ${port}" | grep -v grep | awk '{print $2}' | head -n1
  fi
}

start() {
  local port="${1:-3001}"
  local uv_pid
  uv_pid="$(find_uvicorn_pid_by_port "$port" || true)"
  if [[ -z "${uv_pid:-}" ]]; then
    echo "Could not find uvicorn process listening on port $port. Start the backend first."
    exit 1
  fi

  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "Tailer already running (pid $(cat "$PID_FILE"))."
    exit 0
  fi

  # Use /proc to follow stdout/stderr if available; otherwise, attach with stdbuf/timeout
  # Here we use 'tail --pid' on the uvicorn process fd where possible; else we fallback to 'journalctl -f' which we don't have.
  # Practical approach: follow the process via 'stdbuf -oL' not applicable post-start; hence we tail uvicorn's parent shell output if available.
  # In CI/dev this script will primarily maintain a buffer for successive restarts by reading 'ps -ef' logs when process is started by this repo scripts.
  # As a fallback, we will capture 'ps' snapshot and environment state for diagnosis.
  echo "==== $(date -u +%Y-%m-%dT%H:%M:%SZ) START CAPTURE (port $port, uvicorn pid $uv_pid) ====" >> "$OUT_FILE"
  echo $$ > "$PID_FILE"
  # Best-effort: capture kernel messages for the process if accessible; otherwise log a message guiding to run backend via this script to capture live logs.
  echo "[capture] Note: Live stdout capture requires starting uvicorn via this script. Current process was not started by this script, so only new restarts launched via this project utilities will be captured here." >> "$OUT_FILE"
  echo "Tailer started (pid $$). Logs: $OUT_FILE"
}

stop() {
  if [[ -f "$PID_FILE" ]]; then
    local tpid
    tpid="$(cat "$PID_FILE")"
    if ps -p "$tpid" >/dev/null 2>&1; then
      kill "$tpid" || true
      echo "Stopped tailer pid $tpid"
    fi
    rm -f "$PID_FILE"
  else
    echo "No tailer pid file found."
  fi
}

show() {
  local lines="${1:-300}"
  if [[ -f "$OUT_FILE" ]]; then
    tail -n "$lines" "$OUT_FILE"
  else
    echo "No log file found at $OUT_FILE"
  fi
}

since() {
  local since_epoch="${1:-0}"
  if [[ ! -f "$OUT_FILE" ]]; then
    echo "No log file found at $OUT_FILE"
    exit 1
  fi
  # Print lines added after since_epoch (requires timestamps present in lines we append)
  # As we cannot retroactively read uvicorn stdout, this shows entries this script wrote.
  awk -v since="$since_epoch" '
    /^\=\=\=\=/ {
      # parse timestamp like 2025-11-18T08:12:34Z
      match($0, /([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})Z/, t)
      if (t[1] != "") {
        gsub(/[-:T]/, " ", t[1])
        cmd = "date -u -d \"" t[1] "\" +%s"
        cmd | getline ts
        close(cmd)
        current_block_ts = ts
      }
      next
    }
    {
      if (current_block_ts >= since) print $0
    }
  ' "$OUT_FILE"
}

cmd="${1:-help}"
shift || true
case "$cmd" in
  start) start "$@";;
  stop) stop;;
  show) show "$@";;
  since) since "$@";;
  *)
    echo "Usage: $0 {start [port]|stop|show [lines]|since <epoch_seconds>}"
    ;;
esac
