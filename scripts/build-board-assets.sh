#!/usr/bin/env bash
# Compile and install ignored runtime artifacts before validation or app builds.
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
owner="$(basename "${PASEO_WORKTREE_PATH:-$repository_root}")"
python_command="${HANGBOARD_PYTHON:-python3}"
freecad_command="${HANGTEN_FREECAD_CMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}"
mkdir -p "$repository_root/.context"
build_root="$(mktemp -d "$repository_root/.context/$owner-board-build.XXXXXX")"
mount_path="$build_root/mount"
# Record exact ownership before creating a mount or installing a toolchain.
printf '%s\n' "$build_root" "$mount_path" > "$build_root/owned-resources"

cleanup() {
    local result=$?
    trap - EXIT
    if [[ "$(uname -s)" == Darwin ]] && mount | grep -Fq " on $mount_path "; then
        hdiutil detach "$mount_path" || result=1
    fi
    if [[ "$(uname -s)" == Darwin ]] && mount | grep -Fq " on $mount_path "; then
        echo "error: owned FreeCAD mount still exists: $mount_path" >&2
        exit 1
    fi
    rm -rf "$build_root"
    [[ ! -e "$build_root" ]] || result=1
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ! -x "$freecad_command" ]]; then
    if [[ "$(uname -s)" != Darwin ]]; then
        echo "Set HANGTEN_FREECAD_CMD to a pinned FreeCAD 1.1.3 executable." >&2
        exit 69
    fi
    case "$(uname -m)" in
        arm64) digest=f5c0ece7cd7c932466d6effadc0fc6e179b0538a9d9a6a77a6769eae3af2667c ;;
        x86_64) digest=8434bd6ad32f597605d184e5b996f496e9cbc7e6d8ffb6db4dbd6e2ce6d1612b ;;
        *) echo "Unsupported FreeCAD architecture" >&2; exit 69 ;;
    esac
    curl --fail --location --retry 3 \
        "https://github.com/FreeCAD/FreeCAD/releases/download/1.1.3/FreeCAD_1.1.3-macOS-$(uname -m)-py311.dmg" \
        --output "$build_root/FreeCAD.dmg"
    echo "$digest  $build_root/FreeCAD.dmg" | shasum -a 256 -c -
    mkdir "$mount_path"
    hdiutil attach "$build_root/FreeCAD.dmg" -nobrowse -readonly -mountpoint "$mount_path"
    ditto "$mount_path/FreeCAD.app" "$build_root/FreeCAD.app"
    hdiutil detach "$mount_path"
    freecad_command="$build_root/FreeCAD.app/Contents/Resources/bin/freecadcmd"
fi

# Use FreeCAD's Python ABI even when the host Python has a different version.
"$python_command" -m pip install --disable-pip-version-check --only-binary=:all: \
    --python-version 3.11 --target "$build_root/usd" usd-core==26.8 \
    -r "$repository_root/Tools/HangboardCAD/rope_solver_requirements.txt"

"$python_command" "$repository_root/Tools/HangboardCAD/prepare_assets.py" \
    --out "$build_root/compiled" \
    --freecad "$freecad_command" \
    --extra-python-path "$build_root/usd" "$@"

# These exact runtime paths are workspace-owned build outputs, ignored by Git.
# Consumers retain their existing package paths on both app platforms.
"$python_command" - "$build_root/compiled" "$repository_root" <<'PY'
from pathlib import Path
import sys

compiled, repository = map(Path, sys.argv[1:])
sys.path.insert(0, str(repository / "Tools/HangboardCAD"))
from prepare_assets import publish_assets

for package in sorted(compiled.iterdir()):
    publish_assets(package / "assets", repository / "Hangboards" / package.name / "assets")
PY
