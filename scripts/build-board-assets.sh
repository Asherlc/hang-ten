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

prepare_arguments=(--out "$build_root/compiled" --jobs "${HANGTEN_CAD_JOBS:-2}")
cache_ready=false
if [[ -n "${HANGTEN_CAD_CACHE_DIR:-}" ]]; then
    prepare_arguments+=(--cache-dir "$HANGTEN_CAD_CACHE_DIR")
    # A complete hit requires only host Python. Skip FreeCAD and native wheels.
    if "$python_command" "$repository_root/Tools/HangboardCAD/prepare_assets.py" \
        "${prepare_arguments[@]}" "$@" --cache-only > "$build_root/cache-probe.log" 2>&1; then
        cache_ready=true
        echo "Restored complete validated board assets; native toolchain setup skipped."
    else
        echo "Native compilation is needed; cache probe summary:"
        tail -n 6 "$build_root/cache-probe.log"
    fi
fi

if [[ "$cache_ready" == false ]]; then
if [[ ! -x "$freecad_command" ]]; then
    freecad_command="$("$repository_root/scripts/install-freecad.sh" "$build_root/freecad")"
fi

# Use FreeCAD's Python ABI even when the host Python has a different version.
"$python_command" -m pip install --disable-pip-version-check --only-binary=:all: \
    --python-version 3.11 --target "$build_root/usd" usd-core==26.8 \
    -r "$repository_root/Tools/HangboardCAD/rope_solver_requirements.txt"

"$python_command" "$repository_root/Tools/HangboardCAD/prepare_assets.py" \
    "${prepare_arguments[@]}" \
    --freecad "$freecad_command" \
    --extra-python-path "$build_root/usd" "$@"
fi

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
