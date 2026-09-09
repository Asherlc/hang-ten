# Task 1 fix 1 review — media-aware workout matching

Review target: `8a99889c4ba19af22be0e581795834085e93a2b8`, re-reviewed with
the original runtime implementation `e1e53c19ab3f12c517fb32793d4c49304c353392`
and the earlier non-approval at `81414e3f`.

Reviewed against Task 1 in
`docs/superpowers/plans/2026-09-08-package-driven-3d-runtime-and-tools.md`,
the model-first runtime data flow in
`docs/superpowers/specs/2026-09-08-beastmaker-1000-3d-design.md`,
`AGENTS.md`, and the complete `migrate-hangboard-to-3d` and
`validate-hang-ten-ios` skills.

## Verdict

**Approved.** `8a99889c` closes the test/evidence gaps recorded in
`task-1-review.md`; no production change was needed or made. The only audit
note is a non-runtime historical lifecycle naming variance documented below.

## Production-boundary audit

- `BoardHold` remains logical metadata. Its only display-derived API resolves
  raster frames from the selected media's union and model frames from that
  selected media descriptor's `facePlaneAABB`
  (`HangTen/Models/TrainingModels.swift:724-738`). Its declaration contains no
  stored frame, presentation ID, descriptor, or descriptor-bound field.
- `TrainingBoard.holds(in:)` admits only holds resolvable in the exact supplied
  presentation (`TrainingModels.swift:884-889`). Board-map content and detail
  entries consume that scoped set and re-resolve in the same selected
  presentation (`HangTen/Views/BoardMapView.swift:17-31,86-103`).
- Workout candidates are filtered through `board.defaultPresentation`
  (`WorkoutActivityRecording.swift:418-425`), and every side/bilateral frame
  calculation resolves through that same default only
  (`WorkoutActivityRecording.swift:410-415,685-766`). The former traversal of
  every presentation is absent from the `e1e53c19` diff.
- Source-boundary search found descriptor AABBs only on model media and package
  decoding; no production `BoardHold` receives copied descriptor geometry.

## Regression audit

- The synthetic model fixture keeps the AABB in `BoardModelMedia.descriptor`,
  not in the logical hold (`WorkoutActivityRecordingTests.swift:91-181`).
  `testModelDescriptorFacePlaneAABBResolvesExactlyForWorkoutMatching` asserts
  the exact `0.1, 0.2, 0.3, 0.4` resolved frame and scoped availability
  (`:282-289`).
- `testWorkoutMatchingTreatsMissingDefaultMediaMappingAsUnavailable` proves a
  descriptor-absent logical ID resolves to `nil`, is removed from
  `holds(in:)`, and cannot resolve an explicit ID target (`:291-304`).
- The default-model/alternate-raster fixture puts the right pocket only on the
  alternate presentation. It verifies single-side matching retains the sole
  available default hold and a bilateral substitution stays unresolved
  (`:306-349`). This does not weaken side semantics: selection still chooses
  the sole eligible equipment object; it prevents the alternate's geometry
  from manufacturing a right-side or two-hand candidate.
- The repaired fractional-depth fixture now supplies selected raster geometry
  for both logical holds (`:778-804`), so it no longer relies on an invalid
  empty-media fallback. The expected nearest measurement behavior is unchanged
  (`:806-811`).
- The original empty-raster Board Map regression remains present
  (`BoardPackageStoreTests.swift:79-108`). The unchanged Compact II regression
  still requires `sloper-round-center` (`BoardTargetSubstitutionTests.swift:248-256`).

## Retained execution and cleanup evidence

- `Package.resolved` locks Amplitude Swift `1.18.8` / `9479e…`, AmplitudeCore
  `1.5.0` / `6ed184…`, analytics connector `1.3.2` / `982b4c…`, and Sentry
  `8.58.4` / `f196cb…`. The retained script copies only those four existing
  source-package repositories/checkouts into workspace-local paths, resolves
  with `-disableAutomaticPackageResolution`,
  `-onlyUsePackageVersionsFromResolvedFile`, and `-skipPackageUpdates`, and
  uses the same isolated paths for XCTest
  (`.context/shaky-rat-task1-fix-1-xctest.zsh:57-118`). The resolver log lists
  exactly those four resolved packages
  (`.context/shaky-rat-task1-fix-1-resolve.log:1-31`).
- The retained raw log reports 108 `BoardPackageStoreTests`, 63
  `BoardTargetSubstitutionTests`, and 38 `WorkoutActivityRecordingTests`: 209
  total, zero failures, and `** TEST SUCCEEDED **`
  (`.context/shaky-rat-task1-fix-1-focused-3.log:4203-4424`). It also records
  each new regression and the Compact II test passing. Independent inspection
  of `.context/shaky-rat-task1-fix-1-focused-3.xcresult` reports 209 passed,
  0 failed, and 0 skipped.
- The script owns a workspace-local derived-data path, source-package copy, and
  package cache and removes those exact paths in its exit trap
  (`.context/shaky-rat-task1-fix-1-xctest.zsh:40-50`). They are absent now;
  both pending and owned simulator manifests are empty.
- Historical variance: the owned simulator was named `Hang Ten Paseo shaky-rat
  Task1Fix1` (`xctest.zsh:81-89`), whereas the plan/validation skill specifies
  the `… Review` suffix. It still meets the required exact workspace ownership
  prefix, and the report records deletion. A fresh read-only `simctl list`
  query could not independently recheck current absence because
  CoreSimulatorService returned connection-refused; no simulator was created
  or modified for this review.

## Review checks

- `SRCROOT=$PWD scripts/verify-board-source-boundary-manifest.sh` — exit 0.
- `git diff --check e1e53c19^..8a99889c` — exit 0.
- `git diff --check` — exit 0 before this review artifact.

