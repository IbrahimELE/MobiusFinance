#!/bin/sh
# Builds the Möbius package from the repo's own modules, so trading/data/learning logic has one source.
#   fd_data/      <- data_service/app      (without main.py: the FastAPI layer; service.py routes instead)
#   fd_learning/  <- learning_service/app  (without main.py)
#   fd_catalog.py <- agent_service/catalog.py (+ catalog/*.snapshot.json): /search, /markets, /crypto
#   fd_crypto.py  <- agent_service/crypto.py: price-only crypto briefs
#   vendor/       <- frontend/vendor/lightweight-charts.js
# Usage: mobius/sync.sh [install-dir]   e.g. mobius/sync.sh /data/apps/finance-desk
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"

copy_pkg() {  # src dst
  rm -rf "$2"
  mkdir -p "$2"
  (cd "$1" && find . -name '*.py' ! -name main.py ! -path '*/__pycache__/*') | while read -r f; do
    mkdir -p "$2/$(dirname "$f")"
    cp "$1/$f" "$2/$f"
  done
}

python3 "$HERE/port_ui.py"
copy_pkg "$ROOT/data_service/app" "$HERE/fd_data"
copy_pkg "$ROOT/learning_service/app" "$HERE/fd_learning"
cp "$ROOT/agent_service/catalog.py" "$HERE/fd_catalog.py"
cp "$ROOT/agent_service/crypto.py" "$HERE/fd_crypto.py"
rm -rf "$HERE/catalog" && mkdir -p "$HERE/catalog" && cp "$ROOT"/agent_service/catalog/*.snapshot.json "$HERE/catalog/"
mkdir -p "$HERE/vendor"
cp "$ROOT/frontend/vendor/lightweight-charts.js" "$HERE/vendor/lightweight-charts.js"

if [ "${1:-}" ]; then
  mkdir -p "$1"
  # Copy the package (no tests, caches or local data) into a Möbius app source dir, then apply it there.
  (cd "$HERE" && find . -type f ! -path '*/__pycache__/*' ! -path './tests/*' ! -name '*.pyc' ! -name sync.sh ! -name port_ui.py ! -name .gitignore ! -name requirements.in) | while read -r f; do
    mkdir -p "$1/$(dirname "$f")"
    cp "$HERE/$f" "$1/$f"
  done
fi
