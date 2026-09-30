# Runtime wood appearance for CAD boards

Each wooden CAD package chooses `media.display.surfaceFinish: "wood"` once in
its native `HangTenBoardManifest`. The iOS renderer applies the same warm matte
procedural grain to every body and hold mesh, including complete recesses and
new importer children. Attachment-role nodes remain neutral; cords retain their
independent material. This removes the need to enumerate every mesh to get
complete coverage.

USDZ packages remain unbound and texture-free. Only the native display metadata
changes through `set_board_manifest.py`; every other FCStd archive member and
all USDZ/descriptor bytes are verified unchanged. Geometry and physical contact
facts are unchanged.

The color and grain are a deliberately subtle visual adaptation, not a
manufacturer-exact reproduction of a wood species, stain, veneer, or plywood
lamination. The same generic finish is used across the opted-in wood products.
The shader samples model-space positions in metres so body/contact meshes
share continuous grain and the pattern rotates with the board. Derivative
filtering suppresses fine fibres at thumbnail sizes. Its material is created
once and reused; failure to load Metal falls back to warm matte PBR.

## Product material mapping

These are package-owned board finish choices, not keyword detection. IDs and source
URLs below come from each native FCStd's retained board manifest. The retained
wood product metadata, manufacturer product descriptions/specifications, and
source evidence determine eligibility. The Lattice catalogue identifies the
MXEdge Lift as beech and the Mini Bar as tulipwood. The Pocket
Lines product specifies birch plywood; Helium Mobile specifies natural wood;
The Hangboard specifies European beech. Metolius Light Rail and Prime Rib
product pages retain FSC certification and wooden product imagery.

