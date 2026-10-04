#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
repo_root=${script_dir:h}
library_path="$repo_root/HangTen/Resources/PlanLibrary.json"
if [[ "${1:-}" == "--output" ]]; then
  library_path="${2:?--output requires a path}"
fi
owner="${${PASEO_WORKTREE_PATH:-$repo_root}:t}"
mkdir -p "$repo_root/.context"
export_dir=$(mktemp -d "$repo_root/.context/$owner-export-plan-library.XXXXXX")
print -r -- "$export_dir" > "$export_dir/owned-resources"
cleanup() {
  local result=$?
  trap - EXIT
  rm -rf "$export_dir"
  [[ ! -e "$export_dir" ]] || result=1
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
resource_dir="$export_dir/Resources"
exporter_path="$resource_dir/export-plan-library"

TARGET_BUILD_DIR="$export_dir" \
UNLOCALIZED_RESOURCES_FOLDER_PATH="Resources" \
DERIVED_FILE_DIR="$export_dir/DerivedFiles" \
  "$repo_root/scripts/run-supported-python.sh" \
  "$repo_root/scripts/stage-board-packages.py" \
  --repository-root "$repo_root" \
  --destination "$resource_dir/Hangboards"

xcrun swiftc \
  "$repo_root/HangTen/Views/DesignSystem.swift" \
  "$repo_root/HangTen/Models/BoardStorage.swift" \
  "$repo_root/HangTen/Models/BoardPackageStore.swift" \
  "$repo_root/HangTen/Models/SuspensionProfiles.swift" \
  "$repo_root/HangTen/Views/SuspendedBoardPresentation.swift" \
  "$repo_root/HangTen/Models/RopePhysicsDescriptor.swift" \
  "$repo_root/HangTen/Models/TrainingModels.swift" \
  "$repo_root/HangTen/Models/WorkoutActivityRecording.swift" \
  "$script_dir/ExportPlanLibrarySupport.swift" \
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
