#!/usr/bin/env bash
# Export the authored hand without modifying its Blender source.
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
owner="$(basename "${PASEO_WORKTREE_PATH:-$repository_root}")"
python_command="${HANGBOARD_PYTHON:-python3}"
blender_command="${HANGTEN_BLENDER_CMD:-/Applications/Blender.app/Contents/MacOS/Blender}"
mkdir -p "$repository_root/.context"
export_root="$(mktemp -d "$repository_root/.context/$owner-hand-export.XXXXXX")"
mount_path="$export_root/mount"
printf '%s\n' "$export_root" "$mount_path" > "$export_root/owned-resources"

cleanup() {
    local result=$?
    trap - EXIT
    if [[ "$(uname -s)" == Darwin ]] && mount | grep -Fq " on $mount_path "; then
        hdiutil detach "$mount_path" || result=1
    fi
    if [[ "$(uname -s)" == Darwin ]] && mount | grep -Fq " on $mount_path "; then
        echo "error: owned Blender mount still exists: $mount_path" >&2
        exit 1
    fi
    rm -rf "$export_root"
    [[ ! -e "$export_root" ]] || result=1
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ! -x "$blender_command" ]]; then
    case "$(uname -s)/$(uname -m)" in
        Darwin/arm64)
            curl --fail --location --retry 3 \
                https://download.blender.org/release/Blender5.2/blender-5.2.0-macos-arm64.dmg \
                --output "$export_root/Blender.dmg"
            echo "ed4d8390166dec5ea0a2813a03db6221f206ce016442be7f59f41d760972568a  $export_root/Blender.dmg" | shasum -a 256 -c -
            mkdir "$mount_path"
            hdiutil attach "$export_root/Blender.dmg" -nobrowse -readonly -mountpoint "$mount_path"
            ditto "$mount_path/Blender.app" "$export_root/Blender.app"
            hdiutil detach "$mount_path"
            blender_command="$export_root/Blender.app/Contents/MacOS/Blender" ;;
        Linux/x86_64)
            archive="$export_root/blender-5.2.0-linux-x64.tar.xz"
            curl --fail --location --retry 3 \
                https://download.blender.org/release/Blender5.2/blender-5.2.0-linux-x64.tar.xz \
                --output "$archive"
            echo "96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48  $archive" | sha256sum -c -
            tar -xJf "$archive" -C "$export_root"
            blender_command="$export_root/blender-5.2.0-linux-x64/blender" ;;
        *)
            echo "Set HANGTEN_BLENDER_CMD to a pinned Blender 5.2.0 executable." >&2
            exit 69 ;;
    esac
fi

export BLENDER_USER_CONFIG="$export_root/config"
export BLENDER_USER_SCRIPTS="$export_root/scripts"
export BLENDER_USER_DATAFILES="$export_root/datafiles"
export XDG_CACHE_HOME="$export_root/cache"
export TMPDIR="$export_root/tmp"
mkdir -p "$TMPDIR"
"$blender_command" --background "$repository_root/Art/GripHand/GripHand.blend" \
    --python-exit-code 1 --python "$repository_root/Art/GripHand/export_hand.py" -- \
    --output "$export_root/hand-mesh.json"
"$python_command" "$repository_root/Art/GripHand/validate_export.py" --path "$export_root/hand-mesh.json"
mkdir -p "$repository_root/HangTen/Resources/GripHand"
cp "$export_root/hand-mesh.json" "$repository_root/HangTen/Resources/GripHand/hand-mesh.json"
