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
All six allocated boards have geometry approval. Fresh agent checks now cover
all 28 Pro contacts; user acceptance of those app views and complete workout
validation remain pending. Historical 0/28 failure packets remain unchanged.

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

### Projection diagnostics and correction to hand-OFF interpretation

The [new Evo projection/correction appendix](zlagboard-evo/runtime-projection-correction-2026-10-02/README.md)
retains three completed failed sequences: orthographic second host, perspective
second host, and visible second host OFF. Work stopped after three runs. The
earlier claim that the historical OFF full workflow passed is withdrawn: its
settled-rest pockets were red when blue was expected. Its correctly red
next-active frame was insufficient to establish a full pass. Original reports
and bytes remain unchanged; explicit hash-bound corrections are appended.
No production fix is established, and native acceptance/package/global records
remain unchanged. The existing resource controller and path reservation remain
active while diagnosis continues.

### Standalone isolation diagnostics — workout defect still unresolved

The [Evo standalone isolation appendix](zlagboard-evo/runtime-standalone-isolation-2026-10-02/README.md)
retains the exact 210 x 36 point A/B/B/A experiment and all 80 successful
isolated board-state/color captures. The actual workout still fails; no
production repair is established. The A1 startup-scope validity failure and
separate correction, B2 single-frame black-capsule artifact, root image reviews
and raw committee responses remain explicit. Earlier packets and all geometry
acceptance records are unchanged. Reserved source and owned resources remain
under coordinated diagnosis, with exact cleanup still pending.

### Isolated timeline delivery — normal workout remains unresolved

The [Evo timeline-driver appendix](zlagboard-evo/runtime-timeline-driver-2026-10-02/README.md)
retains all 60 successful isolated A/B/C board captures at the exact 210 x 36
point viewport: task-driven state, task state under TimelineView, and monotonic
phase derived inside TimelineView. This does not reproduce or repair the actual
workout failure. Exact raw/root reviews, source snapshot, delivery analysis and
context-boundary audit are retained; previous evidence and native acceptances
remain unchanged. Source reservation and owned resources stay active for
coordinated diagnosis, with cleanup pending.

### Caption/BoardMap isolation and same-binary workout contrast

The [Evo caption/BoardMap appendix](zlagboard-evo/runtime-caption-boardmap-2026-10-02/README.md)
retains 60 successful isolated C/D/E captures, exact D/E screenshot equivalence,
and the failed normal workout on the same binary. Settled rest was correctly
blue; the next active Hang remained blue despite red CPU material brackets.
The first diagnostic compile failure, narrow correction, initial and complete
normal traces, root reviews and source provenance remain exact. No production
fix or new acceptance is claimed. Prior packets and canonical/global records
remain unchanged; owned resources and source reservation stay active, with
cleanup pending.

### Passive natural-workout reproduction

The [Evo passive-workout appendix](zlagboard-evo/runtime-passive-workout-2026-10-02/README.md)
retains all 12 independently reviewed frames and the complete 147-record trace
from the unchanged C/D/E binary. With no AX/tap/Skip after launch/openURL,
first active is red, sampled rest incorrectly red, and the following natural
hang incorrectly blue after a 180.016-second rest. Late sampler/census limits
remain explicit; no middle-rest persistence or SDK root cause is claimed.
Source links, parity and analysis are retained without changing old packets or
acceptances. The workflow remains unresolved; owned resources and reservations
continue under coordinated diagnosis, with cleanup pending.

### Initial-resize isolation — qualified evidence, no workout repair

The [Evo resize appendix](zlagboard-evo/runtime-resize-2026-10-02/README.md)
retains both diagnostic builds, the invalid first F integer-arithmetic setup
with zero captures, its explicit correction, and 60 visually correct E2/F2/G2
captures. G2 has only 19/20 complete CPU brackets; the missing final after-end
record remains qualified. Black-capsule artifacts and all root/raw reviews are
retained. This isolated history does not reproduce or repair the real workout.
Earlier evidence and acceptances are unchanged. Source reservation and owned
resources remain active under coordination, with cleanup pending.

### Continuous sibling-update isolation

