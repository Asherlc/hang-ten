#!/usr/bin/env bash
# Provision Linux libraries only when the restored shard needs native compilation.
set -euo pipefail

if [[ $# != 3 ]]; then
    echo "usage: $0 <shard-index> <shard-count> <cache-directory>" >&2
    exit 2
fi

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
owner="$(basename "${PASEO_WORKTREE_PATH:-$repository_root}")"
python_command="${HANGBOARD_PYTHON:-python3}"
mkdir -p "$repository_root/.context"
probe_root="$(mktemp -d "$repository_root/.context/$owner-cad-ci-setup.XXXXXX")"
printf '%s\n' "$probe_root" > "$probe_root/owned-resources"

cleanup() {
    local result=$?
    trap - EXIT
    rm -rf "$probe_root"
    [[ ! -e "$probe_root" ]] || result=1
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if "$python_command" "$repository_root/Tools/HangboardCAD/prepare_assets.py" \
    --out "$probe_root/assets" --shard-index "$1" --shard-count "$2" \
    --cache-dir "$3" --cache-only > "$probe_root/cache-probe.log" 2>&1; then
    echo "Restored complete validated board assets; native system library setup skipped."
    exit 0
fi

echo "Native compilation is needed; cache probe summary:"
tail -n 6 "$probe_root/cache-probe.log"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends libegl1 libgl1 libglu1-mesa libopengl0 squashfs-tools
