# Merged-main metadata restoration — Simulator 3-D

This packet documents a metadata-only integration correction for review #8, `metolius.simulator-3d`. The existing contact `round-sloper-3-center` now retains `handCapacity: 2` from merged main PR #516. No new manufacturer fact, routine, contact, geometry, or source interpretation was authored.

## Why the correction was necessary

The native migration preserved the older manifest while PR #516 independently added capacity metadata. Incoming main `d53c019c43319a70b32e6dc654814de29e87ab89` includes merge `781e64636eafb382f6ad49cbdf276be354117310`. For this exact field the three-way comparison is:

| Version | `round-sloper-3-center.handCapacity` |
| --- | --- |
| Baseline `d0e4e95191e4a76822815bb4eeef3a32caa6fea0` | absent |
| Incoming main `d53c019c43319a70b32e6dc654814de29e87ab89` | 2 |
| Initial current native/generated/built snapshots | absent |
| Corrected native manifest | 2 |

The pre-correction library validation reported four existing paired round-sloper task mismatches:

| Existing step ID | Task index | Validation path |
| --- | --- | --- |
| `metolius.simulator-3d.entry.minute-8` | 0 | `plans[6].blocks[1].steps[6].segments[0].target.tasks[0]` |
| `metolius.simulator-3d.intermediate.minute-4` | 1 | `plans[7].blocks[1].steps[2].segments[0].target.tasks[1]` |
| `metolius.simulator-3d.intermediate.minute-10` | 1 | `plans[7].blocks[1].steps[8].segments[0].target.tasks[1]` |
| `metolius.simulator-3d.advanced.minute-10` | 1 | `plans[8].blocks[1].steps[8].segments[0].target.tasks[1]` |

Each already contains two hand targets with `kind: sloper` and `shape: round`. The missing shared-contact capacity prevented those pairs from resolving together. [Exact existing task metadata](existing-task-mismatches.json) retains the packaged plan IDs, block IDs, tasks, PlanLibrary hash and existing manufacturer training-guide attribution. [Pre-correction failure excerpt](pre-correction-library-failure.txt) and [log provenance](pre-correction-log-provenance.json) retain the observed failure. The routine instructions, task order, prescriptions and source mappings were not edited.

## Preservation and review identity

- Historical human-reviewed source: `b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef`.
- Current metadata-corrected source: `ac957ebf25e5134ab2875e9b06d9c23831f35b0b8bcbc64730d6a626b7f8588e`.
- Model remains `f06a5350e07862d1619556d1c81aefe5bf83c64f5688394d2763355c459f637b`.
- Descriptor remains `147f8c18768831c7bc4e04c161c491cbfa7c95c37f99d6ca1ba7a527b9736ffb`.

The [exact preservation proof](metadata-preservation.json) records that only `Document.xml` changed in the native archive; all 509 BRep entries and all other archive members are byte-identical. The independently read corrected embedded manifest equals the frozen initial manifest with only the capacity field added. No geometry, surface membership, display finish, model or descriptor changed. The accepted geometry therefore remains the geometry reviewed on 2026-10-01; this event does not constitute a new visual approval.

The historical [human-review record](../../metolius-simulator-3d/human-review.json), including its shown source hash and “lgtm” answer, remains unchanged. Queue row #8 records the new current source identity separately from the historical accepted geometry source. Other queue rows and all existing app-review statuses remain unchanged.

## All-15 integration audit and snapshot timing

[Audit summary](initial-audit/audit.md), [structured report](initial-audit/audit-report.json), [exact field comparison](initial-audit/three-way-facts.json) and [snapshot inventory](initial-audit/artifact-sha256.json) retain the initial read-only audit of review rows #1–15. The exact original snapshots are under [initial-audit/snapshots](initial-audit/snapshots). No native archive or BRep copies are included.

Every `snapshots/*/current-*.json`, the root `*-current.json`, the original protected-file baseline and review-identity comparison are **pre-correction** observations. They intentionally continue to show the omitted Simulator capacity. The separate `post-correction-simulator-embedded.json` and correction note document the later restoration; the original observations were not rewritten. Original audit files are archived byte-for-byte, so their historical `.context` locations remain in provenance strings. Those strings refer to the original workspace observations; the complete compact JSON audit is now retained here.

The audit found no additional direct factual correction. Metolius Contact's three upstream capacity additions were already integrated. Forge's equipment-object split remains a separate accepted combined-native-asset representation, and Port-A-Board/Poker/Plateau deliberate local differences are documented separately in the audit. No other board's current review status is changed by this packet.

## Validation boundary

This packet retains the observed **pre-correction** validation failure and the source/archive/manifest preservation checks. Focused post-correction runtime tests have not yet run at this documentation handoff. No passing app-validation, interaction, physics or full-suite result is claimed. Root owns subsequent runtime validation and the overall report.

[Simulator source audit appendix](../../metolius-simulator-3d/source-audit.md#2026-10-03--merged-main-capacity-metadata-restoration) links this integration event to the retained geometry history. [Documentation change proof](documentation-change-proof.json) records the narrow queue update, unchanged historical review record and protected asset/plan identities.


## 2026-10-03 appended correction — Forge physical equipment identities

The earlier conclusion above and in the frozen initial audit that Forge's single `primary` equipment identity was an acceptable consequence of a combined native asset was insufficient. The actual workout regression `testRockProdigyReusableFramesResolveToDistinctPhysicalSides` requires the two physical units to remain distinct. A single baked paired model does not remove those equipment identities or require runtime clones.

Root restored the two merged-main `left-half` / `right-half` equipment objects and the corresponding 20 contact references, with no other manifest or geometry changes. The [Forge correction packet](forge-equipment-identity/README.md) retains the exact failure, before/after manifests, source/model/descriptor identities, independent 128-BRep/archive preservation check and explicitly revised audit conclusion. Initial raw snapshots and reports remain immutable; their prior no-further-correction and keep-Forge-primary dispositions are superseded by this addendum.

The current integration conclusion requires both the Simulator capacity restoration and the Forge physical-equipment identity restoration. The accepted #15 shape and historical human-review answer remain intact. Focused runtime validation after the Forge correction is pending root's rerun; no passing post-correction claim is added here. The earlier Simulator pending-test statement records its original handoff time; subsequent verified runtime results belong to root's forthcoming overall report.
