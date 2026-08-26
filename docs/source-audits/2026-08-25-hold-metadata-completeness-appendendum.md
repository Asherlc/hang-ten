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

`kind` is complete: all 706 current hold records have one of the schema's five
classes. A missing `fingerCapacity` on an edge, jug, pinch, or sloper is not a
gap: capacity is meaningful only for a source-labelled finger pocket. Likewise,
`sizeMillimeters` is only used for a source-mapped single depth; a continuous
surface with several published depths uses `depthRangeMillimeters` when the
source establishes its endpoints.

### Tension and So iLL ledger certification

The Tension/So iLL batch re-opened the seven current manufacturer product
pages and manually reviewed the stable IDs in
`.context/hangboard-metadata-backfill-icky-cow/tension-soill/`. `icky-cow` is
the workspace-owned fallback because `CONDUCTOR_WORKSPACE_NAME` was unset.
Flash Board has separate labelled captures for its three-edge and two-edge
presentations. No capture was used to create, adjust, or classify geometry.

The machine-readable ledger covers every reviewed field with either a verified,
adapted, unavailable, or not-applicable outcome. Training Tiles is the
source-limited exception to a manufacturer contact map: its current listing
supports product identity but no per-contact map, count, dimensions, capacity,
or roles. Its 20 kind values are explicit app adaptations, and all optional
per-contact values remain absent. The complete source-term type audit is in the
[So iLL/Tension audit](2026-08-12-soill-tension-board-packages.md#2026-08-25-source-audited-metadata-batch).

Remaining batch blanks are deliberate: Flash Board depths are a global,
unpositioned list; Training Tiles has no current manufacturer-authored
per-contact map, count, dimensions, capacities, or roles; Honestone has
source-labelled one-finger pockets but the schema has no corresponding grip
enum; width, angle, curvature, and radius are not contact depth; and no
reviewed source publishes simultaneous hand capacity or an exact package
feature-tag array.

### Resolved independent-board ledger certification

The Lattice Triple Rung, The Hangboard, target10a Linebreaker BASE, and Nature
Stoak Board III batch reviewed 49 stable IDs against the current manufacturer
sources and the visible-ID captures listed in the
[scoped source audit](2026-08-12-single-board-documentation-packages.md#2026-08-25-resolved-independent-board-metadata-certification).
The target10a capture contains all 24 corrected stable IDs; the Nature capture
contains seven contacts with one full-width `top-jug`. No capture supplied a
physical value and no geometry changed in this metadata certification.

The ledger moves from 20 boards / 263 holds after the independently committed
Escape/Evolv/DoorMount review to 24 boards / 312 holds. All seven fields are
accounted for and all 49 mandatory `kind` values are manufacturer-backed:

| Field | Before populated / verified | After populated / verified | After unavailable | After not applicable |
| --- | ---: | ---: | ---: | ---: |
| `kind` | 263 / 263 | 312 / 312 | 0 | 0 |
| `sizeMillimeters` | 173 / 173 | 209 / 209 | 103 | 0 |
| `depthRangeMillimeters` | 14 / 14 | 18 / 18 | 294 | 0 |
| `fingerCapacity` | 91 / 91 | 121 / 121 | 4 | 187 |
| `handCapacity` | 0 / 0 | 0 / 0 | 312 | 0 |
| `gripType` | 89 / 89 | 102 / 102 | 210 | 0 |
| `features` | 4 / 4 | 4 / 4 | 308 | 0 |

The 132 batch-populated outcomes are 49 kinds, 36 scalar depths, four exact
continuous-contact depth ranges, 30 exact finger capacities, and 13 exact grip
enums. Every other outcome has a source-specific ledger reason. In particular,
Nature's 55 mm/open-hand callout does not create a second top contact and is not
stored as a scalar or grip value on the single continuous jug; target10a's
finger bars have exact capacities but no corresponding three-/four-finger edge
grip enum; and no source in this batch establishes hand capacity or an exact
feature-tag array.

### YY Vertical and Zlagboard ledger certification

The final manufacturer-family batch manually reconciled 168 stable IDs across
eight YY Vertical packages and two Zlagboard packages with the primary sources
and labelled captures documented in the [YY
audit](2026-08-12-yy-vertical-board-packages.md#2026-08-25-source-audited-metadata-certification)
and [Zlagboard
audit](2026-08-12-zlagboard-board-packages.md#2026-08-25-source-audited-metadata-certification).
The primary-presentation captures are retained under
`.context/hangboard-metadata-backfill-icky-cow/yy-zlagboard/`, while the
collision-free secondary-contact captures and manifest are under
`.context/hangboard-metadata-backfill-icky-cow/yy-zlagboard-secondary/`. Those
14 one-ID images are manually reviewed renderings of the Workbench API's
selected-presentation document and existing canonical paths; no geometry
changed.

The ledger moves from 28 boards / 388 holds to 38 boards / 556 holds. All seven
fields are accounted for and all 168 mandatory kinds are source-verified:

| Field | Before populated / verified | After populated / verified | After unavailable | After not applicable |
| --- | ---: | ---: | ---: | ---: |
| `kind` | 388 / 388 | 556 / 556 | 0 | 0 |
| `sizeMillimeters` | 223 / 223 | 338 / 338 | 218 | 0 |
| `depthRangeMillimeters` | 34 / 34 | 34 / 34 | 522 | 0 |
| `fingerCapacity` | 161 / 161 | 179 / 179 | 40 | 337 |
| `handCapacity` | 0 / 0 | 0 / 0 | 556 | 0 |
| `gripType` | 134 / 134 | 180 / 180 | 376 | 0 |
| `features` | 32 / 32 | 70 / 70 | 486 | 0 |

The batch certifies 391 populated outcomes: 168 kinds, 115 scalar depths, 18
finger capacities, 48 grip enums, and 42 feature arrays. The 90 package
additions are the 48 grips and 42 features; the other exact values were already
present and are now tied to
stable-ID evidence records. Zlagboard's compound `sloper JUG` stays
`kind: sloper`, with `gripType: sloper` and feature `jug` preserving the whole
manufacturer label. The global after totals also incorporate the later removal
of two unsupported Trango grip values and four unsupported Trango feature
values; the 391 Task 9 outcomes themselves are unchanged.

Remaining blanks are deliberate. YY degree labels, mono phalange wording,
magnetic inserts, and portable-board inclination are not millimetre depth
ranges. Zlagboard's exhaustive maps do not assign the product page's general
`pockets` wording to any exact contact or publish finger/hand capacity. YY's
one-arm exercise wording likewise does not establish simultaneous hand
capacity. No edge posture or wide-contact hand count was inferred from
geometry.

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
| `tension-honestone` | `edge-20-15-{left,right}`, `edge-10-8-{left,right}` | `edge-{15,20}-{left,right}`, `edge-{8,10}-{left,right}` | The [product page](https://tensionclimbing.com/products/honestone) lists the four edge depths, and the [official labelled close view](https://tensionclimbing.com/cdn/shop/files/Honestone2.png?v=1726542571) maps each value to its own step. The 35°/45° macro sloper remains one unmeasured physical contact because Tension expressly describes continuously variable curvature. | 12 source physical contacts; all 11 pockets/edges use scalar depth; no depth ranges remain. |
| `tension-whetstone` | `edge-40-30-{left,right}`, `edge-25-20-{left,right}` | `edge-{30,40}-{left,right}`, `edge-{20,25}-{left,right}` | The [product page](https://tensionclimbing.com/products/whetstone) lists the four edge depths, and the [official labelled close view](https://tensionclimbing.com/cdn/shop/files/Whetstone2.png?v=1726542637) maps 40/30 and 25/20 to distinct planar steps. | 12 logical holds; all 11 pockets/edges use scalar depth; no depth ranges remain. |
| `frictitious.megalith` | `stepped-8-10-12-{left,right}`, `stepped-30-40-pocket-{left,right}`, `stepped-15-20-{left,right}` plus the overlapping unnamed `hold-11`…`hold-14` records | `edge-{8,10,12}-{left,right}`, `edge-30-{left,right}`, `edge-40-pocket-{left,right}`, `edge-{15,20}-{left,right}` | The [product page](https://frictitiousclimbing.com/products/megalith) enumerates seven shoulder-width edge sizes and identifies the two-finger pocket on the 40 mm edge. The [official labelled front](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front.jpg?v=1780436232&width=3840) and [official oblique detail](https://frictitiousclimbing.com/cdn/shop/files/Mega-4.jpg?v=1764914587&width=3840) map every value to a visibly separate planar shelf. The integrated pocket stays part of its 40 mm edge contact; no independent depth or capacity was invented. | 18 logical holds: 14 shoulder-width scalar edges, one 25 mm centre edge, one jug, and two mono pockets. No depth ranges or unnamed duplicate holds remain. |

The canonical ledger now uses the 14 replacement Tension contacts and contains
no retired range-backed IDs. After all certifications below, it accounts for
43 boards and 670 holds; Beastmaker 2000's 27 holds remain outside the ledger,
completing the current 697-hold catalog inventory.

Every replacement contact has a newly reviewed, closed canonical path authored
through Workbench. Adjacent steps share only their physical transition line;
none of the old full-recess paths or nested Megalith duplicates remains to
overlap selectable contacts. The four Whetstone source-side shelves were
independently re-authored after review of the labelled view: their differing
outer-end curvature, widths, and upper/lower recess boundaries are preserved
in four distinct canonical command arrays rather than translated copies.

### `tension-honestone` macro-sloper selection adaptation

Tension’s current [Honestone product page](https://tensionclimbing.com/products/honestone)
describes one top macro-textured sloper with 35° and 45° areas and continuously
variable curvature; it does not enumerate four discrete contacts or publish a
per-region depth, capacity, posture, or subtype. Hang Ten therefore retains
the source’s single physical-contact interpretation while exposing four
descriptive selectable regions—`macro-sloper-left`, `macro-sloper-left-center`,
`macro-sloper-right-center`, and `macro-sloper-right`—for practical app
selection. These regions are a clearly labelled product adaptation, not
manufacturer-labelled holds. The package consequently has 15 selectable holds
(four sloper regions, two pockets, and nine edges), while the source inventory
remains 12 physical contacts.

### Retained continuous ranges and ruled-out splits

| Package / IDs | Retained range | Why it is not a discrete-step candidate |
| --- | --- | --- |
| `trango.rock-prodigy-forge` / `variable-edge-rail-{left,right}` | 7–20 mm | Trango's [Forge depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887) maps the endpoints to one continuously sloped rail. There are no source-mapped shelf boundaries to split. |
| `trango.rock-prodigy-pivot` / `variable-edge-{left,right}` | 16–31 mm | The [Pivot depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905) maps numbered item 3, “Edge: 16mm–31mm (L–R),” to one continuous yellow rail on each half. `L–R` describes the depth change across that single sculpted contact; the guide shows no separate shelf boundary at either endpoint. |
| `trango.rock-prodigy-pivot` / `medium-crimp-{left,right}` | 9–10 mm | The same guide maps numbered item 4, “Medium Crimp: 9mm–10mm (L–R),” to one continuous purple crimp strip on each half. The 1 mm left-to-right variation occurs within one physical strip, so splitting its endpoints would invent contacts the source does not show. |
| `trango.rock-prodigy-pivot` / `large-crimp-{left,right}` | 11–12 mm | Numbered item 5, “Large Crimp: 11mm–12mm (L–R),” is drawn as one continuous grey crimp strip on each half. Its source-mapped left/right endpoint variation belongs to that single sculpted strip, with no intervening step. |
| `trango.rock-prodigy-pivot` / `two-finger-pocket-{left,right}` | 28–32 mm | Numbered item 6, “2-Finger Pocket: 32mm–28mm (L–R),” maps both endpoint depths to one orange pocket opening on each half. The package normalizes the bounds to 28–32 mm; the source shows a continuously sculpted pocket floor rather than two openings or shelves. |
| `trango.rock-prodigy-pivot` / `three-finger-pocket-{left,right}` | 17–28 mm | Numbered item 7, “3-Finger Pocket: 28mm–17mm (L–R),” maps both endpoints to one blue pocket opening on each half. The package normalizes the bounds to 17–28 mm; no source boundary divides that single sculpted pocket into discrete contacts. |

No package outside the four source-mapped stepped boards was split.

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

### Beastmaker 1000 conditional group-level certification

Beastmaker 1000 was re-reviewed against the current product page, its linked
official front, and a fresh 22-ID Workbench capture recorded in the
[Beastmaker source audit](2026-08-12-beastmaker-board-packages.md#2026-08-25-beastmaker-1000-source-audited-metadata-certification).
The official front supports 22 physical contacts—two jugs, three slopers, and
17 front cavities—even though the manufacturer's grouped copy totals only 15
pockets. The physical inventory and geometry therefore remain at 22; the
copy/image contradiction is recorded instead of deleting two visible cavities.

Mandatory kinds are certified as three conservative source-backed groups. The
two outer top contacts are the exact two-jug family, the other three top
surfaces are the 35-/20-degree sloper family, and all 17 front cavities retain
`pocket` because pockets are the exhaustive front-contact kind. This is a
shared-kind ruling only: it does not position Beastmaker's 10 mm pair,
deep/medium/small labels, or two-/three-/four-finger subtypes.

After the discrete-contact migration, the ledger moves from 42 boards / 648
holds to 43 boards / 670 holds. All 154
seven-field outcomes are explicit and all 22 mandatory kinds are verified:

| Field | Before populated / verified | After populated / verified | After unavailable | After not applicable |
| --- | ---: | ---: | ---: | ---: |
| `kind` | 648 / 648 | 670 / 670 | 0 | 0 |
| `sizeMillimeters` | 415 / 415 | 415 / 415 | 255 | 0 |
| `depthRangeMillimeters` | 20 / 20 | 20 / 20 | 650 | 0 |
| `fingerCapacity` | 185 / 185 | 185 / 185 | 73 | 412 |
| `handCapacity` | 1 / 1 | 1 / 1 | 669 | 0 |
| `gripType` | 182 / 182 | 182 / 182 | 488 | 0 |
| `features` | 105 / 105 | 105 / 105 | 565 | 0 |

Every optional Beastmaker 1000 field remains blank. The pass removes 17
unsupported pocket scalar depths, 19 duplicated kind-as-feature arrays, and
the two jugs' unsupported capacity, open-hand posture, and feature arrays. The
center sloper receives only a source-faithful display name. No geometry,
presentation asset, Beastmaker 2000 metadata, or unrelated package changed.

## Remaining unsupported metadata

The audit did not leave values blank merely because they were difficult to
read. Each group below was checked against the indicated primary materials and
remains blank for a specific evidence reason.

| Packages / contacts | Fields deliberately left blank | Reason and source status |
| --- | --- | --- |
| `beastmaker-1000` pockets; `beastmaker-2000` unmapped pockets and edges; `dewoodstok-woodbord` pockets | Per-contact capacity and/or depth | Product pages give product or family facts but no numbered per-contact mapping. The prior catalog audit explicitly prohibits applying aggregate values to a pocket ID. |
| `beastmaker-2000` | Full seven-field ledger certification | Beastmaker's current sources do not map the board's mixed front recesses to exact stable IDs. Mandatory per-ID type certification therefore remains blocked and unchanged. |
| `frictitious.doormount-pro-7` unnamed lower records and mixed contacts | Depth and capacity | [DoorMount Pro](https://frictitiousclimbing.com/products/doormount-pro) lists the 35/25/20/15/10 mm families and pockets, but its declared seven-hold inventory does not map those facts to this package's 13 current logical records. A fresh field assignment would be an inference; the inventory discrepancy needs a separate physical-contact reconciliation. |
| `soill.training-tiles`; `tension.flash-board` | Training Tiles: all per-contact fields; Flash Board: per-contact depth and, where applicable, pocket capacity | Training Tiles' current listing has no manufacturer-authored per-contact map, count, dimensions, capacities, or roles, so its 20 app-adapted contacts retain no optional values. Flash Board publishes grouped family information rather than an individual ID-to-value guide. |
| `trango.rock-prodigy-forge` IM pockets; `trango.rock-prodigy-natural` centre-lower and supported pockets; `trango.rock-prodigy-training-center` variable rails and pockets | Exact per-contact depth | Forge's official guide gives only an aggregate IMR range. Natural's official product markings and quick-start guide conflict on the affected values/capacities. The Training Center manual names only selected training grips and lacks a depth map for each physical package contact. |
| `frictitious.megalith` mono pockets | Exact depth | Manufacturer material identifies the board-level pocket family but does not establish individual depths for these exact mono contacts. |
| All other blanks on jugs, edges, pinches, and slopers | `fingerCapacity` | The reviewed primary source does not constrain a fixed number of fingers. Capacity was not guessed from a hold's apparent width or use photograph. |

Existing explicit capacities (mono, duo, three-finger, four-finger) and
source-mapped scalar depths elsewhere in the 44 packages were rechecked and
retained unless a later scoped certification above records an exact correction
or addition. Apart from the discrete-contact correction and fractional mappings
above, no other `kind`, `fingerCapacity`, or scalar `sizeMillimeters` change was
justified by the additional evidence. No optional value was populated from
apparent size or geometry.
