#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h:h}
workflow=${1:-"$repo_root/.github/workflows/release.yml"}

# Inspect the active commands in the named release steps, rather than matching
# literals anywhere in the YAML. This prevents comments or unrelated steps
# from satisfying the release-version contract.
exec ruby - "$workflow" <<'RUBY'
require 'yaml'

workflow_path = ARGV.fetch(0)
workflow = YAML.safe_load(File.read(workflow_path), aliases: true)
steps = workflow.dig('jobs', 'release', 'steps')
abort 'release workflow has no release steps' unless steps.is_a?(Array)

def step(steps, name)
  matches = steps.each_with_index.select { |entry, _index| entry['name'] == name }
  abort "release workflow must contain exactly one #{name.inspect} step" unless matches.length == 1

  entry, index = matches.first
  run = entry['run']
  abort "release workflow step #{name.inspect} must have a run script" unless run.is_a?(String)

  [index, run.lines.reject { |line| line.lstrip.start_with?('#') }.join]
end

def require_contract(run, description, pattern)
  return if pattern.match?(run)

  abort "release workflow is missing required versioning contract: #{description}"
end

version_index, version_run = step(steps, 'Select unique App Store version and build number')
archive_index, archive_run = step(steps, 'Archive signed release')
verify_index, verify_run = step(steps, 'Verify archived bundle')
abort 'release versioning steps must run before archive verification' unless version_index < archive_index && archive_index < verify_index

# A new App Store upload must use a train derived from the globally monotonic
# workflow run number; otherwise an approved train can reject a new binary.
require_contract(version_run, 'workflow-run marketing version', /^\s*marketing_version="1\.0\.\$\{GITHUB_RUN_NUMBER\}"\s*$/)
require_contract(version_run, 'exported marketing version', /^\s*echo "MARKETING_VERSION=\$marketing_version" >> "\$GITHUB_ENV"\s*$/)
require_contract(
  archive_run,
  'marketing version passed to xcodebuild',
  /xcodebuild\s+\\(?:[^\n]*\n)*?\s*MARKETING_VERSION="\$MARKETING_VERSION"\s+\\/m
)
require_contract(
  archive_run,
  'build number passed to the archive xcodebuild invocation',
  /xcodebuild\s+\\(?:[^\n]*\n)*?\s*CURRENT_PROJECT_VERSION="\$BUILD_NUMBER"\s+\\/m
)

# The archive verification must read CFBundleShortVersionString and fail the
# step when it differs from the train selected above, rather than merely
# logging its version.
require_contract(
  verify_run,
  'archived CFBundleShortVersionString read',
  /^\s*archived_marketing_version="\$\(\/usr\/libexec\/PlistBuddy -c 'Print :CFBundleShortVersionString' "\$app_path\/Info\.plist"\)"\s*$/
)
require_contract(
  verify_run,
  'archived marketing version mismatch failure',
  /\[\[ "\$archived_marketing_version" == "\$MARKETING_VERSION" \]\] \|\| \{\s*\n(?:\s*[^#\n].*\n)*?\s*exit 1\s*\n\s*\}/m
)

publish_index, publish_run = step(steps, 'Submit production release with automatic publication after approval')
upload_index = steps.index { |entry| entry['name'] == 'Upload to App Store Connect' }
abort 'production submission must follow the processed upload' unless upload_index && upload_index < publish_index
abort 'upload must wait for processing' unless steps[upload_index].dig('with', 'wait-for-processing') == 'true'
require_contract(publish_run, 'submission uses the workflow tooling revision', /scripts\/publish-app-store\.py\?ref=\$WORKFLOW_REVISION/)
require_contract(publish_run, 'submission of the archived version and build', /--app "\$ASC_APP_ID" --version "\$MARKETING_VERSION"\s+\\\n\s*--build-number "\$BUILD_NUMBER" --ipa "\$PWD\/build\/export\/HangTen\.ipa" --confirm/)
require_contract(publish_run, 'downloaded release tool checksum verification', /shasum -a 256 --check/)
RUBY
