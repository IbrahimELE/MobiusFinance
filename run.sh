#!/bin/sh
# Pokreće data_service (8001), learning_service (8003) i agent_service+UI (8002). Zaustavi s Ctrl+C.
# Offline demo (AAPL, MSFT, NVDA iz keša):  DATA_OFFLINE=1 ./run.sh
# Drugi Python (npr. venv):                 PYTHON=.venv/bin/python ./run.sh
cd "$(dirname "$0")"
[ -f data_service/.env ] && set -a && . data_service/.env && set +a
# macOS/Linux često imaju samo python3; Windows (Git Bash) često samo python.
PY="${PYTHON:-$(command -v python3 || command -v python)}"
[ -n "$PY" ] || { echo "Nije pronađen python3 ni python."; exit 1; }
# SEC_USER_AGENT ("Ime e-mail") čita data_service iz data_service/.env; bez njega koristi svoj zadani.
(cd data_service && "$PY" -m uvicorn app.main:app --port 8001) &
D=$!
(cd learning_service && "$PY" -m uvicorn app.main:app --port 8003) &
L=$!
trap 'kill $D $L 2>/dev/null' EXIT INT TERM
sleep 4
echo "Finance Desk: http://localhost:8002/"
cd agent_service && DATA_URL=http://localhost:8001 LEARNING_URL=http://localhost:8003 "$PY" -m uvicorn main:app --port 8002
