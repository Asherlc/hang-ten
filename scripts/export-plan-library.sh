#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
repo_root=${script_dir:h}
library_path="$repo_root/HangTen/Resources/PlanLibrary.json"
export_dir=$(mktemp -d "$repo_root/.context/export-plan-library.XXXXXX")
trap 'rm -rf "$export_dir"' EXIT
resource_dir="$export_dir/Resources"
exporter_path="$resource_dir/export-plan-library"

TARGET_BUILD_DIR="$export_dir" \
UNLOCALIZED_RESOURCES_FOLDER_PATH="Resources" \
  "$repo_root/scripts/stage-board-packages.py" \
  --repository-root "$repo_root" \
  --destination "$resource_dir/Hangboards"

xcrun swiftc \
  "$repo_root/HangTen/Views/DesignSystem.swift" \
  "$repo_root/HangTen/Views/BoardDesignLanguage.swift" \
  "$repo_root/HangTen/Models/BoardStorage.swift" \
  "$repo_root/HangTen/Models/BoardPackageStore.swift" \
  "$repo_root/HangTen/Models/TrainingModels.swift" \
  "$repo_root/HangTen/Models/WorkoutStepNormalization.swift" \
  "$repo_root/HangTen/Models/PlanStorage.swift" \
  "$script_dir/ExportPlanLibrary.swift" \
  -o "$exporter_path"

if [[ "${1:-}" == "--check" ]]; then
  generated_path="$export_dir/PlanLibrary.json"
  "$exporter_path" "$generated_path"
  if ! cmp -s "$generated_path" "$library_path"; then
    echo "PlanLibrary.json is stale; run scripts/export-plan-library.sh" >&2
    exit 1
  fi
  echo "PlanLibrary.json matches the source-audited definitions"
else
  "$exporter_path" "$library_path"
fi
