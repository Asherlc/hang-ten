#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tool_root="$repository_root/Tools/HangboardPipeline"
environment_root="$repository_root/.context/hangboard-onboarding-venv"
python_command="${HANGBOARD_PYTHON:-python3}"

usage() {
    cat <<'EOF'
Usage: scripts/hangboard-tools.sh <command> [arguments]

Commands:
  onboard     Start, inspect, approve, or resume a staged onboarding run
  inspect     Summarize hold-region review artifacts for one run
  compare     Build a read-only comparison HTML document for one review run
  lint        Validate edited hold-region review artifacts
  preview     Render deterministic review preview artifacts
  accept      Record an acceptance decision for reviewed hold regions
  promote     Build a safe promotion package for an accepted review run
  release-check Verify repo-facing release readiness for one promoted review run
  benchmark   Replay the accepted Metolius run without a live model call
  catalog     Validate, inspect, or register hangboard package catalog artifacts
EOF
}

if [[ $# -lt 1 ]]; then
    usage >&2
    exit 64
fi

command_name="$1"
shift

if ! command -v "$python_command" >/dev/null 2>&1; then
    echo "Python executable not found: $python_command" >&2
    exit 69
fi

if ! "$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "Hangboard onboarding requires Python 3.11 or newer." >&2
    exit 69
fi

environment_has_package=false
if [[ -x "$environment_root/bin/python" ]] && \
   "$environment_root/bin/python" -c 'import hangboard_vectorizer' >/dev/null 2>&1; then
    environment_has_package=true
fi

if [[ ! -x "$environment_root/bin/hangboard-onboard" || \
      ! -x "$environment_root/bin/hangboard-review" || \
      ! -x "$environment_root/bin/hangboard-promote" || \
      ! -x "$environment_root/bin/hangboard-release-check" || \
      "$environment_has_package" != true || \
      "$tool_root/pyproject.toml" -nt "$environment_root/bin/hangboard-onboard" ]]; then
    "$python_command" -m venv "$environment_root"
    "$environment_root/bin/python" -m pip install --disable-pip-version-check -e "$tool_root"
fi

case "$command_name" in
    onboard)
        exec "$environment_root/bin/hangboard-onboard" "$@"
        ;;
    inspect)
        exec "$environment_root/bin/hangboard-review" inspect "$@"
        ;;
    compare)
        exec "$environment_root/bin/hangboard-review" compare "$@"
        ;;
    lint)
        exec "$environment_root/bin/hangboard-review" lint "$@"
        ;;
    preview)
        exec "$environment_root/bin/hangboard-review" preview "$@"
        ;;
    accept)
        exec "$environment_root/bin/hangboard-review" accept "$@"
        ;;
    promote)
        exec "$environment_root/bin/hangboard-promote" promote "$@"
        ;;
    release-check)
        exec "$environment_root/bin/hangboard-release-check" release-check "$@"
        ;;
    benchmark)
        accepted_run="$tool_root/boards/metolius-wood-grips-compact-ii"
        if [[ $# -eq 0 ]]; then
            set -- --output "$repository_root/.context/hangboard-onboarding/metolius-parity/report.json"
        fi
        exec "$environment_root/bin/hangboard-semantic-benchmark" \
            --accepted-run "$accepted_run" "$@"
        ;;
    catalog)
        exec "$environment_root/bin/hangboard-catalog" "$@"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown command: $command_name" >&2
        usage >&2
        exit 64
        ;;
esac
