#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h}
owner=${PASEO_WORKTREE_PATH:-$repo_root}
owner=${owner:t}
venv="$repo_root/.context/plan-schema-$owner-venv"
if [[ ! -x "$venv/bin/python" ]]; then
  python3 -m venv "$venv"
  "$venv/bin/python" -m pip install --quiet -r "$repo_root/scripts/plan-schema-requirements.txt"
fi

"$venv/bin/python" - "$repo_root" <<'PY'
import json
import pathlib
import sys

from jsonschema import Draft202012Validator

root = pathlib.Path(sys.argv[1])
schema = json.loads((root / "docs/schemas/PlanWorkTarget.schema.json").read_text())
catalog = json.loads((root / "HangTen/Resources/PlanLibrary.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
count = 0
for block in catalog["blocks"]:
    for step in block["steps"]:
        if step.get("phase") == "hang" and not any(
            segment["kind"] == "work" for segment in step.get("segments", [])
        ):
            raise SystemExit(f"{block['id']}/{step['id']}: hang has no explicit work target")
        for index, segment in enumerate(step.get("segments", [])):
            if segment["kind"] != "work":
                continue
            location = f"{block['id']}/{step['id']}/segments/{index}/target"
            target = segment.get("target")
            if target is None:
                raise SystemExit(f"{location}: missing target")
            errors = sorted(validator.iter_errors(target), key=lambda error: list(map(str, error.path)))
            if errors:
                raise SystemExit(f"{location}: {errors[0].message}")
            for task in target["tasks"]:
                for hand in task:
                    depth = hand["target"].get("depth") if isinstance(hand["target"], dict) else None
                    if depth is not None and "minMM" in depth and depth["minMM"] > depth["maxMM"]:
                        raise SystemExit(f"{location}: minMM exceeds maxMM")
            count += 1

print(f"Validated {count} work targets against PlanWorkTarget.schema.json")
PY
