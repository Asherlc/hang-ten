#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_command="${HANGBOARD_PYTHON:-python3}"

if ! command -v "$python_command" >/dev/null 2>&1; then
    echo "Python executable not found: $python_command" >&2
    exit 69
fi

if ! "$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11, 4) else 1)'; then
    echo "Board catalog export requires Python 3.11.4 or newer." >&2
    exit 69
fi

exec "$python_command" "$repository_root/scripts/export-board-catalog.py" "$@"
