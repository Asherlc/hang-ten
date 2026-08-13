# Final whole-branch review fixes

Date: 2026-08-12
Branch: `audit-hangboard-image-source-of-truth`

## Findings resolved

- Serialized every Workbench package publication on the stable `Hangboards/`
  directory inode, so board-scoped jobs cannot race catalog snapshots.
- Replaced in-place catalog writes and stale-backup restoration with a fsynced
  sibling catalog followed by `os.replace` as the transaction commit point.
  Package changes roll back under the same catalog-wide lock before commit.
- Allowed an existing canonical ID/path pair to be replaced in place, including
  draft-to-approved transitions and approved package revisions. ID aliases,
  path aliases, malformed packages, duplicate IDs, and duplicate paths remain
  rejected.
- Marked the Xcode package-staging phase intentionally always out of date. The
  phase therefore reruns for nested JSON/PNG changes instead of treating the
  top-level directory and catalog output as complete dependency declarations.

## Regression coverage

- Concurrent different-board publications preserve both catalog entries.
- A failing publication cannot restore a catalog snapshot older than another
  successful publication.
- Draft-to-approved replacement and approved revision replacement preserve a
  single canonical ID/path entry.
- Failed replacement preserves the prior package and exact catalog bytes.
- Existing ID/path aliases remain rejected.
- Repeated staging refreshes changed nested package bytes.
- The Xcode project lint requires the staging phase to be always out of date.

## Verification

- Focused Python:
  `python -m pytest Tools/HangboardPipeline/tests/test_workbench_end_to_end.py Tools/HangboardPipeline/tests/test_board_package_staging.py -q`
  — 41 passed.
- Full Python:
  `python -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q`
  — 873 passed, 7 skipped.
- Full Workbench Node:
  `node --test Tools/HangboardWorkbench/tests/*.test.js`
  — 211 passed.
- Canonical catalog:
  `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`
  — passed.
- Xcode Debug simulator build:
  `xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData-final-review-fixes build`
  — `** BUILD SUCCEEDED **`; the build log confirms the staging phase runs
  during every build.
- `git diff --check` — passed.
