#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
repo_root=${script_dir:h}
library_path="$repo_root/HangTen/Resources/PlanLibrary.json"
export_dir=$(mktemp -d)
trap 'rm -rf "$export_dir"' EXIT

xcrun swiftc \
  "$repo_root/HangTen/Views/DesignSystem.swift" \
  "$repo_root/HangTen/Models/TrainingModels.swift" \
  "$repo_root/HangTen/Models/PlanStorage.swift" \
  "$script_dir/ExportPlanLibrary.swift" \
  -o "$export_dir/export-plan-library"

if [[ "${1:-}" == "--check" ]]; then
  generated_path="$export_dir/PlanLibrary.json"
  "$export_dir/export-plan-library" "$generated_path"
  if ! cmp -s "$generated_path" "$library_path"; then
    echo "PlanLibrary.json is stale; run scripts/export-plan-library.sh" >&2
    exit 1
  fi
  echo "PlanLibrary.json matches the source-audited definitions"
else
  "$export_dir/export-plan-library" "$library_path"
fi
