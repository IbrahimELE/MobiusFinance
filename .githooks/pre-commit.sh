#!/bin/sh
. "$(git rev-parse --show-toplevel)/.githooks/_lib.sh"
gitflow_enabled || exit 0
b=$(current_branch); [ -z "$b" ] && exit 0
if is_protected "$b"; then echo "✗ Direktan commit na '$b' nije dozvoljen. Napravi granu: git switch -c feature/<ime>"; exit 1; fi
echo "$b" | grep -Eq '^(feature|bugfix|hotfix|docs|refactor|test)/[a-z0-9][a-z0-9._-]*$' || { echo "✗ Naziv grane '$b' nije dozvoljen. Format: feature|bugfix|hotfix|docs|refactor|test/<ime>"; exit 1; }
