#!/bin/sh
# Pokreće data_service (8001) i agent_service+UI (8002). Zaustavi s Ctrl+C.
# Offline demo (AAPL, MSFT, NVDA iz keša):  DATA_OFFLINE=1 ./run.sh
cd "$(dirname "$0")"
[ -f data_service/.env ] && set -a && . data_service/.env && set +a
export SEC_USER_AGENT="${SEC_USER_AGENT:-FinanceDesk hackathon contact@example.com}"
(cd data_service && python -m uvicorn app.main:app --port 8001) &
D=$!; trap 'kill $D 2>/dev/null' EXIT INT TERM
sleep 3
cd agent_service && DATA_URL=http://localhost:8001 python -m uvicorn main:app --port 8002
