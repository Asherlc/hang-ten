#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h:h}
workflow="$repo_root/.github/workflows/release.yml"
workflow_contents=$(<"$workflow")

require_workflow_contract() {
  local expected=$1
  [[ "$workflow_contents" == *"$expected"* ]] || {
    print -u2 -- "release workflow is missing required versioning contract: $expected"
    exit 1
  }
}

# A new App Store upload must use a train derived from the globally monotonic
# workflow run number; otherwise an approved train can reject a new binary.
require_workflow_contract 'marketing_version="1.0.${GITHUB_RUN_NUMBER}"'
require_workflow_contract 'echo "MARKETING_VERSION=$marketing_version" >> "$GITHUB_ENV"'
require_workflow_contract 'MARKETING_VERSION="$MARKETING_VERSION"'

# The archive verification must fail when the built bundle does not carry the
# train selected above, rather than merely logging its version.
require_workflow_contract 'archived_marketing_version="$(/usr/libexec/PlistBuddy -c '\''Print :CFBundleShortVersionString'\'' "$app_path/Info.plist")"'
require_workflow_contract '[[ "$archived_marketing_version" == "$MARKETING_VERSION" ]]'
