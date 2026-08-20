#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tool_root="$repository_root/Tools/HangboardPackages"
environment_root="$repository_root/.context/hangboard-packages-venv"
python_command="${HANGBOARD_PYTHON:-python3}"

usage() {
    cat <<'EOF'
Usage: scripts/hangboard-packages.sh <command> [arguments]

Commands:
  validate    Validate directly discovered hangboard packages
  status      Print directly discovered package metadata
  simplify-hold-paths    Reduce fidelity-validated editable hold paths
  normalize-presentations    Normalize board presentation canvases
  derive-hold-geometry    Emit read-only image-derived geometry candidates
EOF
}

if [[ $# -lt 1 ]]; then
    usage >&2
    exit 64
fi

command_name="$1"
shift

case "$command_name" in
    validate|status|simplify-hold-paths|normalize-presentations|derive-hold-geometry)
        ;;
    -h|--help|help)
        usage
        exit 0
        ;;
    *)
        echo "Unknown command: $command_name" >&2
        usage >&2
        exit 64
        ;;
esac

if ! command -v "$python_command" >/dev/null 2>&1; then
    echo "Python executable not found: $python_command" >&2
    exit 69
fi

if ! "$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11, 4) else 1)'; then
    echo "Hangboard package validation requires Python 3.11.4 or newer." >&2
    exit 69
fi

environment_has_package=false
if [[ -x "$environment_root/bin/python" ]] && \
   "$environment_root/bin/python" -c 'import hangboard_packages' >/dev/null 2>&1; then
    environment_has_package=true
fi

environment_needs_install=false
if [[ ! -x "$environment_root/bin/hangboard-packages" || \
      "$tool_root/pyproject.toml" -nt "$environment_root/bin/hangboard-packages" ]]; then
    environment_needs_install=true
fi

if [[ "$environment_has_package" != true || "$environment_needs_install" == true ]]; then
    "$python_command" -m venv "$environment_root"
    "$environment_root/bin/python" -m pip install --disable-pip-version-check -e "$tool_root"
fi

exec "$environment_root/bin/hangboard-packages" "$command_name" "$@"
