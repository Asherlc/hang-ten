#!/usr/bin/env bash
# Materialize all generated app resources from the retained authored sources.
set -euo pipefail
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$repository_root/scripts/build-board-assets.sh"
"$repository_root/scripts/export-grip-hand.sh"
"$repository_root/scripts/export-plan-library.sh"
