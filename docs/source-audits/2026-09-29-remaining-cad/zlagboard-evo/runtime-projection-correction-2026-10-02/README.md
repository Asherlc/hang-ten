# Evo projection diagnostics and OFF correction — 2026-10-02

All three completed full workout sequences **failed**. The proposed orthographic/perspective/OFF/OFF/perspective/orthographic sequence stopped after its first three runs at root's instruction; the remaining three were not run. No renderer repair or SDK root cause is established.

| Diagnostic second host | First active | Settled rest | Next active | Workflow |
| --- | --- | --- | --- | --- |
| Plain PBR box, orthographic | Red | Blue | Blue (incorrect) | Failed |
| Plain PBR box, perspective | Red | Blue | Blue (incorrect) | Failed |
| Visible second host OFF | Red | Red (incorrect) | Blue (incorrect) | Failed |

The [frozen discriminator report](raw/projection-discriminator-findings.json) retains complete JSONL traces, capture intervals, scene/camera identities, CPU material samples, screenshot hashes and the explicit stop reason. Each run's whole images, AX records, raw command outputs and environment are preserved under `raw/projection-*-a-landscape/`. Build/install command logs, all-Mach-O parity, package parity, proposals and exact applied patches are retained byte-for-byte. These diagnostic images are not new geometry acceptance or proof of a production fix.

## Correction to the earlier OFF inference

The previous [diagnostic appendix](../runtime-diagnostics-2026-10-02/README.md) and its committed raw records remain unchanged as history. Its assertion that the hand-OFF run passed the full workflow is withdrawn. The historical [settled-rest image](historical-off-critical-images/following-rest-settled.png) shows **red pockets at Rest 02:56**, when blue was expected. Its exact SHA-256 is `4540ff67ccf2fbe2ee689fc7826c0226a0243ea0170d192d37bd0a30e6b2f9d2`. The historical [next-active image](historical-off-critical-images/next-active-timed-2.png) correctly shows red, but that single successful phase was insufficient to claim a full-sequence pass.

The [worker correction](raw/hand-host-rest-correction-appendix.json) and [root's independent correction](raw/root-hand-off-full-sequence-correction.json) explicitly retain that distinction. Visible hand-host suppression did not fix the full sequence. The prior claimed FAIL/PASS/FAIL causal inference and any architecture conclusion based on a full OFF pass are withdrawn. This observation does not census every hidden retained host and does not establish the rendering failure's cause.

## Provenance and scope

[retention-manifest.json](retention-manifest.json) maps every source scratch path to the byte-exact retained path and hash. Absolute scratch paths embedded in old JSON remain provenance and are not rewritten. [The three-file source snapshot](frozen-source/snapshot.json) and [current diff](frozen-source/current-three-file-diff.patch) preserve the exact temporary diagnostics against `10c7a6eb980e7e1c9a3ef0119c82a42e5159e83a`; this documentation package does not ship those changes as a production repair.

Canonical CAD packages, global queue/lock and existing human acceptance records are unchanged. The exact owned Simulator and build paths remain live under the existing controller for continued diagnosis; `resource-provenance/ownership-at-snapshot.json` is historical ownership, not cleanup proof. No resource operation was performed during this promotion. Previous failed packets and all earlier raw interpretations remain byte-for-byte intact, with this appendix providing the current correction.
