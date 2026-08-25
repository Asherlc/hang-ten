# Hold metadata completeness appendendum

**Reviewed:** 2026-08-25  
**Scope:** all 44 discoverable `Hangboards/*/board.json` packages, extending
the [all-board hold audit](2026-08-25-all-board-hold-audit.md).

This pass used the existing stable-ID overlays in
`.context/audit-board-hold-id-overlays/` to cross-reference individual JSON
contacts with the physical contact named by each manufacturer. It is a metadata
audit only: no measurement, finger count, or hold kind was inferred from a
render or photograph.

## Result

`kind` is complete: all 672 current hold records have one of the schema's five
classes. A missing `fingerCapacity` on an edge, jug, pinch, or sloper is not a
gap: capacity is meaningful only for a source-labelled finger pocket. Likewise,
`sizeMillimeters` is only used for a source-mapped single depth; a continuous
surface with several published depths uses `depthRangeMillimeters` when the
source establishes its endpoints.

### Tension and So iLL ledger certification

The Tension/So iLL batch re-opened the seven current manufacturer product
pages and manually reviewed all 69 stable IDs in
`.context/hangboard-metadata-backfill-icky-cow/tension-soill/`. `icky-cow` is
the workspace-owned fallback because `CONDUCTOR_WORKSPACE_NAME` was unset.
Flash Board has separate labelled captures for its three-edge and two-edge
presentations. No capture was used to create, adjust, or classify geometry.

The machine-readable ledger now covers 17 boards and 239 holds, up from 10
boards and 170 holds. Every reviewed hold has seven accounted fields and a
verified manufacturer-backed `kind`:

| Field | Before populated / verified | After populated / verified | After unavailable | After not applicable |
| --- | ---: | ---: | ---: | ---: |
| `kind` | 170 / 170 | 239 / 239 | 0 | 0 |
| `sizeMillimeters` | 133 / 133 | 151 / 151 | 88 | 0 |
| `depthRangeMillimeters` | 0 / 0 | 14 / 14 | 225 | 0 |
| `fingerCapacity` | 87 / 87 | 91 / 91 | 2 | 146 |
| `handCapacity` | 0 / 0 | 0 / 0 | 239 | 0 |
| `gripType` | 87 / 87 | 89 / 89 | 150 | 0 |
| `features` | 0 / 0 | 0 / 0 | 239 | 0 |

