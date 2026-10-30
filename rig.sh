#!/usr/bin/env bash
# Run the rig CLI without typing `uv run`, from any directory:
#   /path/to/rig/rig.sh run --task "..."      ./rig.sh resume <session>      ./rig.sh --help
# It stays in your current directory, which rig uses as the workspace (and for .rig/), and
# only borrows this project's environment. (The name can't be ./rig: that is the package.)
set -euo pipefail
exec uv run --project "$(dirname "$0")" rig "$@"
