#!/usr/bin/env bash
# Generalized launcher for the Notion migration init-container command.
# When copied elsewhere, set PROJECT_TOOLKIT_ROOT to the submodule location.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
toolkit_root="${PROJECT_TOOLKIT_ROOT:-$(cd -- "$script_dir/../.." && pwd)}"
export PYTHONPATH="$toolkit_root${PYTHONPATH:+:$PYTHONPATH}"

exec "${PYTHON_EXECUTABLE:-python}" "$toolkit_root/scripts/run_migrations.py" "$@"
