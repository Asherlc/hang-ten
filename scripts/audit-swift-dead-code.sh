#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repository_root"

# Consume a complete build-for-testing index so test injection and diagnostic
# APIs remain reachable. Generic-project mode also supports our PBX file layout.
derived_data=${1:-.context/DerivedData}
audit_owner=$(basename "${PASEO_WORKTREE_PATH:-$repository_root}")
output_directory="$repository_root/.context/$audit_owner-dead-code"
periphery_binary=${PERIPHERY_BIN:-periphery}

if [[ ! -d "$derived_data/Index.noindex/DataStore" ]]; then
    echo "Build HangTen with build-for-testing and COMPILER_INDEX_STORE_ENABLE=YES first." >&2
    exit 1
fi

mkdir -p "$output_directory"
python3 - "$derived_data" "$output_directory/generic-project.json" <<'PY'
import json
from pathlib import Path
import sys

index = Path(sys.argv[1]).resolve() / "Index.noindex/DataStore"
configuration = {
    "indexstores": [str(index)],
    "test_targets": ["HangTenTests", "HangTenUITests"],
    "plists": [str(Path("HangTen/Info.plist").resolve())],
    "xibs": [],
    "xcdatamodels": [],
    "xcmappingmodels": [],
}
Path(sys.argv[2]).write_text(json.dumps(configuration, indent=2) + "\n")
PY

"$periphery_binary" scan \
    --config "$repository_root/.periphery.yml" \
    --generic-project-config "$output_directory/generic-project.json" \
    --relative-results --format json --quiet --disable-update-check --strict \
    > "$output_directory/periphery.json"

echo "Swift dead-code audit passed; report: $output_directory/periphery.json"
