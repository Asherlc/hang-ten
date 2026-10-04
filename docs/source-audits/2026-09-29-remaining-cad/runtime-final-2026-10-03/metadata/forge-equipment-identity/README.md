# Forge physical-equipment identity restoration

This event corrects the earlier audit conclusion that Forge's equipment-object difference was harmless because its two halves are baked into one asset. **That conclusion was insufficient.** Physical equipment identity is independent of rendering-instance topology. The accepted paired native export can and must retain distinct `left-half` and `right-half` equipment objects without `media.instances`, runtime clones or any shape change.

The observed pre-correction regression, `WorkoutActivityRecordingTests.testRockProdigyReusableFramesResolveToDistinctPhysicalSides`, failed because Forge resolved the pair to `[primary]` instead of `[left-half, right-half]`. The [exact failure excerpt](pre-correction-equipment-identity-failure.txt) is retained. This is a real functional metadata omission, not a reason to weaken the test or split/rebuild the approved asset.

## Exact correction

Root restored only `equipmentObjects` and all 20 contacts' `equipmentObjectID` from incoming main `d53c019c43319a70b32e6dc654814de29e87ab89`. Baseline and initial native metadata had one `primary` equipment object; main and the corrected native metadata have `left-half` and `right-half`. The exact before/after documents are [before-manifest.json](before-manifest.json) and [updated-manifest.json](updated-manifest.json).

For each stem below, its `-left` contact now belongs to `left-half`, and its `-right` contact to `right-half`: `sloper-30`, `sloper-40`, `large-flat-edge`, `slopey-crimper`, `variable-edge-rail`, `closed-crimp`, `mr-deep`, `mr-shallow`, `im-deep`, `im-shallow`. No contact ID, name, kind, capacity, depth, path, pose, display finish, presentation or routine changed. No runtime instance was added.

The earlier upstream object split is traceable to `e85a42ee38073a2c4cb19f842ef02f88cdd52e11` and the frozen [main snapshot](../initial-audit/snapshots/trango-rock-prodigy-forge/main.json). This restores already-merged metadata for the manufacturer's two physical units; it introduces no new manufacturer fact or routine prescription.

## Geometry and approval preservation

- Historical human-approved source: `4f970f46263bbf8e3cc4a1995fe48f4c3c6f638f65b816c9fb0a95a65843dc4e`.
- Current metadata source: `91e9116bf072c355198211c0c3bad12da4b13ad2c5dfa98339a6ce0ba2fbf124`.
- Model: `6af1091171a5251914983b6d9c17859eb7e85fe35e15628d5c3c164fe2b8ba61` (unchanged).
- Descriptor: `ec716c7eddbfeeae7ca4881b146dd824138af137299ed23c10b5706076b989e6` (unchanged).

The [exact root preservation proof](metadata-preservation.json) and [independent read-only recheck](independent-preservation-recheck.json) confirm 128 byte-identical BRep entries and all archive members except `Document.xml` unchanged. The recheck confirms current authored manifest equals the retained after-manifest; only the equipment-object list and 20 equipment references changed, and those exactly match incoming main. The proof field `contactIDsFactsAndPathsChanged: false` denotes unchanged contact inventory, hold facts and paths; equipment-object references are the explicitly listed changed fields.

The accepted shape, native mirror, paired placement and existing review limitations remain intact. The historical [human-review record](../../../trango-rock-prodigy-forge/human-review.json) is unchanged. Queue #15 records the new current source separately from its historical accepted geometry source; no new visual approval or completed app-review status is asserted.

## Revised audit conclusion and timing

The initial [audit summary](../initial-audit/audit.md), [structured report](../initial-audit/audit-report.json), all raw snapshots and their hashes remain frozen exactly as read before either correction. In particular, their statements that no additional direct correction was needed and that Forge's `primary` identity should remain are **superseded by this appended conclusion**, not silently rewritten. The observed raw three-way values were correct; their disposition was not.

Current integration conclusion: the Simulator shared round-sloper capacity restoration and this Forge physical-equipment identity restoration are both required. The earlier deliberate Port-A-Board/Poker/Plateau decisions are not revised by this event.

Focused runtime validation after this Forge restoration is pending root's rerun at this documentation handoff. The retained failure predates the correction. No passing post-correction runtime, workout, app-review or whole-suite claim is made here; root owns the forthcoming final runtime report.