The [Evo continuous-siblings appendix](zlagboard-evo/runtime-continuous-siblings-2026-10-02/README.md)
retains H0a/H1a/H1b/H0b: 80 visually correct captured board states and 20/20 CPU
brackets per run at fixed placement. Timer/progress siblings in this isolated
context did not reproduce the actual-workout defect. Raw artifacts, independent
and root reviews, source/parity, committee responses and pending-next analysis
remain exact. No production fix or acceptance is claimed. Previous evidence
and canonical/global records are unchanged; owned resources and reservations
remain coordinated and live, with cleanup pending.

### Direct-root versus normal workout comparison

The [Evo root-workout appendix](zlagboard-evo/runtime-root-workout-2026-10-02/README.md)
retains the invalid extra-autostart setup and its explicit launch-only correction,
one diagnostic binary, and two valid natural workout cycles. Direct root has
12/12 correct captured colors; the normal route retains early-rest red and
following-Hang blue failures despite complete CPU correspondence. All 24 root
visual reviews, raw traces, source/parity and startup limitations remain exact.
This discriminates contexts without establishing a navigation root cause or
production fix. Earlier evidence and acceptances are unchanged; coordinated
owned resources remain live, with cleanup pending.

### Root-navigation control gate and unchanged repeat

The [Evo root-navigation appendix](zlagboard-evo/runtime-root-navigation-2026-10-02/README.md)
retains the failed direct control and exactly one unchanged repeat. Both show
early following-Hang blue at +0.25/+1 seconds, then red at +3/+5, despite
12/12 CPU brackets per run. No NavigationStack arm ran and no navigation root
cause or production fix is established. Original reports, source snapshots,
raw frames, parity and separately attributed reviews remain exact. Earlier
evidence and acceptance records are unchanged; coordinated resources remain
live with cleanup pending.

### Standalone short/long timing isolation

The [Evo timing appendix](zlagboard-evo/runtime-standalone-timing-2026-10-02/README.md)
retains both isolated timing arms: 20 captured states and 20 CPU brackets each.
Five whole representative images per arm plus exact whole-file equality support
the worker's visual result; root's separate reviews retain their narrower scope.
The original helper KeyError, frozen validator and reviewed correction remain
exact. Extending isolated preview to 180 seconds did not reproduce the actual
workout defect in these runs, and no production fix or acceptance is claimed.
Earlier packets remain unchanged; coordinated resources stay live, cleanup pending.

### Strict hand-host suppression confirmation

The [Evo strict-hands appendix](zlagboard-evo/runtime-strict-hands-2026-10-02/README.md)
retains ON/OFF/OFF-B/ON-B as FAIL/PASS/PASS/FAIL on one binary, with all
48 CPU brackets and matching observed frame/transform sets. Both OFF runs
retain zero hand constructor/make counts; ON runs retain positive paired counts
and stale early following-Hang colors. ON-B also has an incorrect early Rest
frame; exact screenshot windows qualify recovery timing. Initial and reverse
reports remain separate and immutable. The authorized sixth-file reservation
and proposal correction are retained, without expanding our board allocation.
This diagnostic contrast establishes no generic host rule or production fix.
Previous acceptances remain unchanged; coordinated owned resources stay live
and cleanup remains pending.

### Current runtime boundary — Train teardown and real hands

The [ordinary-ownership comparison](zlagboard-evo/runtime-structural-dependency-2026-10-02/README.md)
passed with all hands suppressed. Restoring real hands
[failed](zlagboard-evo/runtime-structural-real-hands-2026-10-02/README.md). The
[weak-hand census](zlagboard-evo/runtime-weak-hand-census-2026-10-02/README.md)
reproduced the failure while the earlier hand root/camera were absent at all
capture brackets and the current pair remained attached. Sparse observations
do not establish continuous lifetime, GPU activity, or a framework cause. No
production repair or new human acceptance is established. The subsequent
[same-binary perspective comparison](zlagboard-evo/runtime-weak-hand-perspective-2026-10-02/README.md)
also failed; no camera reversal or production camera change followed.

The coordinated reservation now covers the original five renderer/test paths
plus `HangTen/Views/GripHandModelView.swift` and `HangTen/Views/TrainView.swift`.
Temporary diagnostics remain uncommitted; owned validation resources remain
registered under the existing cleanup controller. Exact final integration and
cleanup verification are still required before readiness is claimed.

