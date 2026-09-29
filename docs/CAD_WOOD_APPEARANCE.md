# Runtime wood appearance for CAD boards

Each wooden CAD package explicitly authors `media.display.woodNodeIDs` in its
native `HangTenBoardManifest`. The iOS RealityKit renderer reads those surface
selections and applies a warm matte procedural grain finish. The USDZ packages
remain unchanged, unbound, and texture-free. No geometry, UVs, descriptor paths,
suspension, or contact facts are changed. Only the native manifest display metadata is
updated with `set_board_manifest.py`; every other FCStd archive member is
verified byte-identical. The delivery lock records the new metadata hashes.

The color and grain are a deliberately subtle visual adaptation, not a
manufacturer-exact reproduction of a wood species, stain, veneer, or plywood
lamination. The same generic finish is used across the opted-in wood products.
The shader samples model-space positions in metres so body/contact meshes
share continuous grain and the pattern rotates with the board. Derivative
filtering suppresses fine fibres at thumbnail sizes. Its material is created
once and reused; failure to load Metal falls back to warm matte PBR.

## Product material mapping

These are explicit package-owned surface selections, not keyword detection. IDs and source
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
| `nature.stoak-board-iii` | [Product source](https://natureclimbing.com/products/stoak-board-iii) | Explicit oak nodes only (see below) |

The optional `woodNodeIDs` array contains exact body/contact descriptor node
IDs. It is display metadata only: the USDZ remains the geometry source of truth.
An empty array has the same neutral behavior as omission.

## Mixed oak/granite mapping

For `nature.stoak-board-iii`, the current CAD descriptor assigns the oak finish
to `body_board_001`, `left_tapered_wood_edge_001`,
`right_tapered_wood_edge_001`, `top_jug_001`, and
`upper_centre_wood_edge_001`. The three granite nodes
`centre_granite_edge_001`, `left_granite_edge_001`, and
`right_granite_edge_001` retain neutral PBR. Material selection follows these
explicit authored node IDs, never contact names or pixel appearance.

Packages without `display.woodNodeIDs` retain neutral PBR, including the molded Metolius boards,
So iLL boards, Evolv Kilter, Escape Beta, Trango resin boards, and Clavellium's
PETG block. New or revised products need explicit evidence-backed node selections in their
package metadata. The renderer contains no board IDs or product-specific node
mappings. Both package validators reject duplicate, unknown, or attachment node
IDs; missing metadata defaults to the neutral finish.

## Highlighting

Capture the full material as each entity's baseline, including `CustomMaterial`.
Active and preview selection temporarily use the existing solid PBR highlight
colors for legibility. Clearing a highlight restores the exact baseline finish.
The suspension cord continues to use its existing independent dark material.

## Validation

Use `validate-hang-ten-ios` on a workspace-owned simulator. Check the original
neutral board against the new wood finish, highlighted recesses, and the mixed
Stoak board. `BoardModelRealityTests` covers wood highlight/restore and mixed
wood/stone selection alongside existing neutral-material and picking checks.
