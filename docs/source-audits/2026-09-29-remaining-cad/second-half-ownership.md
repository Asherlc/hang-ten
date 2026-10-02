# Parallel review ownership — 2026-10-01

Workspace and branch: `placid-badger-cad-second-half`, based on
`9399160729fcc418cedf47344b41163d244b5d96`.

This workspace exclusively reviews #16 `yy-baguette`, #17 `yy-baguette-evo`,
#18 `yy-penta-evo`, #19 `yy-travelboard`, #20 `zlagboard-evo`, and
#21 `zlagboard-pro`, in that order, one board at a time with the user.
#16 was accepted by the user on 2026-10-01 (reply “y”, displayed commit
`a77034f`). #17 was accepted on 2026-10-01 (reply “y”, displayed commit `112121501`).
#18 and #19 were subsequently accepted by explicit replies; their acceptance
records are committed in `c63554f9f` and `04979bde9`. #20 geometry was accepted on 2026-10-02 (reply “Y”, displayed commit
`b60f41c59`). Workout highlight transitions remain unresolved on iOS 26.4 and
26.5; full app-workflow validation is not passing. #21’s displayed native
geometry was accepted on 2026-10-02 (reply “Y”, displayed commit `e28886489`).
All six allocated boards now have geometry approval; #21 fresh app review
remains blocked and pending with 0/28 contacts checked.

The parent `placid-badger` owns #9–15; accepted #1–8 and all other packages
are outside this workspace's scope. Shared compiler, schema, renderer, and
rope-solver changes require coordination with the parent. Global queue and
delivery metadata edits must preserve all other package records. Integration
must retain both branches' substantive review records.

Scratch belongs under `.context/placid-badger-cad-second-half/`. Temporary
validation simulators carry this exact workspace name, are registered before
use, and are deleted by verified cleanup traps. This workspace and review
agent remain available; they are not temporary validation resources.

Every commit is pushed to this branch. No merge to main or the parent branch
is authorized by this allocation.

For #18, the parent explicitly coordinated the additive `terminalsByPoseID`
authoring extension with this branch. The parent retains `grooveGuides`; combining
the two is rejected. Later explicit integration must preserve its optional
`source_metadata` argument, guide dispatch and validation, alongside this
branch's pose station validation/tests and dispatch before route caching.
Coordination is retained in #18's package-local review packet.

### #18 workout pairing correction

Fresh Penta Evo workout validation exposed an existing resolver assumption: two
reused unit contacts share a local descriptor frame, so spatial bilateral
selection fails. Parent confirmed no overlapping edit to
`WorkoutActivityRecording.swift` and authorized the narrow corresponding-slot
instance branch with positive/negative regressions. Package geometry, source
facts, routine prescriptions and renderer remain unchanged by this fix. Preserve
this addition alongside the parent's independent changes at a later explicitly
authorized merge. Exact coordination is retained in #18's individual packet.

### #20 app review and shared-code reservation

The [fresh geometry review](zlagboard-evo/app-review-2026-10-02/review.md)
preserves the startup failures and unsuccessful highlight experiments. The parent
reserved `HangTen/Models/BoardModelRealityTypes.swift`, `BoardModelView.swift`,
`RootView.swift` and focused tests for investigation. All tentative app and test
edits were reverted exactly; no shared renderer fix ships with this review.
Existing Mammut finish, NUG and migration changes remain intact. Temporary
validation resources were deleted and independently checked. #20’s subsequent acceptance is recorded in `zlagboard-evo/human-review.json`;
the immutable app packet retains its original pre-acceptance status. #21’s
subsequent native-only acceptance is recorded in `zlagboard-pro/human-review.json`.

### #21 native geometry accepted; fresh app review pending

The existing Pro 2.0 source retains its native history and all 28 contacts. Narrow
top rounds and restored jug crest/corner selection coverage were independently
reviewed, exported twice with identical USDZ bytes, and checked against a fresh
descriptor reconstruction. Existing renderer wood finish and a labeled downward
camera adaptation are embedded in the source. The
[individual packet](zlagboard-pro/individual-review-2026-10-02/review.md) retains
the original/prior/current comparison and all startup failures. Fresh app validation is blocked by startup failures on isolated iOS 26.4 and
26.5 devices; both builds passed but contact coverage is 0/28. Exact temporary
resources were deleted. The user subsequently accepted the displayed native
geometry with “Y”; app validation remains pending. The immutable review packet
retains its original pre-acceptance status and failed runtime evidence.
No shared app, compiler, schema or solver files were changed for #21.