The [sync-delivery counter observation](zlagboard-evo/runtime-sync-delivery-counter-2026-10-02/README.md) still fails Rest visually, despite correct phase assignments and no repeated board synchronization in the sampled Rest interval. The next Hang is correct in this run; that difference does not establish repair. No iPhone is available, so conclusions remain Simulator-only. Seven shared-path reservations remain active for temporary diagnostics; canonical packages and human acceptance are unchanged.

The [pre-start-hand control](zlagboard-evo/runtime-prestart-hand-control-2026-10-02/README.md) reproduces stale Rest and next-Hang colors. Its original prospective checker remains failed: the first preceding board snapshot occurred before normal hand construction. A separate timing audit confirms construction before the screenshot, while retaining the missing first pre-capture ownership observation; the remaining 23 ownership observations pass. The matched action is pending and no production change is selected.

The [first pre-start suppression action](zlagboard-evo/runtime-prestart-hand-action-invalid-2026-10-02/README.md) is invalid for color comparison: no qualified initial sequence was captured. Its additive timing correction records delayed scene construction and later CPU phase progression, without claiming the workout never started. Original failure evidence is unchanged. One unchanged repeat is authorized separately; no remedy or acceptance is established.

The [single unchanged pre-start action repeat](zlagboard-evo/runtime-prestart-hand-repeat-invalid-2026-10-02/README.md) also lacks the required initial capture sequence. Its shorter initial screenshot and later CPU progression are retained without a color verdict. No further identical repeat is planned; the next boundary is a 30-second startup observation. No production repair, board acceptance, or integration is established.

The [bounded startup observation](zlagboard-evo/runtime-startup-observation-2026-10-02/README.md) completed with prompt countdown and board loading; the earlier long initialization gap did not recur. Added diagnostics and asynchronous external polling prevent a causal repair claim. No workout color sequence was captured, and early hand readiness remains unproven. The unanswered pre-start-hand comparison requires a fresh failing control in this same binary before an action; no production change or acceptance follows.

The [startup-instrumented full-color control](zlagboard-evo/runtime-startup-full-color-control-2026-10-02/README.md) validly reproduced red Rest and blue following-Hang pockets. All nine original validators and the separate timing audit pass, including all 24 hand ownership points. Its matched action is separately retained when complete; this control establishes no remedy or new acceptance.

The [matched full-color action](zlagboard-evo/runtime-startup-full-color-action-invalid-2026-10-02/README.md) stopped at its prospective initial-sequence deadline with no timed images. The last marker precedes synchronous audio preparation; no return marker was observed within 30 seconds. The comparison is inconclusive and stopped without a retry. A separate source audit identifies possible preparation work, not its runtime cause. Next work is a temporary on-demand-hand-image feasibility prototype; no production renderer change, acceptance, or integration is selected.

The [static hand-image prototype](zlagboard-evo/runtime-hand-image-static-2026-10-02/README.md) retains the initial pre-render viewport failure and the later technical pass with visual failure: inverted, darker hands. Both original freezes and prototype/helper history are preserved. This is not workout validation or a production repair; native assets and human acceptance remain unchanged. Existing Simulator/DerivedData ownership stays with this workspace’s root controller.

The [neutral hand-image feasibility packet](zlagboard-evo/runtime-hand-image-neutral-2026-10-02/README.md) preserves the upright-but-dark orientation-only failure and the fixed neutral-lighting static cue result on cream and black. This is an explicitly adapted appearance, not live-renderer equivalence, workout validation, production repair, or acceptance. Exact diagnostic source/build/runtime proofs are retained; package bytes remain unchanged and the existing Simulator/DerivedData stay with the root controller.

The [first LIVE control for the hand-image workout comparison](zlagboard-evo/runtime-hand-image-workout-live-invalid-2026-10-02/README.md) is invalid with zero timed captures; the30-second startup gate expired before a qualifying first Hang. Its last marker precedes audio preparation, without establishing a cause. Exact app PID absence is verified despite the preserved termination error; persistent Simulator/DerivedData remain root-owned. No IMAGE comparison, retry, production repair or acceptance is established.

