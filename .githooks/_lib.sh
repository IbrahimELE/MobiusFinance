# zajednička funkcija: je li gitflow uključen
gitflow_enabled() { [ "$(git config --get --bool hooks.gitflow.enabled)" != "false" ]; }
current_branch() { git symbolic-ref --short -q HEAD; }
is_protected() { case "$1" in main|dev) return 0;; *) return 1;; esac; }
