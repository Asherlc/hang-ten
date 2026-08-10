# Task 1 Report

## Implementation summary

Updated `.github/workflows/codeql.yml` with `ARCHS=arm64` and `ONLY_ACTIVE_ARCH=YES` on the traced `xcodebuild` invocation. Added the required `paths` filters to both `pull_request` and `push`; preserved `merge_group`, `workflow_dispatch`, and `schedule`.

## Tests and commands

- `rtk actionlint .github/workflows/codeql.yml` — passed with no output.
- `rtk ruby -e 'require "yaml"; data = YAML.load_file(".github/workflows/codeql.yml"); abort "missing workflow root" unless data.is_a?(Hash); puts "YAML parsed successfully"'` — `YAML parsed successfully`.
- `rtk git diff --check` — passed with no output.
- `rtk git diff -- .github/workflows/codeql.yml` — confirmed exactly 10 requested insertions.

## Files changed

- `.github/workflows/codeql.yml`
- `.superpowers/sdd/codeql-speedup-plan/task-1-report.md`

## Self-review findings

No findings. The branch filters and unrelated triggers remain unchanged; the requested path entries and build settings use the brief’s exact values.

## Concerns

None.
