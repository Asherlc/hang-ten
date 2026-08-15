#!/bin/sh
# Run a direct board-package tool with a Python version it supports.
set -eu

if [ "$#" -eq 0 ]; then
  echo "usage: $0 SCRIPT [ARGUMENT ...]" >&2
  exit 64
fi

run_if_supported() {
  candidate=$1
  candidate_path=$(command -v "$candidate" 2>/dev/null || true)
  [ -n "$candidate_path" ] || return 1
  "$candidate_path" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    >/dev/null 2>&1 || return 1
  shift
  exec "$candidate_path" "$@"
}

if [ -n "${HANGTEN_PYTHON:-}" ]; then
  run_if_supported "$HANGTEN_PYTHON" "$@" || true
else
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    run_if_supported "$candidate" "$@" || true
  done
fi

echo "error: Python 3.10 or newer is required to stage direct board packages." >&2
echo "Set HANGTEN_PYTHON to an explicit supported interpreter." >&2
exit 1