A later exact-PID [crash supplement](zlagboard-evo/runtime-hand-image-workout-live-invalid-2026-10-02/raw/hand-image-live-startup-crash-audit/report.json) identifies that LIVE control’s main-thread audio RPC-timeout abort while accessing `AVAudioEngine.mainMixerNode`. The original invalid control audit remains unchanged; underlying service cause and any connection to stale board highlighting are unestablished. No repair or new acceptance is claimed.

The [first muted LIVE control](zlagboard-evo/runtime-hand-image-muted-first-census-2026-10-03/README.md) remains invalid with 1/12 scheduled images: its original sparse-census gate stopped after the first Hang. Current hand construction/make preceded that image and the later census shows attachment; the preceding census gap does not prove absent hands. Root reviewed that first image as correct, but the full color sequence is unknown. Exact app cleanup passed; existing Simulator/DerivedData remain root-owned. No IMAGE comparison, production repair or new acceptance follows.

The [muted LIVE-b clock-affected result](zlagboard-evo/runtime-hand-image-muted-clock-2026-10-03/README.md) captured all 12 images but visually failed: the following Hang stayed blue at +0.25/+1 seconds. Eight validators pass; the original natural-Rest epoch check fails and remains failed. An additive audit records four clock-domain discontinuities and locally supported capture brackets without proving uninterrupted execution or qualifying a new control. Exact app cleanup passed; root retains the Simulator/DerivedData. No IMAGE authorization, product repair, acceptance, or PR readiness follows.

The [muted awake LIVE-c control](zlagboard-evo/runtime-hand-image-muted-awake-pass-2026-10-03/README.md) passes all 12 root-reviewed images, nine validators, and the prospective clock check. Its failing-control prerequisite is lost: no IMAGE trial or retry is authorized. The tested context includes muted audio, temporary DEBUG Train unmount, diagnostics, and an idle-sleep assertion; no sleep causality or production repair is established. The first-before census remains explicitly incomplete with 23 other ownership observations. Exact app/assertion/capture-child cleanup passed; root retains Simulator/DerivedData. Prior failures and human approvals remain unchanged.

The [second-half canonical/integration snapshot](second-half-canonical-integration-2026-10-03/README.md) verifies unchanged #16–21 package/LFS and review records, preserves both owners’ full records in an unapplied 405a/9b0a integration preview, and records restoration of five diagnostic app files plus six unchanged test files. The 87-file solver/test overlay is byte-identical to its prior 84-test proof. No merge, runtime repair, new human approval or PR readiness is established; pristine runtime evidence is recorded separately when complete.

The [pristine Evo muted/awake run](zlagboard-evo/runtime-pristine-muted-awake-2026-10-03/README.md) retains all 44 scheduled whole images and passing mechanical checks, but visually fails: selected pockets stay blue throughout the captured second Hang. Initial hands also appear late. The earlier diagnostic pass does not clear this result. Pro runtime is deferred; no IMAGE workout ran, acceptance changed, or production repair was adopted. Exact app/assertion cleanup passed; Simulator/DerivedData remain controller-owned. A separate temporary Train-only comparison is pending.

The [minimal Train-only comparison](zlagboard-evo/runtime-train-only-2026-10-03/README.md) fails visually in both same-binary arms despite complete 44-image capture and mechanical checks. Removing the covered Train board subtree alone leaves stale Rest and following-Hang colors. Both original raw freezes and full reviews are retained, including early missing hands and differing external-offset phase boundaries. No reversal or production adoption follows. A separate DEBUG hand-output comparison is pending, with Train removal common and a fresh live-hand control required.

The [clean hand-output comparison](zlagboard-evo/runtime-clean-hand-output-2026-10-03/README.md) fails in both same-binary arms: on-demand hand images do not restore timely board highlights. Each arm retains all 44 captures, whole-image reviews, and passing mechanical checks; early missing cues and the image lighting adaptation remain explicit. No reversal, production workaround, new acceptance, or PR readiness is claimed. All seven reserved source/test paths are restored to their committed bytes and their no-overlap reservation is released. The exact owned Simulator, DerivedData, result bundles, and module cache were deleted and independently verified absent; this workspace and its agents remain available. Evo workout correctness, Pro fresh runtime/app review, and explicit combined integration remain outstanding.
