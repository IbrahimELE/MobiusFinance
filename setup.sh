#!/bin/sh
# Instalira gitflow hookove: kopira .githooks/*.sh u .git/hooks/* (bez .sh). Pokreni jednom nakon clone-a.
set -e
cd "$(git rev-parse --show-toplevel)"
for f in .githooks/*.sh; do n=$(basename "$f" .sh); case "$n" in _lib) continue;; esac; cp "$f" ".git/hooks/$n"; chmod +x ".git/hooks/$n"; done
git config --local pull.ff only
echo "Hookovi instalirani (isključi: git config --local hooks.gitflow.enabled false)"
