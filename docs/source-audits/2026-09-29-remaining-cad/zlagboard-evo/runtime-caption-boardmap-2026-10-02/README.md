# Evo caption/BoardMap isolation and same-binary contrast — 2026-10-02

All **60 isolated C/D/E board-state/color captures passed**. The subsequent actual workout on the **same installed diagnostic binary failed**: the next active hang displayed blue pockets despite CPU active-red material state. No production fix, general workout pass or new human acceptance is established.

| Isolated arm | Changed boundary | Result |
| --- | --- | --- |
| C | Monotonic TimelineView phase, changing caption, direct BoardModelSurface | Clear/red/blue/red/blue passed |
| D | Same delivery and Surface, constant caption text | Clear/red/blue/red/blue passed |
| E | Same constant caption, existing unmodified BoardMapView wrapper | Clear/red/blue/red/blue passed |

Each arm retains the measured **210 × 36 point** actual leaf viewport, five phases and four whole captures per phase. D/E's corresponding 20 screenshots are exact byte matches. [The frozen report](raw/caption-cde-findings.json), SHA-256 `56c7f949ec78a90fda20ed885514324a595e1f4f5527e2477cc0ec67dbe788ed`, links complete timing/input/material/placement checks and per-run root image reviews. All raw proposal/applied files, including early versions, remain unchanged.

## Actual workout comparison

[Root's whole-image review](raw/caption-normal-workout-landscape/root-visual-review.json) records Step1 Hang00:05 red; early Rest03:00 red; settled Rest02:52 blue; Get Ready00:02 blue; then Step3 Hang00:07 and00:05 incorrectly blue. The settled rest is correct—this packet does not classify the entire rest interval as failed. The early frame requires its recorded mutation timing for interpretation.

[The frozen normal summary](raw/caption-normal-workout-landscape/frozen-summary.json), SHA-256 `eb77bf0d31b44d228442cfd3f9adb2b164ead4df1557f2e22a2386055afc2d3f`, verifies all five installed Mach-O hashes still match. Complete trace records42/44 bracket the visibly blue Hang00:05 screenshot with active-red CPU material in the same scene, roughly three seconds after mutation. [Detailed correspondence](raw/caption-normal-workout-landscape/normal-workout-correspondence.json) retains exact times, application/scene state and renderer placement.

The initial 65-record trace prefix is preserved alongside the complete 155-record copy ending at sampler completion. This normal run includes AX observation and the visible Skip action; it is not a touch-free control. A later passive experiment is outside this frozen appendix. These findings show the isolated caption and wrapper changes did not reproduce the real-workout context; they identify no specific root cause.

## Preserved build failure and limits

The first [caption build](raw/caption-build-command.json) failed on actor-isolation calls in a read-only nested UIKit census identity helper. Its stdout/stderr remain exact. The [narrow compile correction](raw/caption-boardmap-applied/compile-correction.json) uses the same direct ObjectIdentifier string conversion; [the second build](raw/caption-build-2-command.json) succeeded. This diagnostic compile repair is not a highlight-behavior fix.

One bounded run per isolated arm and one interactive normal comparison were performed. Sparse Surface observers and UIKit census were present identically across isolated arms; observer callback time is distinct from actual material mutation. Initial clear was already established before readiness. Whole-image judgments apply to these Simulator captures, not physical-device rendering. [The Astra context review](analysis/architecture-committee/astra-context-discriminator-review.txt) is retained analysis, not an implemented recommendation.

## Provenance and ownership

[retention-manifest.json](retention-manifest.json) maps each scratch source to exact retained bytes and SHA-256. Absolute paths in raw records are preserved historical provenance. [The three-file diagnostic snapshot](frozen-source/snapshot.json) and [diff](frozen-source/current-three-file-diff.patch) were frozen against `8455851926c5d8c66e90d0668cac40a3079e3228` before later work. All previous packets were verified unchanged.

No canonical CAD, queue/lock, source, index, commit, device or acceptance change was performed by packaging. The exact registered Simulator and DerivedData/result paths remain live under the existing owner controller, with cleanup pending; the ownership record is a snapshot, not deletion proof. Further experiments and cleanup belong in separate evidence.