The 107 additional populated/verified fields are 69 mandatory kinds, 18
scalar depths, 14 continuous-contact ranges, four finger capacities, and two
two-finger-pocket grip enums. These values were already source-mapped in the
seven package files, so the certification changes the ledger and audit trail
without rewriting any `board.json`. The complete manufacturer-label to stable
ID map and the source-term type audit are in the
[So iLL/Tension audit](2026-08-12-soill-tension-board-packages.md#2026-08-25-source-audited-metadata-batch).

Remaining batch blanks are deliberate: Flash Board depths are a global,
unpositioned list; Training Tiles measurements are grouped without numbered
left/right mappings and its pockets have no published finger count; Honestone
has source-labelled one-finger pockets but the schema has no corresponding
grip enum; width, angle, curvature, and radius are not contact depth; and no
reviewed source publishes simultaneous hand capacity or an exact package
feature-tag array.

### Corrected source mappings

The following are newly recorded structured mappings in this appendendum. The
current product-page retrieval is **new evidence review**; the URLs and the
official front-image mapping were already catalogued in the earlier source
audits noted in the last column. No source fact was transferred between models.

| Package | Hold IDs | Added field | Evidence retrieved in this pass | Prior audit record |
| --- | --- | --- | --- | --- |
| `tension-grindstone` | `edge-10-8-{left,right}` | 8–10 mm range | [Tension Grindstone](https://tensionclimbing.com/collections/bestsellers/products/grindstone) lists both 8 and 10 mm edges. | [So iLL/Tension audit](2026-08-12-soill-tension-board-packages.md#tension-grindstone) maps the visibly continuous paired stepped recesses. |
| `tension-grindstone` | `edge-20-15-{left,right}` | 15–20 mm range | [Tension Grindstone](https://tensionclimbing.com/collections/bestsellers/products/grindstone) lists both 15 and 20 mm edges. | Same prior mapping. |
| `tension-grindstone` | `edge-30-25-{left,right}` | 25–30 mm range | [Tension Grindstone](https://tensionclimbing.com/collections/bestsellers/products/grindstone) lists both 25 and 30 mm edges. | Same prior mapping. |
| `tension-honestone` | `edge-10-8-{left,right}` | 8–10 mm range | [Tension Honestone](https://tensionclimbing.com/products/honestone) lists 8 and 10 mm edges. | [So iLL/Tension audit](2026-08-12-soill-tension-board-packages.md#tension-honestone) maps the continuous paired recesses. |
| `tension-honestone` | `edge-20-15-{left,right}` | 15–20 mm range | [Tension Honestone](https://tensionclimbing.com/products/honestone) lists 15 and 20 mm edges. | Same prior mapping. |
| `tension-whetstone` | `edge-25-20-{left,right}` | 20–25 mm range | [Tension Whetstone](https://tensionclimbing.com/products/whetstone) lists 20 and 25 mm edges. | [So iLL/Tension audit](2026-08-12-soill-tension-board-packages.md#tension-whetstone) maps the continuous paired recesses. |
| `tension-whetstone` | `edge-40-30-{left,right}` | 30–40 mm range | [Tension Whetstone](https://tensionclimbing.com/products/whetstone) lists 30 and 40 mm edges. | Same prior mapping. |
| `frictitious.megalith` | `stepped-8-10-12-{left,right}` | 8–12 mm range | [Frictitious Megalith](https://frictitiousclimbing.com/products/megalith) enumerates 8, 10, and 12 mm shoulder-width edges. | [Evolv/Frictitious audit](2026-08-12-evolv-frictitious-board-packages.md#frictitious-megalith) maps the continuous top contacts. |
| `frictitious.megalith` | `stepped-15-20-{left,right}` | 15–20 mm range | [Frictitious Megalith](https://frictitiousclimbing.com/products/megalith) enumerates 15 and 20 mm shoulder-width edges. | Same prior mapping. |
| `frictitious.megalith` | `stepped-30-40-pocket-{left,right}` | 30–40 mm range | [Frictitious Megalith](https://frictitiousclimbing.com/products/megalith) enumerates 30 and 40 mm shoulder-width edges and says the 40 mm edge contains the two-finger pocket. | Same prior mapping; its continuous contact remains `edge`, without a fabricated fixed pocket capacity. |

The correction is 20 hold fields: six on Grindstone, four on Honestone, four
on Whetstone, and six on Megalith. `depthRangeMillimeters` records the bounds
of a continuous physical surface; it does not assert that every point between
the two published shelf depths is a separately calibrated hold.

### Fractional value recovery

The package schema now accepts positive finite JSON numeric scalar and range
values, retaining their `Double` precision through the app loader, editable
document, writer, training model, and activity record. This releases the
following primary-source mappings that were previously documented but could not
be represented without rounding.

| Package | Hold IDs | Exact `sizeMillimeters` | Evidence and mapping |
| --- | --- | --- | --- |
| `metolius.climbers-edge` | `edge-17-5-{left,right}`, `edge-12-5-{left,right}`, `edge-7-5-center` | 17.5, 12.5, 7.5 mm | [Metolius audit](2026-08-12-metolius-board-packages.md#climbers-edge--15-contacts) maps the manufacturer’s lower-row depths to these five contacts. |
| `soill.split-palm` | `sloping-rail-38-{left,right}`, `flat-edge-25-{left,right}`, `outer-crimp-12-{left,right}`, `bottom-sloping-crimp-12-{left,right}` | 38.1, 25.4, 12.7, 12.7 mm | [So iLL/Tension audit](2026-08-12-soill-tension-board-packages.md#soill-split-palm) gives the seven per-piece contacts and their exact metric depths. |
| `trango.rock-prodigy-forge` | `closed-crimp-{left,right}` | 7.5 mm | [Trango audit](2026-08-12-trango-board-packages.md) maps the manufacturer’s 7.5 mm closed crimp to the mirrored pair. |

This resolves 15 formerly unrepresentable hold fields. The primary sources do
not establish additional fractional per-contact depths among the remaining
blank fields.

## Remaining unsupported metadata

The audit did not leave values blank merely because they were difficult to
read. Each group below was checked against the indicated primary materials and
remains blank for a specific evidence reason.

| Packages / contacts | Fields deliberately left blank | Reason and source status |
| --- | --- | --- |
| `beastmaker-1000` pockets; `beastmaker-2000` unmapped pockets and edges; `dewoodstok-woodbord` pockets | Per-contact capacity and/or depth | Product pages give product or family facts but no numbered per-contact mapping. The prior catalog audit explicitly prohibits applying aggregate values to a pocket ID. |
| `frictitious.doormount-pro-7` unnamed lower records and mixed contacts | Depth and capacity | [DoorMount Pro](https://frictitiousclimbing.com/products/doormount-pro) lists the 35/25/20/15/10 mm families and pockets, but its declared seven-hold inventory does not map those facts to this package's 13 current logical records. A fresh field assignment would be an inference; the inventory discrepancy needs a separate physical-contact reconciliation. |
| `soill.training-tiles`; `tension.flash-board`; `target10a.linebreaker-base`; `zlagboard.evo`; `zlagboard.pro` | Per-contact depth and, where applicable, pocket capacity | Manufacturers publish grouped size/family information or product views, not an individual ID-to-value guide. The front image establishes physical contact boundaries, not an exact value assignment. |
| `trango.rock-prodigy-forge` IM pockets; `trango.rock-prodigy-natural` centre-lower and supported pockets; `trango.rock-prodigy-training-center` variable rails and pockets | Exact per-contact depth | Forge's official guide gives only an aggregate IMR range. Natural's official product markings and quick-start guide conflict on the affected values/capacities. The Training Center manual names only selected training grips and lacks a depth map for each physical package contact. |
| `nature.stoak-board-iii` gradient/composite contacts; `frictitious.megalith` mono pockets | Exact depth | Manufacturer material identifies the board-level or named edge facts but does not establish individual endpoints/depths for these exact compound/mono contacts. |
| All other blanks on jugs, edges, pinches, and slopers | `fingerCapacity` | The reviewed primary source does not constrain a fixed number of fingers. Capacity was not guessed from a hold's apparent width or use photograph. |

Existing explicit capacities (mono, duo, three-finger, four-finger) and
source-mapped scalar depths elsewhere in the 44 packages were rechecked and
retained. Apart from the fractional mappings above, no `kind`,
`fingerCapacity`, or scalar `sizeMillimeters` change was justified by the
additional evidence.
