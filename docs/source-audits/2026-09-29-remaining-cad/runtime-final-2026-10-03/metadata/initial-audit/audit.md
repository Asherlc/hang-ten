# Boards 1–15 factual metadata integration audit

The only missed direct upstream fact was `metolius.simulator-3d` contact `round-sloper-3-center.handCapacity = 2`. Root has now restored it. No additional direct factual correction is needed.

Comparison: baseline `d0e4e95191e4a76822815bb4eeef3a32caa6fea0`, incoming main `d53c019c43319a70b32e6dc654814de29e87ab89`, initial task HEAD `f9554600c`. Scope is exactly review-queue rows 1–15. Contact fields are matched by exact ID; board-level handCapacity is checked separately. No package from rows 16–21 was inspected.

## Frozen initial observations

All `snapshots/*/current-*.json`, the initial root Simulator `*-current.json`, `three-way-facts.json`, `protected-file-baseline.json`, and `review-identity-comparison.json` describe the initial **pre-correction** read. They have not been rewritten to imply the later correction was already present.

| Package / exact contact ID | Field | Baseline | Main | Initial native/generated/built | Disposition |
| --- | --- | --- | --- | --- | --- |
| metolius-contact / `edge-17-center` | handCapacity | absent | 2 | 2 | Already integrated |
| metolius-contact / `edge-18-center` | handCapacity | absent | 2 | 2 | Already integrated |
| metolius-contact / `flat-sloper-center` | handCapacity | absent | 2 | 2 | Already integrated |
| metolius-simulator-3d / `round-sloper-3-center` | handCapacity | absent | 2 | absent | Root corrected after snapshot |

These four additions are the exact scoped PR #516 merge changes (`781e64636eafb382f6ad49cbdf276be354117310`); retained patch: `upstream-516-contact-capacity.diff`. All 15 embedded/generated/built factual maps agreed at the initial read. No upstream contact ID inventory/order changes and no board-level handCapacity changes were found.

## Separate structural divergence

Forge retains `primary` for every contact in the accepted combined native asset. Main instead changes equipmentObjectID to `left-half` / `right-half` for each corresponding `-left` / `-right` ID below. This is a structural representation difference, not another lost capacity/depth fact. Root explicitly confirmed preserving the accepted combined asset.

`closed-crimp`, `im-deep`, `im-shallow`, `large-flat-edge`, `mr-deep`, `mr-shallow`, `sloper-30`, `sloper-40`, `slopey-crimper`, `variable-edge-rail` (both `-left` and `-right` for each: all 20 exact IDs and three-way values are in `audit-report.json`).

Upstream provenance: `e85a42ee38073a2c4cb19f842ef02f88cdd52e11`. Local paired-source decision: `docs/source-audits/2026-09-29-remaining-cad/trango-rock-prodigy-forge/source-audit.md:31–33`.

## Local deliberate differences, not upstream omissions

- Port-A-Board removes `pocket-30-two-finger-mono`; baseline and main both retain this duplicate label for the same 30 mm cavity. Current keeps `edge-30` and the eight other actual contacts. Decision: `docs/source-audits/2026-09-29-remaining-cad/frictitious-port-a-board/native-authoring.md:7`.
- Owl Poker omits the old 100 mm depth values on `face-c-left-shallow-half-round` and `face-c-right-shallow-half-round`; baseline and main agree on those old values. The current source distinguishes display estimates from published per-contact depth facts. Decision: `docs/source-audits/2026-09-29-remaining-cad/owl-climb-poker/review12-2026-10-02/review.md:13`.
- Plateau removes `blocker-edge-10` / `blocker-edge-15` as independent contacts and names `edge-18` “Wood edge” instead of “18 mm wood edge”. Baseline and main agree on the old inventory. Current represents one physical edge with configuration-specific effective depths 18/15/10 mm. Decision: `docs/source-audits/2026-09-29-remaining-cad/plateau-lifting-edge/native-authoring.md:7` and `review13-2026-10-02/review.md:7,17`.

## Geometry identity and subsequent correction

Every reviewed model and descriptor hash matched the review queue at the initial read. Initial source hashes differed for rows 1, 2, 3, 4, 5 and 7; these distinguish native metadata updates from the retained geometry approval identities. This read-only metadata audit does not independently claim BRep equality for those earlier finish updates.

Root subsequently corrected only the Simulator manifest field. Its source changed from `b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef` to `ac957ebf25e5134ab2875e9b06d9c23831f35b0b8bcbc64730d6a626b7f8588e`. An independent pure manifest read confirmed that the new embedded JSON equals the frozen initial manifest with only `round-sloper-3-center.handCapacity = 2` added. The new read is retained separately as `post-correction-simulator-embedded.json`; no claim is made here about a rebuilt post-correction app JSON.

Root preservation proof: `.context/placid-badger/runtime-final-2026-10-03/main-metadata-correction/metadata-preservation.json` (SHA-256 `b83f997ac89ba3e741a21ca758b8f1152cdc10f5090ab40283e88aaffbacb1d1`). It records 509 byte-identical BRep entries, all archive members except Document.xml identical, and unchanged model/descriptor. The final protected-file comparison found only that source change; every other protected source/model/descriptor/sidecar remained unchanged.

No canonical writes were performed by this audit agent. No FreeCAD process, build, Simulator, server, or external resource was started; no resource cleanup remained. Full structured results: `audit-report.json`; exact field diffs and original snapshots: `three-way-facts.json` and `snapshots/`.
