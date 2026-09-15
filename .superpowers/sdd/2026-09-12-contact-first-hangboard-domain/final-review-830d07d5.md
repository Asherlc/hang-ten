# Final release-blocking review: contact-first hard cut

Date: 2026-09-13  
Reviewer: independent controller review  
Reviewed commit: `830d07d58fe7c448d292ad8679f405a51b3a4b6c`  
Reviewed ref at review start: `origin/replace-2d-rasters-downloaded-models`  
Task 6 base: `3a95c9762bbab2c84dddadd9c070ddfea253c818`  
Verdict: **FAIL — not ready for release handoff**

## Review basis

I read the repository instructions, approved design, task plan, SDD ledger,
Task 6 report, and the `receiving-code-review` and
`verification-before-completion` instructions. I then inspected the exact
remote commit and its parent diff rather than relying on the reports. The
worktree and remote ref both resolved to the reviewed commit before this report
was written.

## Critical finding

### C1. Board-specific source-linked work is explicitly allowed to lose its factual target and record as self-selected

The fail-closed distinction required by the final review is not implemented.
`PlanLibraryDefinition` permits any non-custom source-linked active step to be
untargeted; `allowsSourceLinkedUntargetedWork` at
`HangTen/Models/PlanStorage.swift:1078` does not require `plan.boardID == nil`.
The runtime repeats the same rule at
`HangTen/Models/WorkoutActivityRecording.swift:565`, and the empty-target path
at `HangTen/Models/WorkoutActivityRecording.swift:505` emits
`.selfSelected` at line 516.

This is demonstrably the current intended behavior, not only a missing test:
`HangTenTests/WorkoutActivityRecordingTests.swift:534` exercises targetless
source-linked work through the helper at line 276, whose plan is explicitly
bound to `board.id` at line 288, and expects a `selfSelected` activity record.
Thus a factual board-specific plan can be accepted without its required
contact target instead of failing closed. Generic source-only work and
board-specific factual work are not separated at either validation or
recording time.

## Important findings

### I1. Schema-v2 activity unknown-field rejection is not recursive

The activity metadata, segment, target, snapshot, measurement, and
`ContactRequirement` decoders inspect their complete key sets. However,
`ResolvedContactSnapshot.requirement.depthRangeMillimeters` reaches
`MillimeterRange`, whose decoder at `HangTen/Models/PlanStorage.swift:175`
uses only a typed `CodingKeys` container and never compares `allKeys` with its
allowed keys. Swift's keyed `Codable` decoding ignores an unrecognized member
at that level. A version-2 activity payload can therefore carry an unknown
field inside `depthRangeMillimeters` while all enclosing strict checks pass.

The negative matrix in
`HangTenTests/WorkoutActivityRecordingTests.swift:1326-1399` covers the root,
segment, snapshot, and measurement boundaries, but not this nested range
object. The Task 6 report's claim that unknown keys are rejected at every
affected nested boundary is therefore too broad.

### I2. Most mature Workbench frontend integration coverage was deleted, not retained or migrated

The Task 6 parent-to-final diff deletes these suites in full:

- `Tools/HangboardWorkbench/tests/react-app.test.tsx` — 1,341 lines
- `Tools/HangboardWorkbench/tests/react-editor.test.tsx` — 3,350 lines
- `Tools/HangboardWorkbench/tests/workbench-modules.test.ts` — 1,178 lines

The replacements add 627 lines across
`contact-app.test.tsx`, `contact-contract.test.ts`, and
`contact-editor.test.tsx`. The TypeScript/TSX test count falls from 289 to 95.
Of the current 95 tests, 81 are the retained path-editor unit suite and only 14
exercise the new contact app/contract/editor boundary. The new app suite has
two cases (`contact-app.test.tsx:138` and `:167`), the contract suite five
(`contact-contract.test.ts:40-90`), and the editor suite seven
(`contact-editor.test.tsx:169-315`).

The deleted coverage included autosave persistence and debounce/retry,
dirty/stale/failed save behavior, branch switching and pull-request flows,
save conflicts and request validation, undo/redo and drag cancellation,
touch/pointer behavior, guide snapping, constraint manipulation, malformed
geometry rollback, and a much broader set of direct-path operations. Those
production paths remain. Passing 95 tests proves the smaller replacement
suite, but it does not support the Task 6 report's statement that the mature
editing/save/conflict/GitHub behavior "remain covered," and it violates the
release criterion that tests be retained rather than simply deleted.

### I3. The Workbench README contradicts the tracked artifact state and the Task 6 report

