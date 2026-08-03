# CI best-practice setup

## Goal

Make pull-request CI validate both compilation and the repository's existing
XCTest suite, while keeping feedback fast and ensuring the same checks gate
merges and release promotion.

## Current context

- `.github/workflows/ci.yml` has a `CI` workflow with two build matrix
  contexts: `Build (Debug simulator)` and `Build (Release device)`.
- `HangTen.xcodeproj` has a shared `HangTen` scheme and a `HangTenTests`
  XCTest target containing unit tests in `HangTenTests/WorkoutTimelineTests.swift`.
- `.github/workflows/release.yml` starts only after a successful `CI` run on
  `main`, so every successful CI job is already part of release promotion.
- Existing workflows use read-only contents permissions, cancellation for
  superseded CI runs, timeouts, full-SHA-pinned actions, and failure log
  artifacts. These conventions remain in place.

## Design

### Workflow triggers

Keep pull-request and `main` push triggers. Add the `merge_group` trigger so
the required checks are emitted when GitHub's merge queue is used.

### Jobs

Keep the existing build matrix unchanged:

- `Build (Debug simulator)` checks simulator compilation.
- `Build (Release device)` checks device/release compilation.

Add one independent job:

- Job/check name: `Test (iOS Simulator)`.
- Runner: `macos-26`, matching the existing workflow.
- Configuration: `Debug`.
- Scheme: `HangTen`.
- Destination: an available iPhone 17 iOS Simulator selected by the Xcode
  destination specification, without hard-coding a runner-specific UDID or
  patch-level OS version.
- Signing: disabled with `CODE_SIGNING_ALLOWED=NO` and
  `CODE_SIGNING_REQUIRED=NO`.
- Diagnostics: use `set -o pipefail`, tee the test log, and write an
  `.xcresult` bundle; upload the bundle and logs when the test step fails.

The job runs the full shared scheme test action rather than selecting an
individual test class, so new tests added to the scheme are automatically
covered.

### Merge protection

Extend the active `Main` ruleset's required status checks with
`Test (iOS Simulator)`, preserving the two existing build checks and all other
rules. The three required contexts will be:

- `Build (Debug simulator)`
- `Build (Release device)`
- `Test (iOS Simulator)`

### Validation

Before handoff:

1. Run the exact simulator `xcodebuild test` command locally with temporary
   derived data and result-bundle paths.
2. Validate the workflow diff and YAML/action syntax with available local
   tooling.
3. Read back the GitHub ruleset and confirm all three required contexts.
4. Confirm no unrelated source files changed.

## Non-goals

- No multi-device or physical-device test matrix yet.
- No code-coverage threshold or third-party test-reporting dependency.
- No changes to the release signing/archive workflow.
- No replacement of the existing pinned actions or permission model.

## References

- [Apple: Automating the Test Process](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/testing_with_xcode/chapters/08-automation.html)
- [GitHub: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub: Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
