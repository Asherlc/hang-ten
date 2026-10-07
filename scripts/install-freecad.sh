#!/usr/bin/env bash
# Install the pinned native toolchain into a new directory owned by the caller.
# Only the command path goes to stdout, so callers can capture it directly.
set -euo pipefail

install_root="${1:?Usage: install-freecad.sh <new-owned-directory>}"
if [[ -e "$install_root" ]]; then
    echo "Refusing to replace an existing FreeCAD directory: $install_root" >&2
    exit 1
fi
mkdir -p "$install_root"
install_root="$(cd "$install_root" && pwd)"
mount_path="$install_root/mount"
printf '%s\n' "$install_root" "$mount_path" > "$install_root/owned-resources"

cleanup() {
    local result=$?
    trap - EXIT
    if [[ "$(uname -s)" == Darwin ]] && mount | grep -Fq " on $mount_path "; then
        hdiutil detach "$mount_path" >&2 || result=1
    fi
    if [[ "$(uname -s)" == Darwin ]] && mount | grep -Fq " on $mount_path "; then
        echo "Owned FreeCAD mount still exists: $mount_path" >&2
        exit 1
    fi
    if [[ "$result" != 0 ]]; then
        rm -rf "$install_root"
        [[ ! -e "$install_root" ]] || result=1
    fi
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

case "$(uname -s)/$(uname -m)" in
    Darwin/arm64)
        filename=FreeCAD_1.1.3-macOS-arm64-py311.dmg
        digest=f5c0ece7cd7c932466d6effadc0fc6e179b0538a9d9a6a77a6769eae3af2667c ;;
    Darwin/x86_64)
        filename=FreeCAD_1.1.3-macOS-x86_64-py311.dmg
        digest=8434bd6ad32f597605d184e5b996f496e9cbc7e6d8ffb6db4dbd6e2ce6d1612b ;;
    Linux/x86_64)
        filename=FreeCAD_1.1.3-Linux-x86_64-py311.AppImage
        digest=3a853eb69ee595f779f2255dbf80a765926981d8ff68903cefee4dfb03a8f5ef ;;
    Linux/aarch64|Linux/arm64)
        filename=FreeCAD_1.1.3-Linux-aarch64-py311.AppImage
        digest=9a8f9f7f2802bb856f2bb70f53d536e2ae06569f4e6d718407803076104ff55e ;;
    *) echo "Unsupported FreeCAD platform: $(uname -s)/$(uname -m)" >&2; exit 69 ;;
esac
download="$install_root/$filename"
curl --fail --location --retry 3 \
    "https://github.com/FreeCAD/FreeCAD/releases/download/1.1.3/$filename" \
    --output "$download" >&2
"${HANGBOARD_PYTHON:-python3}" - "$download" "$digest" <<'PY'
import hashlib
import sys
from pathlib import Path
path, expected = sys.argv[1:]
with Path(path).open("rb") as source:
    digest = hashlib.sha256()
    for block in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(block)
    actual = digest.hexdigest()
if actual != expected:
    raise SystemExit(f"FreeCAD checksum mismatch: {actual} != {expected}")
PY

if [[ "$(uname -s)" == Darwin ]]; then
    mkdir "$mount_path"
    hdiutil attach "$download" -nobrowse -readonly -mountpoint "$mount_path" >&2
    ditto "$mount_path/FreeCAD.app" "$install_root/FreeCAD.app"
    hdiutil detach "$mount_path" >&2
    command_path="$install_root/FreeCAD.app/Contents/Resources/bin/freecadcmd"
else
    # Read the pinned type-2 payload directly: no FUSE or AppImage launcher.
    if ! command -v unsquashfs >/dev/null; then
        echo "Install squashfs-tools before installing pinned FreeCAD on Linux." >&2
        exit 69
    fi
    offset="$("${HANGBOARD_PYTHON:-python3}" - "$download" <<'PY'
import struct
import sys
with open(sys.argv[1], "rb") as source:
    header = source.read(64)
    if header[:6] != b"\x7fELF\x02\x01" or header[8:11] != b"AI\x02":
        raise SystemExit("Expected the pinned ELF64 type-2 AppImage")
    section_table = struct.unpack_from("<Q", header, 40)[0]
    section_size, section_count = struct.unpack_from("<HH", header, 58)
    offset = section_table + section_size * section_count
    source.seek(offset)
    if source.read(4) != b"hsqs":
        raise SystemExit("Pinned AppImage has no SquashFS payload at the ELF boundary")
    print(offset)
PY
)"
    if ! unsquashfs -no-progress -processors 2 -d "$install_root/squashfs-root" \
        -o "$offset" "$download" > "$install_root/extract.log" 2>&1; then
        tail -n 20 "$install_root/extract.log" >&2
        exit 1
    fi
    command_path="$install_root/freecadcmd"
    cat > "$command_path" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
native_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/squashfs-root/usr" && pwd)"
export PREFIX="$native_root"
export PYTHONHOME="$native_root"
export PATH_TO_FREECAD_LIBDIR="$native_root/lib"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export FONTCONFIG_FILE=/etc/fonts/fonts.conf
export FONTCONFIG_PATH=/etc/fonts
export SSL_CERT_FILE="$native_root/ssl/cacert.pem"
export GIT_SSL_CAINFO="$native_root/ssl/cacert.pem"
exec "$native_root/bin/freecadcmd" "$@"
WRAPPER
    chmod +x "$command_path"
fi
test -x "$command_path"
printf '%s\n' "$command_path"
