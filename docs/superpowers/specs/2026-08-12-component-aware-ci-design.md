# Component-Aware CI Design

**Date:** 2026-08-12

## Goal

Reduce pull-request latency and macOS runner use by running each CI component
only when changed files can affect it, while retaining complete validation for
merge-queue entries and changes pushed to `main`.

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
the immutable v4.0.3 commit. Its pull-request mode requires
`pull-requests: read`.

| Filter | Conservative paths | Effect |
| --- | --- | --- |
| `ios` | `HangTen/**`, `HangTenTests/**`, `HangTen.xcodeproj/**`, iOS scripts, `Package.resolved`, and iOS CI/release workflow files | iOS build and simulator tests |
| `python` | `Tools/HangboardPipeline/**`, Python Workbench server/runtime/packaging files, Python tests, `pyproject.toml`, and Python CI/release workflow files | Python pipeline and Workbench tests |
| `workbench_web` | Workbench HTML/CSS/browser JavaScript and Node tests, plus Node CI/release workflow files | Workbench Node tests |
| `workbench_native` | `Tools/HangboardWorkbench/macos/**` and native packaging/release files | SwiftPM/native Workbench checks |
| `shared_board_content` | `Hangboards/**`, `Tools/HangboardPipeline/boards/**`, `HangTen/Resources/BoardLibrary.json`, board export/catalog scripts, and catalog inputs | Python and iOS; relevant Workbench checks |
| `metadata` | App Store metadata and its validation script | metadata validation |
| `workflow` | `.github/workflows/**`, `.github/ci-paths.yml`, and action/dependency lock files | full relevant PR suite |

Uncertain cross-component paths are classified as `workflow` or
`shared_board_content`, never as a narrow component. New shared paths must be
added here with their producer/consumer change.

### Main CI

Add a lightweight Ubuntu `changes` job to `.github/workflows/ci.yml`. It
publishes filter outputs; existing job names remain unchanged. On pull
requests, use `needs: changes` and Boolean job conditions:

- `metadata`: `metadata`, `workflow`, or `shared_board_content`.
- `python`: `python`, `workflow`, or `shared_board_content`.
- iOS `build` and simulator `test`: `ios`, `workflow`, or
  `shared_board_content`.
- `build-release-device` stays push-only.

Skipped jobs remain visible, preserving the required-check surface without
allocating a macOS runner. For `push` to `main` and `merge_group`, every main
CI job runs regardless of filter outputs. These are the complete integration
gates.

### Workbench workflow

Apply the same taxonomy to
`.github/workflows/hangboard-workbench-release.yml` and split its current
single macOS build into component jobs for pull requests:

- Browser-only editor changes run the Workbench Node suite on Ubuntu only.
- Python/pipeline/server/packaging changes run Python tests; native checks run
only where native packaging or the shipped runtime boundary can change.
- Native-shell changes run SwiftPM/native checks.
- Shared board content runs conservative Python and relevant native checks.

On `push` to `main` and `workflow_dispatch`, retain the complete signed/release
pipeline exactly as today. Release artifacts must never rely on partial path
classification.

### Testing and safety

Use job-level conditions only with Boolean filter outputs; never interpolate
attacker-controlled changed-file lists into shell commands. Add a small
configuration test that parses the taxonomy/workflow and proves:

- editor-only: Workbench Node true; Python and iOS false;
- Python-only: Python true; iOS false unless a shared path changes;
- iOS-only: iOS true;
- shared board/export: Python and iOS true;
- workflow/taxonomy: full relevant PR suite;
- `push` and `merge_group`: all jobs run even if filters are false.

## Acceptance criteria

- Editor-only pull requests run Node Workbench tests, not Python or iOS/Xcode.
- Python-only pull requests skip iOS/Xcode unless shared content changes.
- iOS and shared board/export changes run iOS build and simulator tests.
- Workflow/taxonomy edits are conservative and run full relevant PR coverage.
- Main pushes and merge-queue entries always run full suites.
- Existing required job names remain stable and skipped jobs remain visible.
- Browser-only Workbench PRs do not build a macOS release app.

## Risks and mitigations

Under-classified shared paths are the main risk. One shared taxonomy,
conservative defaults, configuration tests, and full `main`/merge-queue runs
reduce it. Job-level conditions avoid disappearing required workflows. The
immutable action pin prevents unreviewed action updates from changing path
classification behavior.
