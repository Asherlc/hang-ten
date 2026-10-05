# Evo initial-resize diagnostics — 2026-10-02

The corrected isolated E2/F2/G2 runs have **60 visually correct board-state/color captures**, but **G2 has only 19/20 complete CPU brackets**. This is not an unqualified full-evidence pass. The actual workout defect remains unresolved; no production fix or human acceptance is established.

| Attempt | Outcome retained |
| --- | --- |
| First binary E | Visual control passed; one far-left black artifact with correct blue board retained |
| First binary F | Invalid readiness from integer arithmetic; zero scheduled captures, full 8-record trace retained |
| First binary G | Not run |
| Corrected E2 | Visual control correct; three black-capsule frames retained |
| Corrected F2 | Animation-disabled initial resize, all 20 board colors correct; one black-capsule frame retained |
| Corrected G2 | Explicitly animated initial resize, all 20 board colors correct; strict CPU brackets 19/20 |

[The frozen report](raw/resize-efg-findings.json), SHA-256 `b24d18124b5891c5ee1137921ba46772ac605c0ff456e6501401355a1a81e442`, retains both build histories, exact material/image correspondence and limits. Root's whole-image/hash reviews remain in the corresponding raw run directories. Valid sequences show clear/red/blue/red/blue in the isolated context; this does not reproduce the normal-workout stale colors.

## Setup failure and correction

The first F setup computed `410*120/700` with integer arithmetic, producing 70 instead of the authorized measured 70.28571428571429. Readiness failed before the capture schedule, and zero captures are counted for that run. [The arithmetic-correction provenance](raw/resize-arithmetic-correction/) retains the root-authorized explicit floating-literal correction and exact source patch. This restores the original intended size; it is not geometry fitting or a highlight fix. First build/install logs and all invalid-run bytes remain unchanged alongside the second build/install/parity proof.

The tested initial history is **410 × 70.28571428571429 → 210 × 36 points**, including centered-layout consequences. G2 records actual intermediate UIKit widths 352.8560256958008 and 237.8308868408203, supporting sampled interpolation. F2 has no sampled intermediate width; sparse absence does not prove that no animation occurred between observations.

## Evidence limits and artifacts

G2's final preview screenshot ended 0.226 seconds after the last CPU observation. The blue screenshot and preview material observed before/during it are retained, but no after-end CPU snapshot exists. The missing strict bracket remains a qualification; nothing was rerun, discarded or relabeled to conceal it. Whole visual judgments and mechanical bracket completeness are separate.

Root individually inspected the F2/G2 phase finals and the F2 +1-second black-capsule frame. The initial E and corrected E2/F2 capsule artifacts remain full-frame evidence; their cause is not asserted. A single bounded run per valid arm was performed. This isolated resize/animation history differs from real-workout coordinates and surrounding hierarchy, so no universal animation/layout conclusion follows.

## Provenance and ownership

[retention-manifest.json](retention-manifest.json) maps raw source paths to exact retained bytes/hashes. Both builds, installs, code/package parity, capture/check scripts, proposal/applied changes, correction source and all raw failures are retained. [The frozen three-file snapshot](frozen-source/snapshot.json) and [diff](frozen-source/current-three-file-diff.patch) preserve the final temporary diagnostic source against `84ee1aa413096630c524e435cafa6e4d7bc08717`. The original [initial-resize audit](../runtime-passive-workout-2026-10-02/analysis/initial-resize-audit/report.json) is reused through [verified hash-bound links](linked-analysis-provenance.json), avoiding duplicate copies.

Earlier packets, CAD packages, queue/lock and human acceptance records remain unchanged. No source, runtime, index or commit changes were made by packaging. The exact registered Simulator and build/result resources remain live under their existing controller, with cleanup pending; the ownership snapshot is not deletion proof. Subsequent work must be recorded separately.
