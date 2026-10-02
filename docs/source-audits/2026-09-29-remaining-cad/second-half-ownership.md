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

### Runtime continuation — uninterrupted first boot

The [new Pro startup appendix](zlagboard-pro/runtime-uninterrupted-2026-10-02/review.md)
records one uninterrupted 900-second first boot on a fresh isolated iOS 26.5
device. It remained in AddressBook migration; all 29 Home checks were negative.
No build, install or app capture ran, so Pro remains at 0/28 fresh app views.
The exact temporary Simulator, DerivedData/result paths and helper processes
were verified absent after cleanup. No shared service was restarted.

The [Evo diagnostic preparation](zlagboard-evo/diagnostic-preparation-2026-10-02/review.md)
addresses the incomplete earlier trace with unique view/scene identities and
complete bounded state snapshots. Its scratch patch passed `git apply --check`
and Swift parsing but remains unapplied, untypechecked and unrun; no fifth
production fix ships. All five reserved app/test paths remain unchanged and
the renewed reservation was explicitly released. A working isolated Simulator
environment is required before these runtime checks can continue.
All six native geometry approvals and all prior proof bytes remain unchanged.

### PR-readiness continuation — fresh baseline and reproduced runtime defect

The [fresh Pro baseline appendix](zlagboard-pro/runtime-baseline-pr-readiness-2026-10-02/README.md)
records all 28 selections, elevated views, physical picking and camera reset in a
new isolated Simulator that reached Home naturally. The baseline executable is
`7a6867151307170dd0993a6d6492500d3fd46467`; package bytes are unchanged. Both
Pro portrait and Evo landscape workout transitions still fail. These new agent
checks do not imply user acceptance or alter the historical failed packets.

The parent renewed the five renderer/test-path reservation and published exact
parent ref `8b1bbd0858ca3e81bc7c43ad842a80ff9ca2138b` for comparison. Temporary
scene diagnostics are now running in this workspace; this documentation commit
ships no production renderer fix. The registered temporary Simulator and build
artifacts remain live under their cleanup controller while validation continues.
No parent/main integration or out-of-scope package edit is included.

### Complete rendering diagnostics — no production repair established

The [Evo diagnostic appendix](zlagboard-evo/runtime-diagnostics-2026-10-02/README.md)
retains complete state traces, raw captures, command outcomes, and temporary
source patches. Multiple independent host probes still fail; recreating the
board display view also caused disappearance. One hand-host-suppressed run
passed between failing controls. Its initial visual misclassification remains
retained with an explicit correction. These results motivate an independent
architecture review; they do not establish an SDK root cause or a production fix.

The five-path reservation remains active. Parent exact published ref is now
`d0a54fef261e1c0a7d6f70f1b0db5178d351f0f7`; scratch integration preparation is
being refreshed for its Plateau package and lock changes. Canonical packages,
review queue, delivery lock and human acceptance records remain unchanged here.
Owned validation resources remain live under the existing cleanup controller.
