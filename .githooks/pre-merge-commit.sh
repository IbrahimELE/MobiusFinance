#!/bin/sh
. "$(git rev-parse --show-toplevel)/.githooks/_lib.sh"
gitflow_enabled || exit 0
echo "✗ Merge commitovi lokalno nisu dozvoljeni. Spajanje ide kroz PR (Squash and merge). Za ažuriranje grane: git pull --rebase origin dev"; exit 1
