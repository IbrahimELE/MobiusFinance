#!/bin/sh
. "$(git rev-parse --show-toplevel)/.githooks/_lib.sh"
gitflow_enabled || exit 0
b=$(current_branch)
if is_protected "$b"; then echo "✗ Rebase dok si na '$b' nije dozvoljen."; exit 1; fi
