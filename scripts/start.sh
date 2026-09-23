#!/usr/bin/env bash
# macOS/Linux launcher mirroring scripts/start.ps1. Binds to localhost only.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

uv="$(command -v uv || echo "$HOME/.local/bin/uv")"
if [ ! -x "$uv" ]; then
  echo "uv를 찾을 수 없습니다. https://docs.astral.sh/uv/ 설치 후 uv sync --python 3.11을 실행하세요." >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "가상환경이 없습니다. 먼저 uv sync --python 3.11을 실행하세요." >&2
  exit 1
fi
for port in 8000 8501; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "포트 $port 를 이미 사용 중입니다. 실행 중인 앱을 확인하거나 scripts/stop.sh 로 종료하세요." >&2
    exit 1
  fi
done

outputs="$root/data/outputs"
mkdir -p "$outputs"

# Local review provider needs its own Ollama server; never started for other providers.
if grep -qE '^IMPROVEMENT_PROVIDER=local_ollama' .env 2>/dev/null; then
  ollama="$(command -v ollama || echo "$HOME/.local/bin/ollama")"
  if [ -x "$ollama" ] && ! curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    nohup "$ollama" serve > "$outputs/ollama.log" 2>&1 &
    echo "$!" > "$outputs/ollama.pid"
    echo "로컬 모델 서버(Ollama)를 시작했습니다."
  fi
fi

PYTHONUTF8=1 nohup .venv/bin/python -m uvicorn backend.main:app \
  --host 127.0.0.1 --port 8000 > "$outputs/api.log" 2>&1 &
api_pid=$!
PYTHONUTF8=1 nohup .venv/bin/python -m streamlit run frontend/app.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  > "$outputs/ui.log" 2>&1 &
ui_pid=$!
printf '[{"process_id": %s}, {"process_id": %s}]\n' "$api_pid" "$ui_pid" \
  > "$outputs/server-processes.json"

echo "웹 화면: http://127.0.0.1:8501"
echo "API 문서: http://127.0.0.1:8000/docs"
echo "종료: ./scripts/stop.sh"
