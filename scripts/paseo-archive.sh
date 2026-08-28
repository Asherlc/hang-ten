#!/bin/sh

if [ "$(uname -s 2>/dev/null)" != "Darwin" ]; then
  echo "Skipping Paseo workspace archive cleanup: this workspace is not running on macOS (Darwin)." >&2
  exit 0
fi

if ! command -v zsh >/dev/null 2>&1; then
  echo "Skipping Paseo workspace archive cleanup: zsh is unavailable on macOS." >&2
  exit 0
fi

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P) || exit 1
workspace_path=${PASEO_WORKTREE_PATH:-$(pwd -P)}
exec env PASEO_WORKTREE_PATH="$workspace_path" zsh "$script_dir/paseo-resource-cleanup.sh" archive
