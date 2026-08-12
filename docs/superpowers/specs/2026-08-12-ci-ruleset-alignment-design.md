# CI ruleset alignment design

## Problem

GitHub's active `Main` ruleset requires three status checks: `Build (Debug simulator)`, `Build (Release device)`, and `Test (iOS Simulator)`. The CI workflow intentionally skips the Release-device build for pull-request events to avoid an additional macOS build. It also does not handle pull-request `edited` events or offer manual dispatch. Automatic base changes in a PR stack can therefore leave a pull request without its required check contexts, causing auto-merge to wait indefinitely despite a conflict-free branch.

## Decision

- Keep the Release-device build post-merge only; do not restore it to pull-request CI.
- Require only the Debug-simulator build and iOS-simulator tests for pull requests.
- Trigger CI when a pull request is edited, including automatic base changes.
- Allow maintainers to manually dispatch CI as a recovery path when GitHub misses an event.

## Implementation outline

1. Update `.github/workflows/ci.yml` to include `edited` in `pull_request.types` and add `workflow_dispatch`.
2. Update the active `Main` repository ruleset to remove `Build (Release device)` from `required_status_checks`, retaining `Build (Debug simulator)` and `Test (iOS Simulator)`.
3. Verify the ruleset matches CI's PR-visible jobs and that an `edited` or manually dispatched run creates both required contexts.

## Failure handling

If GitHub fails to produce checks after an automatic base change, a maintainer can run CI manually for the branch. Required-check names remain stable, so GitHub evaluates the manual run against the same ruleset.

## Scope

This changes only CI triggering and the `Main` ruleset's required status checks. It does not change application code, post-merge Release-device validation, merge methods, or review requirements.
