#!/bin/sh
. "$(git rev-parse --show-toplevel)/.githooks/_lib.sh"
gitflow_enabled || exit 0
head -1 "$1" | grep -Eq '^(Merge |Revert )' && exit 0
head -1 "$1" | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|hotfix)(\([a-z0-9._-]+\))?: .+' || { echo "✗ Poruka mora biti: type(scope): opis  (npr. feat(agent): LLM teza)"; exit 1; }
