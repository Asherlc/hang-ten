#!/bin/sh

if [ "$(uname -s 2>/dev/null)" != "Darwin" ]; then
  echo "Skipping Conductor archive cleanup: this workspace is not running on macOS (Darwin)." >&2
  exit 0
fi

if ! command -v zsh >/dev/null 2>&1; then
  echo "Skipping Conductor archive cleanup: zsh is unavailable on macOS." >&2
  exit 0
fi

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P) || exit 1
exec zsh "$script_dir/conductor-resource-cleanup.sh" archive
