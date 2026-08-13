# Component-Aware CI Design

**Date:** 2026-08-12

## Goal

Reduce pull-request latency and macOS runner use by running each CI component
only when changed files can affect it, while retaining all applicable
validation for merge-queue entries and changes pushed to `main`.

## Problem

The main `CI` workflow currently runs Python, iOS build, and iOS simulator
tests for every pull request. The Hangboard Workbench release workflow also
runs Python, Node, and native checks together for every pull request. An
editor-only JavaScript, HTML, or CSS change therefore consumes Xcode and
Python capacity even when it cannot affect either codebase.

Workflow-level `paths` filters are insufficient because a missing workflow or
check can complicate required-check and merge-queue behavior. Selection must
happen at job level, after one explicit, auditable classification step.

## Design

### Shared path taxonomy

Create `.github/ci-paths.yml` as the one source of truth. Both CI workflows
load it through `dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d`,
the immutable v4.0.3 commit. Each `changes` job has the narrow permissions its
pull-request mode requires: `contents: read` and `pull-requests: read`. Each
job checks out the event revision before invoking `paths-filter`, so the
filter file and changed content come from the pull request's checkout on
`pull_request` events.

| Filter | Conservative paths | Effect |
| --- | --- | --- |
| `ios` | `HangTen/**`, `HangTenTests/**`, `HangTen.xcodeproj/**`, iOS scripts, `Package.resolved`, and iOS CI/release workflow files | iOS build and simulator tests |
| `python` | `Tools/HangboardPipeline/**`, Python Workbench server/runtime/packaging files, Python tests, `pyproject.toml`, and Python CI/release workflow files | Python pipeline and Workbench tests |
| `workbench_web` | Workbench HTML/CSS/browser JavaScript and Node tests, plus Node CI/release workflow files | Workbench Node tests |
| `workbench_native` | `Tools/HangboardWorkbench/macos/**` and native packaging/release files | SwiftPM/native Workbench checks |
| `shared_board_content` | `Hangboards/**`, `Tools/HangboardPipeline/boards/**`, `HangTen/Resources/BoardLibrary.json`, board export/catalog scripts, and catalog inputs | Python and iOS; Workbench Node and Python checks |
| `metadata` | App Store metadata and its validation script | metadata validation |
| `workflow` | `.github/workflows/**`, `.github/ci-paths.yml`, and action/dependency lock files | full relevant PR suite |

Uncertain cross-component paths are classified as `workflow` or
`shared_board_content`, never as a narrow component. New shared paths must be
added here with their producer/consumer change.

For pull requests, classification intentionally uses the pull request's
checked-out workflow and taxonomy. A change to any CI workflow or to
`.github/ci-paths.yml` itself matches `workflow`, which forces every relevant
PR suite. This fail-conservative rule protects review of classifier edits
without a second base-branch checkout, changed-file shell processing, or
other security-sensitive comparison logic. Changed-file lists are never
interpolated into shell commands.

### Main CI

Add a lightweight Ubuntu `changes` job to `.github/workflows/ci.yml`. It
publishes filter outputs; existing job names remain unchanged. On pull
requests, use `needs: changes` and Boolean job conditions:

- `metadata`: `metadata`, `workflow`, or `shared_board_content`.
- `python`: `python`, `workflow`, or `shared_board_content`.
- iOS `build` and simulator `test`: `ios`, `workflow`, or
  `shared_board_content`.
- `build-release-device` uses `github.event_name == 'push'`: it remains a
  post-merge check and does not run for pull requests or `merge_group`.

Skipped jobs remain visible, preserving the required-check surface without
allocating a macOS runner. For `push` to `main` and `merge_group`, every
eligible main CI job runs regardless of filter outputs. The Release device
build remains limited to pushes after merge.

### Workbench workflow

Apply the same taxonomy to
`.github/workflows/hangboard-workbench-release.yml` and split its current
single macOS build into component jobs for pull requests:

- Browser-only editor changes run the Workbench Node suite on Ubuntu only.
- Python/pipeline/server/packaging changes run Python tests; native checks run
only where native packaging or the shipped runtime boundary can change.
- Native-shell changes run SwiftPM/native checks.
- Shared board content runs Workbench Node and Python checks, but does not by
  itself run the native shell check.

The existing stable `build` job identifier and display name, `Build verified
arm64 workbench`, remain unchanged. That job stays visible but skipped on pull
requests while the component jobs run. Add a `merge_group` trigger; because
`build` uses `github.event_name != 'pull_request'`, merge-queue entries execute
its complete Python, Node, native, build, identity, smoke, and archive
validation. Publishing remains limited to a push to `main` or a manual
`workflow_dispatch` on `main`, so `merge_group` validates but never publishes.
Release artifacts therefore never rely on partial path classification.

### Testing and safety

Use job-level conditions only with Boolean filter outputs. Configuration
contracts parse YAML through the repository's Ruby YAML convention and prove:

- editor-only: Workbench Node true; Python and iOS false;
- Python-only: Python true; iOS false unless a shared path changes;
- iOS-only: iOS true;
- shared board/export: Python and iOS true;
- workflow/taxonomy: full relevant PR suite;
- both classifier jobs check out content before `paths-filter` and retain
  `contents: read` plus `pull-requests: read`;
- shared board content selects Workbench Node and Python, not native;
- main CI keeps `build-release-device` push-only while `merge_group` runs the
  other complete integration jobs;
- Workbench `merge_group` runs the stable full `build` job but cannot run the
  publishing job;
- `push` and `merge_group` eligible gates do not depend on filter outputs.

The contracts assert workflow behavior and configuration structure. This
design document records the policy; it is not treated as a runtime test.

## Acceptance criteria

- Editor-only pull requests run Node Workbench tests, not Python or iOS/Xcode.
- Python-only pull requests skip iOS/Xcode unless shared content changes.
- iOS and shared board/export changes run iOS build and simulator tests.
- Workflow/taxonomy edits are conservative and run full relevant PR coverage.
- Main pushes and merge-queue entries run every eligible suite; the main CI
  Release device build remains push-only.
- Workbench merge-queue entries run the complete stable `build` validation and
  never publish a release.
- Existing required job identifiers and names remain stable, including
  Workbench `build` / `Build verified arm64 workbench`, and skipped PR jobs
  remain visible.
- Browser-only Workbench PRs do not build a macOS release app.

## Risks and mitigations

Under-classified shared paths are the main risk. One shared taxonomy,
conservative `workflow` matching for workflow/taxonomy edits, configuration
contracts, and full eligible `main`/merge-queue runs reduce it. Reading classification
from the PR checkout is safe under that conservative rule and avoids adding a
trusted-base checkout plus shell comparison machinery. Job-level conditions
avoid disappearing required workflows. The immutable action pin prevents
unreviewed action updates from changing path-classification behavior.
