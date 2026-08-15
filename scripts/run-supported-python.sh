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

  probe_output=$("$candidate_path" -c '
import sys
print("hangten-python:%s:%d:%d" % (
    sys.implementation.name,
    sys.version_info.major,
    sys.version_info.minor,
))
' 2>/dev/null) || return 1
  case "$probe_output" in
    hangten-python:*:*:*) ;;
    *) return 1 ;;
  esac

  probe_fields=${probe_output#hangten-python:}
  implementation=${probe_fields%%:*}
  version_fields=${probe_fields#*:}
  major=${version_fields%%:*}
  minor=${version_fields#*:}
  [ "$version_fields" != "$major" ] || return 1
  case "$implementation" in
    ''|*[!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-]*) return 1 ;;
  esac
  case "$major" in ''|*[!0-9]*) return 1 ;; esac
  case "$minor" in ''|*[!0-9]*) return 1 ;; esac
  if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
    return 1
  fi

  shift
  exec "$candidate_path" "$@"
}

if [ -n "${HANGTEN_PYTHON:-}" ]; then
  run_if_supported "$HANGTEN_PYTHON" "$@" || {
    echo "error: HANGTEN_PYTHON must name a Python 3.10 or newer interpreter." >&2
    exit 1
  }
else
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    run_if_supported "$candidate" "$@" || true
  done
fi

echo "error: Python 3.10 or newer is required to stage direct board packages." >&2
echo "Set HANGTEN_PYTHON to an explicit supported interpreter." >&2
exit 1
