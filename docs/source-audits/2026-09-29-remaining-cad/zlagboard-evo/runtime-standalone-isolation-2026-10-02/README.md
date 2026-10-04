# Evo standalone isolation diagnostics — 2026-10-02

All **80 board-state/color captures passed in isolation** across A1/B1/B2/A2. The earlier actual-workout defect remains unresolved. This is no production repair, renderer rewrite, new implementation or human acceptance.

The standalone route mounts one BoardModelSurface before normal tabs/navigation/workout/hand construction. It reuses the existing loader, model, camera and synchronization at the exact **210 × 36 point** GeometryReader viewport measured from the real workout, not from pixels. The sequence is clear → active → preview → active → preview, with four whole-screen captures per phase. A omits SceneEvents.Update subscription; B adds an in-memory update counter. That counter is not a display/presentation counter or a fix.

[The frozen A/B/B/A report](raw/standalone-abba-findings.json) and [measured viewport](raw/standalone-workout-viewport.json) retain exact identity, timing and CPU brackets. Root reviews are retained for [A1](raw/standalone-a1/root-visual-review.json), [B1](raw/standalone-b1/root-byte-equivalence-review.json), [B2](raw/standalone-b2/root-visual-review.json) and [A2](raw/standalone-a2/root-byte-equivalence-review.json). Root individually opened representative whole images and verified exact hashes for matching repeated captures. No image-derived geometry was used. The metadata-only viewport-preflight directory is separate from these four visual runs.

## Preserved limitations

- A1's original [validity.json](raw/standalone-a1/validity.json) failed because it included pre-readiness startup. The separate [measurement-window correction](raw/standalone-a1/validity-measurement-window.json) scopes checks to the scheduled interval after application/window/viewport readiness. The original failed check remains unchanged.
- B2 has a one-frame black rounded capsule at the screen edge in [phase 3, +1 second](raw/standalone-b2/phase-3-active-plus-1.png), SHA-256 `0386801cc5121b39da6676a55e868424cc3c93a9fcb8dbf78d561cc12a97b685`. The board is correctly red. The artifact's origin is unproven; full-frame byte identity is not claimed for every capture. Root's review preserves the earlier overly strict hash-equivalence helper failure.
- One build and one bounded A/B/B/A series ran on the owned Simulator. Isolation removes several context variables together; success identifies no specific removed hierarchy or scheduling cause. CPU records and event counts alone do not prove display correctness.

## Analysis, provenance and resource status

[Committee consensus](analysis/architecture-committee/consensus.md), raw responses and launch metadata are retained byte-for-byte as analysis. Early recommendations may be superseded by later OFF corrections and isolation results; they are not selected implementation plans or proof of an SDK defect. The historical full OFF-pass inference remains withdrawn in the [projection correction](../runtime-projection-correction-2026-10-02/README.md).

[retention-manifest.json](retention-manifest.json) maps original scratch files to exact retained paths/hashes. Absolute paths embedded in raw files remain provenance. Build/install/parity outputs, proposals/applied source, harness, complete logs, images and root reviews remain unchanged. [The three-file source snapshot](frozen-source/snapshot.json) and [diff](frozen-source/current-three-file-diff.patch) preserve temporary diagnostics against `3b6c03c9b8e60b1c1af4fcd9a0e75946e0117765`.

Previous packets, CAD packages, review queue/lock and human acceptance are unchanged. The registered Simulator and DerivedData/result paths remain live under the existing owner controller, pending cleanup. The retained ownership record is a historical snapshot, not deletion proof. Packaging performed no source, index, commit or device operation. Later validation and cleanup belong in separate evidence.
