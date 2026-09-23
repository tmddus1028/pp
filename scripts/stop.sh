#!/usr/bin/env bash
# Stops only the processes this project started.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
state="$root/data/outputs/server-processes.json"
ollama_pid="$root/data/outputs/ollama.pid"

if [ -f "$state" ]; then
  for pid in $(grep -oE '[0-9]+' "$state"); do
    kill "$pid" 2>/dev/null || true
  done
  rm -f "$state"
  echo "앱 서버를 종료했습니다."
else
  echo "저장된 서버 프로세스가 없습니다."
fi
if [ -f "$ollama_pid" ]; then
  kill "$(cat "$ollama_pid")" 2>/dev/null || true
  rm -f "$ollama_pid"
  echo "로컬 모델 서버(Ollama)를 종료했습니다."
fi