| Board ID | Manufacturer/product evidence | Surfaces receiving wood |
| --- | --- | --- |
| `beastmaker-1000` | [Product source](https://www.beastmaker.co.uk/collections/fingerboards/products/beastmaker-1000-series) | Body and contact nodes; attachments excluded |
| `beastmaker-2000` | [Product source](https://www.beastmaker.co.uk/products/beastmaker-2000-series) | Body and contact nodes; attachments excluded |
| `captain-fingerfood.pocket` | [Product source](https://en.captainfingerfood.rocks/products/lines-hangboard) | Body and contact nodes; attachments excluded |
| `crimptonite.helium-mobile` | [Product source](https://crimptonite.com/product/helium-mobile/) | Body and contact nodes; attachments excluded |
| `dewoodstok-woodbord` | [Product source](https://www.dewoodstok.nl/product/hangboard-woodbord/) | Body and contact nodes; attachments excluded |
| `escape.unlimited` | [Product source](https://escapeclimbing.com/products/ec72000) | Body and contact nodes; attachments excluded |
| `frictitious.doormount-pro-7` | [Product source](https://frictitiousclimbing.com/en-ca/products/doormount-pro) | Body and contact nodes; attachments excluded |
| `frictitious.megalith` | [Product source](https://frictitiousclimbing.com/products/megalith) | Body and contact nodes; attachments excluded |
| `j-bryant.ftg-32` | [Product source](https://www.amazon.com/dp/B0FZGY19T9) | Body and contact nodes; attachments excluded |
| `lattice.mini-bar` | [Product source](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf) | Body and contact nodes; attachments excluded |
| `lattice.mxedge-lift-large` | [Product source](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf) | Body and contact nodes; attachments excluded |
| `lattice.mxedge-lift-small` | [Product source](https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf) | Body and contact nodes; attachments excluded |
| `lattice-triple-rung` | [Product source](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | Body and contact nodes; attachments excluded |
| `metolius.climbers-edge` | [Product source](https://www.metoliusclimbing.com/products/climbers-edge-board) | Body and contact nodes; attachments excluded |
| `metolius.light-rail-2` | [Product source](https://www.metoliusclimbing.com/products/light-rail) | Body and contact nodes; attachments excluded |
| `metolius.prime-rib` | [Product source](https://www.metoliusclimbing.com/products/prime-rib) | Body and contact nodes; attachments excluded |
| `metolius.wood-grips-compact-ii` | [Product source](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) | Body and contact nodes; attachments excluded |
| `metolius.wood-grips-deluxe-ii` | [Product source](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) | Body and contact nodes; attachments excluded |
| `moon.armstrong` | [Product source](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | Body and contact nodes; attachments excluded |
| `target10a.linebreaker-base` | [Product source](https://www.target10a.com/en/linebreaker-boards/409-linebreaker-base-trainingsboard.html) | Body and contact nodes; attachments excluded |
| `tension.grindstone` | [Product source](https://tensionclimbing.com/products/grindstone) | Body and contact nodes; attachments excluded |
| `tension.grindstone-pro` | [Product source](https://www.tensionclimbing.com/hangboards/grindstone-pro) | Body and contact nodes; attachments excluded |
| `the-hangboard.the-hangboard` | [Product source](https://thehangboard.com/products/hangboard) | Body and contact nodes; attachments excluded |
| `nature.stoak-board-iii` | [Product source](https://natureclimbing.com/products/stoak-board-iii) | Wood with three source-backed granite inserts (see below) |

## Board-wide coverage and Stoak correction

`surfaceFinish` is `wood`, `plastic`, `granite`, or `neutral`. Omission preserves the legacy
neutral default. The native CAD catalog explicitly chooses one finish for every
board. Existing optional `woodNodeIDs` / `plasticNodeIDs` are supported for
whole-node overrides in legacy packages; native packages no longer rely on
exhaustive node lists. Attachment nodes always stay neutral. Both validators
reject invalid finish values and unknown display fields.

Stoak keeps wood as its board-wide default. Three separately authored CAD surface
nodes receive granite via `graniteNodeIDs`: the larger lower-center pocket insert
and the outer ends of the two lower side pockets. Their pocket floors, rounded
front lips and front faces share a subtle charcoal mineral shader. The wooden
rear walls, roofs, inner side edges and small upper-center pocket retain wood.
Both validators require override selectors to be unique, disjoint, and bound to
body/contact nodes; attachments cannot receive an override. Granite material
selection is independent of contact identity, so a mixed contact highlights and
restores both finishes together. See
[the approved evidence and CAD partition audit](source-audits/2026-09-29-stoak-granite-surfaces.md).

The granite appearance is supplied at runtime. USDZ meshes stay unbound and
texture-free; no per-pixel height cutoff paints wood gray. The CAD splits actual
surfaces at explicitly authored material boundaries. The retained parametric
solid and physical contact metadata are unchanged. Legacy node names remain
identity strings, not material evidence.

The previous correction introduced `woodNeutralBands` and hand-selected height
cutoffs to paint pocket bottoms gray. That answered a different appearance
question and preserved the reported symptom. Those estimates, their schema,
and their shader branch have been removed. They must not be used as material
or geometry authoring precedent.

The earlier process checked that chosen material parameters survived selection,
but did not establish that the resulting appearance met the user’s request.
The acceptance check now starts with an unhighlighted whole-board render:
inspect the complete walls, rear faces, floors, lips and transitions of every
pocket. Then exercise selection and clearing to ensure the same finish returns.
A passing material-type test alone does not establish visual correctness.

The catalog audit covers 35 native CAD boards: 24 wood, 11 plastic and 480
body/contact descriptor meshes. A catalog test requires a board-level finish
for every native source. An iOS catalog test loads every opted-in model and
checks all imported body/hold meshes for its finish. A regression also verifies
that an unlisted imported mesh inherits the board finish while an attachment
stays neutral. These are coverage checks; actual app screenshots remain the
appearance acceptance evidence.

Plastic boards choose `surfaceFinish: "plastic"`; see
[CAD plastic appearance](CAD_PLASTIC_APPEARANCE.md). The renderer contains no
product IDs, product-name heuristics, or per-pocket coordinate cutoffs.

## Highlighting

Capture the full material as each entity's baseline, including `CustomMaterial`.
Active and preview selection temporarily use the existing solid PBR highlight
colors for legibility. Clearing a highlight restores the exact baseline finish.
The suspension cord continues to use its existing independent dark material.

## Validation

Use `validate-hang-ten-ios` on a workspace-owned simulator. Review normal wood
and mint boards at detail and thumbnail size before checking highlights. Inspect
all of Stoak’s pocket floors while no hold is selected. Keep the before/after
screenshots with the audit. `BoardModelRealityTests` covers catalog mesh coverage,
new-mesh inheritance, attachment isolation and full highlight restoration.