`Tools/HangboardWorkbench/README.md:29` calls `app.js` "checked-in." In fact,
`.gitignore:23` ignores `/Tools/HangboardWorkbench/app.js`, and `git ls-files
Tools/HangboardWorkbench/app.js` returns no path. The Task 6 report correctly
says the generated bundle is ignored and is not described as a tracked
artifact, but the active operational README does describe it as tracked. This
leaves the clean-checkout/hosted artifact contract inaccurate.

## Requirements checked without a separate finding

- The production Workbench parser is schema-v3/contact-first. Contact facts
  are sourced from `contacts[]`; raster geometry is read and saved through
  `presentations[].media.contactGeometry`. `open_package` rejects a model
  presentation as noneditable, and PNG inspection is reached only for raster
  media. Direct canonical path and operator-selected constraint editing remain
  present in `src/useContactEditor.ts` and the path editor.
- `Tools/HangboardModels` contains exactly the eight retained contact-native
  importer/descriptor/verifier files and tests asserted by the hard-cut audit.
  The schema-v2 compiler, migration manifests, baselines, renderers, wrappers,
  and the two obsolete package migration scripts are absent.
- The focused hard-cut scan found no live former plan/persistence adapter in
  production Swift or Workbench source. The only production
  `schemaVersion == 2` match is the separate bundled grip-hand mesh format in
  `GripHandModelView.swift`, not a hangboard package or plan contract. The
  ignored compiled Workbench bundle has no match for the reviewed prohibited
  adapter/wire tokens. Current board package JSON has no schema-v1/v2 root or
  old hold-geometry fields.
- No Task 6 diff touches `Hangboards/yy-baguette-evo`. Fresh hashes are:
  `primary.usdz` =
  `c984434edc54cfc6ec7b950a710e03e80b2514a5c5919e5fb7d1dde48e65e088`,
  `primary.model.json` =
  `f1d44e9f6e5ce76e8bc3cebb912d1bc594e375da467e01a2566b6191281e148d`,
  and `board.json` =
  `0bfd347089ab8250957789aae8ce29e75800bbfc8b15e977c33da68eb25df473`.
  The tracked Baguette re-audit at
  `docs/source-audits/2026-09-10-imported-model-packages.md:184-236`
  truthfully limits fresh-checkout reproducibility to tracked outputs and
  tests, and identifies ignored/external source evidence and approval as not
  branch-contained.
- Other inspected Task 1-4 hard-cut boundaries remain contact-native: board
  packages require v3, model descriptors bind contacts, raster paths stay the
  rendering/hit-test source, recorded resolved targets snapshot revision,
  requirement and contact IDs, and the old persistence versions/keys fail at
  their explicit outer boundaries. Findings C1 and I1 are the exceptions that
  prevent an all-clear on plan and persistence constraints.

## Fresh verification evidence

| Check | Result |
| --- | --- |
| Commit/ref identity before report | `HEAD` and `origin/replace-2d-rasters-downloaded-models` both `830d07d58fe7c448d292ad8679f405a51b3a4b6c` |
| Focused hard-cut, Workbench contact package, and retained model tests | `29 passed in 16.01s` |
| Workbench TypeScript check and current frontend suite | `95 passed`; the first sandboxed attempt was blocked from opening the test runner's local IPC socket, and the identical host-permitted run passed |
| Generated bundle prohibited-token scan | no matches |
| Baguette package diff from Task 6 base | no changes |
| Baguette hashes and LFS object | match the tracked re-audit and Task 6 report |
| Task 6 context path | absent |
| Exact Task 6 simulator name/UUID | absent from the current Simulator device list |
| Exact Task 6 UUID/context identifier in running processes | no matches |

The historical broad-run claims remain documented in the Task 6 report:
986 repository Python tests, 32 macOS wrapper tests, 11 model tests, 62 board
inventory validations, 44 metadata audits, and exit-zero iOS test/build runs.
The report explicitly does not claim an iOS test count and says its result
artifacts were removed during owned cleanup. I did not rerun those broad suites
after source inspection established release blockers; the focused fresh checks
above were sufficient to validate the relevant green claims and distinguish
them from the uncovered failures.

## Final disposition

**FAIL.** Commit `830d07d58fe7c448d292ad8679f405a51b3a4b6c` is not
objectively ready for release handoff. C1 violates the required factual
board-specific fail-closed behavior. I1 leaves the promised recursive strict
activity contract open, I2 removes core regression evidence instead of
migrating it, and I3 makes the active Workbench artifact instructions
factually inconsistent with the repository. No fixes were made in this review.
