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

`kind` is complete: all 690 current hold records have one of the schema's five
classes. A missing `fingerCapacity` on an edge, jug, pinch, or sloper is not a
gap: capacity is meaningful only for a source-labelled finger pocket. Likewise,
`sizeMillimeters` is only used for a source-mapped single depth; a continuous
surface with several published depths uses `depthRangeMillimeters` when the
source establishes its endpoints.

### Discrete-contact correction

Re-reviewed 2026-08-25 under the catalog rule that manufacturer-labelled
discrete shelves are individual scalar-depth holds, while a continuously
variable rail remains one range-backed hold. This supersedes the earlier
interpretation that a shared surrounding recess made all of its visibly
stepped shelves one logical contact. The decisive evidence is not the mere
presence of several numbers on a product page: the official labelled views
map each number to a separate planar shelf divided by a visible vertical depth
transition. The right-side paths are exact mirrors only where those same
manufacturer views establish bilateral symmetry.

| Package | Retired range-backed IDs | Source-confirmed scalar replacements | Physical-contact evidence | Resulting inventory |
| --- | --- | --- | --- | --- |
| `tension-grindstone` | `edge-10-8-{left,right}`, `edge-30-25-{left,right}`, `edge-20-15-{left,right}` | `edge-{8,10}-{left,right}`, `edge-{25,30}-{left,right}`, `edge-{15,20}-{left,right}` | The [product page](https://tensionclimbing.com/products/grindstone) enumerates all six edge depths, and the [official labelled close view](https://tensionclimbing.com/cdn/shop/files/Grindstone2.png?v=1726542525) places 10/8, 30/25, and 20/15 on separate planar steps on the source side. | 14 logical holds; all 13 measured edges use `sizeMillimeters`; no depth ranges remain. |
| `tension-honestone` | `edge-20-15-{left,right}`, `edge-10-8-{left,right}` | `edge-{15,20}-{left,right}`, `edge-{8,10}-{left,right}` | The [product page](https://tensionclimbing.com/products/honestone) lists the four edge depths, and the [official labelled close view](https://tensionclimbing.com/cdn/shop/files/Honestone2.png?v=1726542571) maps each value to its own step. The 35°/45° macro sloper remains one unmeasured contact because Tension expressly describes continuously variable curvature. | 12 logical holds; all 11 pockets/edges use scalar depth; no depth ranges remain. |
| `tension-whetstone` | `edge-40-30-{left,right}`, `edge-25-20-{left,right}` | `edge-{30,40}-{left,right}`, `edge-{20,25}-{left,right}` | The [product page](https://tensionclimbing.com/products/whetstone) lists the four edge depths, and the [official labelled close view](https://tensionclimbing.com/cdn/shop/files/Whetstone2.png?v=1726542637) maps 40/30 and 25/20 to distinct planar steps. | 12 logical holds; all 11 pockets/edges use scalar depth; no depth ranges remain. |
| `frictitious.megalith` | `stepped-8-10-12-{left,right}`, `stepped-30-40-pocket-{left,right}`, `stepped-15-20-{left,right}` plus the overlapping unnamed `hold-11`…`hold-14` records | `edge-{8,10,12}-{left,right}`, `edge-30-{left,right}`, `edge-40-pocket-{left,right}`, `edge-{15,20}-{left,right}` | The [product page](https://frictitiousclimbing.com/products/megalith) enumerates seven shoulder-width edge sizes and identifies the two-finger pocket on the 40 mm edge. The [official labelled front](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front.jpg?v=1780436232&width=3840) and [official oblique detail](https://frictitiousclimbing.com/cdn/shop/files/Mega-4.jpg?v=1764914587&width=3840) map every value to a visibly separate planar shelf. The integrated pocket stays part of its 40 mm edge contact; no independent depth or capacity was invented. | 18 logical holds: 14 shoulder-width scalar edges, one 25 mm centre edge, one jug, and two mono pockets. No depth ranges or unnamed duplicate holds remain. |

Every replacement contact has a newly reviewed, closed canonical path authored
through Workbench. Adjacent steps share only their physical transition line;
none of the old full-recess paths or nested Megalith duplicates remains to
overlap selectable contacts.

### Retained continuous ranges and ruled-out splits

| Package / IDs | Retained range | Why it is not a discrete-step candidate |
| --- | --- | --- |
| `trango.rock-prodigy-forge` / `variable-edge-rail-{left,right}` | 7–20 mm | Trango's [Forge depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887) maps the endpoints to one continuously sloped rail. There are no source-mapped shelf boundaries to split. |
| `trango.rock-prodigy-pivot` / `variable-edge-{left,right}` | 16–31 mm | Trango's [Pivot depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905) maps a continuous depth interval to the same physical rail. Its endpoints remain a range, not two invented holds. |

Other Pivot dimensional ranges describe existing single sculpted contacts and
were not discrete stepped candidates in this migration. No package outside the
four source-mapped stepped boards was split.

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
retained. Apart from the discrete-contact correction and fractional mappings
above, no `kind`, `fingerCapacity`, or scalar `sizeMillimeters` change was
justified by the additional evidence.
