# Retained runtime validation evidence — 2026-10-03

The final **focused selection passed 455 tests, failed 0 and retained 1 existing skip** (456 total). This is not a complete-suite or human/app acceptance result. The earlier full attempt timed out and is preserved as unsuccessful.

## Results and chronology

| Retained run | Result | Evidence |
| --- | --- | --- |
| Initial focused regressions | Pre-correction failures retained | [Summary](focused-red-summary.json), [receipt](commands/focused-red.json), [log](commands/focused-red.log) |
| Full attempt, historically named `full-green` | Unsuccessful: owned 1,200-second limit, exit 124; 326 completed tests with 5 recorded failures before later fixes | [Summary](full-attempt-summary.json), [receipt](commands/full-green.json), [full log](commands/full-green.log) |
| Focused run after camera/material fixes, before Forge equipment correction | 454 passed, 1 failed, 1 skipped; Forge physical equipment identity still failed | [Summary](focused-final-summary.json), [receipt](commands/focused-final.json), [log](commands/focused-final.log) |
| Final focused run after both metadata restorations | **455 passed, 0 failed, 1 existing skip** | [Summary](hardware-final-summary.json), [receipt and exact test selection](commands/hardware-final.json), [log](commands/hardware-final.log) |

The existing skipped test is `PlanStorageTests.testBuiltInPlanLibraryVisibleCueFieldsHaveSourceAuditCoverage`. No test is represented as passed merely because it was omitted from the focused selection. The opt-in live-physics determinism run exceeded the full attempt's owned limit; the same retained log also contains the earlier `testLiveScenePausesThenPublishesAcceptedSettledFrame` 30-second timeout and zero frame notifications. There is no subsequent passing live-physics/full-suite claim in this packet. The [owned timeout cleanup receipt](commands/terminate-timed-out-test-host.json) and its [log](commands/terminate-timed-out-test-host.log) are preserved.

Build receipts/logs for the metadata correction, scene correction and final equipment correction remain in `commands/`. The [final build receipt](commands/hardware-corrected-build.json) and [package-validation receipt](commands/hardware-corrected-package-validation.json) retain their commands and outcomes, alongside their logs. Earlier failures were not replaced by the final passing summary.

## Exact tested inputs and preserved geometry

[Scene-fix inputs](scene-fix-inputs.json) bind the reviewed dirty Swift changes and final package hashes. [Final inputs](final-inputs.json) retain the canonical source/model/descriptor identities and metadata-only integration history. [Installed-app provenance](installed-app-provenance.json) records the root-observed matching built/installed app binary and package identities; archiving this record does not imply a new launch or app review.

The only canonical source changes documented here are restored merged-main metadata: Simulator `round-sloper-3-center.handCapacity = 2`, and Forge's two physical equipment IDs with 20 corresponding contact references. The [metadata proof references](metadata-proof-references.json) link the retained preservation checks: 509 Simulator and 128 Forge BRep entries and all non-Document.xml archive members unchanged, unchanged models/descriptors, and no new runtime clones or geometry. The initial audit's mistaken Forge-primary disposition remains historical and is explicitly superseded by the existing [Forge addendum](../metadata/forge-equipment-identity/README.md).

## Scoped review and limitations

The [final code review](shared-contact-failure-audit/final-code-review.md) ([structured identities](shared-contact-failure-audit/final-code-review.json)) approves the requested scope with no blockers. It checks CAD camera-only orbit preserving solved body/cord, retained non-CAD pivots, substantive Forge geometry/hardware tests and authored-material restoration. One nonblocking pitch-only test improvement is recorded. The earlier [scene diagnosis](scene-failure-audit/report.md) and [shared-contact/live-scene diagnosis](shared-contact-failure-audit/audit.md) remain as time-specific evidence, not new conclusions after the final run.

This packet makes **no human acceptance, app appearance, interaction or complete-workflow acceptance claim**. Root owns screenshots, subsequent UI review and queue status updates separately.

## Archive integrity

[Archive provenance](archive-provenance.json) maps each copied source record to its exact archived bytes and SHA-256. [Artifact inventory](artifact-sha256.json) hashes every file in this directory except the inventory itself. All supplied records were copied byte-for-byte. No xcresult/DerivedData, CAD/model binary or mutable app-capture directory is included. The archiver changed only this new documentation directory and started no persistent process, build, Simulator or external resource.
