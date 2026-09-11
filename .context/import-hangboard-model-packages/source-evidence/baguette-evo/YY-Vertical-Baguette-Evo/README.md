# YY Vertical Baguette Evo

Editable Blender display reconstruction of the round **Baguette Evo, Turn & Pull version**, SKU **YY BAGUETTE EVO**, EAN **3760305271822**. Based on the current manufacturer listing and photographs accessed 11 September 2026. The manufacturer does not publish a numbered subrevision. The catalog listing was published 7 March 2025; that is not asserted as the manufacturing date. The older rectangular La Baguette and wall-mounted VerticalBoard Evo are different products and are excluded.

**Fidelity limit:** this is a photograph-constrained display asset, not a scan or manufacturer CAD model. The published envelope, named grip inventory and visible arrangement are supported; exact machining profiles, pocket widths, fillets and bore dimensions are not published. Their explicit estimates are recorded below and in `geometry-parameters.json`. Public evidence cannot establish an exact, tolerance-verified reconstruction. The less clearly photographed small-edge geometry is called out rather than claimed as measured.

## Files

- `YY-Vertical-Baguette-Evo.blend` — editable source geometry, one clean asset scene.
- `YY-Vertical-Baguette-Evo.glb` — optional mobile-oriented glTF 2.0 export with embedded texture and node metadata.
- `evidence/` — original reference images, manufacturer page/catalog snapshots, URL/rights ledger and checksums.
- `renders/` — five requested labeled views, one supplementary top view, and an actual Blender Outliner screenshot.
- `textures/` and `texture-manifest.md` — original neutral 1K base color and complete material provenance.
- `hold-mapping.json`, `cord-markers.json` — stable app-facing identities and marker coordinates.
- `geometry-parameters.json`, `validation-report.json` — reconstruction parameters and machine-checked asset inventory.
- `scripts/` — repeatable Blender build and validation scripts. Render rigs exist only during generation and are never saved in the asset.

## Published specifications

| Item | Source-backed value | Evidence / conflict |
|---|---|---|
| Overall envelope | 520 × 50 × 50 mm; circular Ø50 mm cross section | Manufacturer product page; round end and outline visible in photos 03/10 |
| Wood | Rubberwood (hevea) | Manufacturer. Bergfreunde lists poplar; manufacturer takes precedence. |
| Mass | Approximately 550 g | Manufacturer product copy. JSON variant: 520 g. Retailer prose: 415 g; another retailer table: 550 g. No simulation mass is assigned. |
| Paired grip options | 25, 20, 15, 12, 10, 8, 6 mm | Explicit manufacturer inventory; 10/15/20/25 and 8/12 labels visible in close-ups |
| Central grip options | 30, 25, 20, 6 mm | Explicit inventory; reverse 25/30 clearly photographed; small 20/6 pairing partly visible |
| Rounded option | Comfortable rounded warm-up contact | Manufacturer description and two-handed use images |
| Suspension | Portable, no wall installation; angle adjustment with Turn & Pull | Manufacturer and visible suspension photography |
| Supplied items visibly established | Wooden board and orange/gray cord, paper packaging sleeve | Manufacturer gallery. No complete itemized packing list or cord length/diameter was published in the reviewed page. |
| Retailer stated maximum | 120 kg | Secondary evidence only; not a rating for this digital model |

Manufacturer source: [Baguette Evo](https://www.yyvertical.com/en/products/baguette-evo). Full sources, limitations and conflicts: [evidence/sources.md](evidence/sources.md).

## Coordinates, source geometry and export

Created and verified in **Blender 4.2.0**, build `a51f293548ad`. Units are metric **meters**, unit scale 1.0. **Z is up**, **X is left/right**, and the primary paired-pocket face points toward **−Y**. Origin is the center of the uncut board envelope. Front-view left/right remains fixed when the camera moves around the board.

All 21 mesh objects have applied identity transforms, a common origin, real mesh faces and one UVMap. Four marker empties sit at their bore centers. No live Geometry Nodes, unapplied Boolean/bevel/subdivision modifiers, cameras, lights, wall, hardware, rope, knots or environmental objects are present. Small recesses, stepped back walls, rounded lips, broad shallow pocket shoulders and physical bore walls are mesh geometry.

The body and 20 contact objects partition a continuous outer surface. They are not overlapping highlight shells. Individual contacts are intentionally open surface patches; the combined surface is closed. Do not add thickness or shrink-wrap offsets in the app. Every contact uses the same original wood material. For highlighting, assign a copied/tinted material to the named object; editing the shared material itself recolors every object.

The GLB contains triangulated exported primitives, preserved node names, custom properties and one embedded texture. Standard glTF uses **Y up**: Blender `(x, y, z)` becomes glTF `(x, z, −y)`. Custom coordinate arrays in extras and JSON remain in the documented Blender basis; convert them explicitly if using those arrays instead of the node transforms. The package does not claim testing in a specific iOS rendering framework.

## Hold IDs and object mapping

There are **12 advertised grip types**: seven paired depths, four central depths and the rounded option. Splitting the paired options for left/right highlighting yields **20 selectable meshes**. This does not assert twenty separate manufactured recesses. Some opposite contacts occupy different sides of the same recess and become usable when the board rotates.

Object name and stable hold ID are identical. The contact selection patches include the relevant inward surface and lip, while the broad shallow shoulders remain on `body`. Rounded-contact patch boundaries are app selection regions on a continuous cylinder, not invented grooves or physical seams.

| Hold ID / object | Nominal depth | Position and contact | Evidence |
|---|---:|---|---|
| `hold-central-06mm` | 6 mm | Center, small top recess; rear side | Inventory + photo 07; offset/profile estimated |
| `hold-central-20mm` | 20 mm | Center, small top recess; front side | Inventory + photo 07; offset/profile estimated |
| `hold-central-25mm` | 25 mm | Center, reverse recess; lower contact | Photo 05 |
| `hold-central-30mm` | 30 mm | Center, reverse recess; upper contact after inversion | Photo 05 |
| `hold-edge-06mm-left` | 6 mm | Left, outer small channel; same nominal depth on opposite sides | Inventory + oblique gallery; profile estimated |
| `hold-edge-06mm-right` | 6 mm | Right, outer small channel; same nominal depth on opposite sides | Inventory + oblique gallery; profile estimated |
| `hold-edge-08mm-left` | 8 mm | Left, inner small channel; rear-facing contact | Photo 08 labels + inventory |
| `hold-edge-08mm-right` | 8 mm | Right, inner small channel; rear-facing contact | Photo 08 labels + inventory |
| `hold-edge-10mm-left` | 10 mm | Left, outer part of primary stepped recess; lower contact | Manufacturer photos 04/06 |
| `hold-edge-10mm-right` | 10 mm | Right, outer part of primary stepped recess; lower contact | Manufacturer photos 04/06 |
| `hold-edge-12mm-left` | 12 mm | Left, inner small channel; front-facing contact | Photo 08 labels + inventory |
| `hold-edge-12mm-right` | 12 mm | Right, inner small channel; front-facing contact | Photo 08 labels + inventory |
| `hold-edge-15mm-left` | 15 mm | Left, deeper inner step of primary recess; lower contact | Manufacturer photos 04/06 |
| `hold-edge-15mm-right` | 15 mm | Right, deeper inner step of primary recess; lower contact | Manufacturer photos 04/06 |
| `hold-edge-20mm-left` | 20 mm | Left, outer part of primary stepped recess; upper contact after inversion | Manufacturer photos 04/06 |
| `hold-edge-20mm-right` | 20 mm | Right, outer part of primary stepped recess; upper contact after inversion | Manufacturer photos 04/06 |
| `hold-edge-25mm-left` | 25 mm | Left, deeper inner step of primary recess; upper contact after inversion | Manufacturer photos 04/06 |
| `hold-edge-25mm-right` | 25 mm | Right, deeper inner step of primary recess; upper contact after inversion | Manufacturer photos 04/06 |
| `hold-rounded-left` | Unspecified | Left, rounded lower cylinder contact region | Manufacturer warm-up description and photos 12/13 |
| `hold-rounded-right` | Unspecified | Right, rounded lower cylinder contact region | Manufacturer warm-up description and photos 12/13 |

`body` is the only nonselectable mesh and has `selectable=false`. Contact meshes have `asset_role=selectable_hold`, `selectable=true`, `hold_id`, `nominal_depth_mm` and source-feature metadata. A value of 0 for a rounded contact means unspecified, not a zero-depth edge.

## Cord handling

The supplied cord is visibly continuous, but the suspended configuration has **four branches**, two at each end. Accordingly this uses the multi-branch marker convention. Photographs 01/02/03/04/06/10 establish four physical passage openings per face, in two end pairs, plus an exterior wrap used for Turn & Pull. No rope, knot, anchor, attachment hardware or simulated tension path is baked into the asset.

There is one empty per physical bore. Names increase **left to right in the front view**; they do not assert a continuous rope traversal order. Each marker is at the bore center and stores front/reverse mouth coordinates, axis and estimated diameter. This avoids inventing a single anchor point or ambiguous hidden path.

| Marker | Center, meters | Front mouth | Reverse mouth |
|---|---|---|---|
| `cord-passage-1` | (−0.246, 0, 0) | (−0.246, −0.025, 0) | (−0.246, +0.025, 0) |
| `cord-passage-2` | (−0.231, 0, 0) | (−0.231, −0.025, 0) | (−0.231, +0.025, 0) |
| `cord-passage-3` | (+0.231, 0, 0) | (+0.231, −0.025, 0) | (+0.231, +0.025, 0) |
| `cord-passage-4` | (+0.246, 0, 0) | (+0.246, −0.025, 0) | (+0.246, +0.025, 0) |

Straight front-to-reverse bore axes and Ø7.2 mm are reconstruction estimates from aligned visible mouths. Their exact angle, counterbore/chamfer and internal finish are not documented by the manufacturer. The exterior cord wrap is visibly supported; its changing path as the cylinder rotates is intentionally left to the app. No ordered full rope route is asserted.

## Estimated geometry and limitations

| Quantity / feature | Model value or decision | Basis / practical limit |
|---|---|---|
| Main recess span, each side | X magnitude 58–217 mm | Proportioned to the 520 mm body in manufacturer front photos; approximate, not measured CAD |
| Deeper inner step | X magnitude 58–135 mm | Visible nested step in photos 04/06 |
| Shallow shoulder | X magnitude 52–224 mm; nominal radial floor 18 mm | Broad flattened/recessed transition visible in photos 04/06; exact curvature unknown; stays body geometry |
| Small paired channels | Inner: 58–135 mm; outer: 140–217 mm | Oblique manufacturer views. Circumferential placement and detailed profiles are estimates. |
| Central recess lengths | 80 mm | Photo-proportioned to reverse view |
| Internal contact profiles | Planar/sloped capsule approximations | Nominal opposing depths constrain the model, but precise depth datum, undercut, slope and milling radius are unpublished |
| Small central profile | Tangential offset −10 mm; 6/20 mm nominal contacts | Partially obscured in photography. This is the least certain reconstructed region. |
| Edge rounding | Up to 1.3 mm, clamped at tight geometry | Visible softened edges; exact radii unpublished |
| End rounding | Approximately 2 mm | Manufacturer end view; not a measured fillet |
| Bore geometry | Centers above, Ø7.2 mm, through Y | Photo-proportioned and explicitly estimated |
| Rounded contact boundaries | Separate left/right lower arc regions | Highlighting regions only; physical surface remains continuous |
| Surface appearance | One uniform, matte light-wood neutral PBR material | Wood tone is approximate; no calibrated albedo/roughness data available |
| Markings | Brand, end engraving and numerical engravings omitted | No reusable licensed artwork established; original factual labels remain in metadata |

No tolerance is claimed for photo-derived dimensions. Actual measurement or manufacturer CAD would be needed to validate the small-edge profiles and internal bore geometry. The referenced source photos are retained so these estimates can be revised without losing app-facing IDs.

## Materials and licenses

One 1024 × 1024 original PNG supplies the base color. It is packed in the `.blend`, embedded in the GLB and present in `textures/`. No normal/roughness/AO maps were invented. Roughness is a neutral scalar rendering choice. The material remains continuous across object boundaries and has no directional grain texture to stretch.

Original neutral texture and scripts: **CC0-1.0**, as stated in `LICENSE-original-assets.txt`. Third-party reference images and page snapshots retain their owners’ rights. They are research evidence and are not licensed runtime textures. Product names identify the modeled object; this package makes no grant of third-party trademark or design rights. See [texture-manifest.md](texture-manifest.md) for the per-file manifest.

## Validation and views

Verified result: **PASS** — 17,392 triangles, 21 mesh objects, 20 selectable contacts, four markers, one packed texture and zero nonmanifold edges in the combined surface.

`validation-report.json` records a fresh Blender file reopen and checks for the required object set, exact published envelope, identity mesh transforms, UV bounds, embedded texture, absence of rig objects, combined-surface topology and GLB node/texture preservation. These checks verify asset construction, not unknown physical dimensions.

The five requested labeled renders are front, reverse, oblique, main hold/attachment detail, and neutral material close-up. A top view supplements the small-edge inspection. The Outliner image is captured from the actual Blender application, with all contact objects and passage markers visible. Render cameras/lights and labels exist only in the render workflow, never in the saved model.

To regenerate: `blender -b --factory-startup --python scripts/build_asset.py`. To validate: `blender -b YY-Vertical-Baguette-Evo.blend --python scripts/verify_asset.py`. Run from the package directory, using Blender 4.2.0. Texture files must remain present when rebuilding; the saved `.blend` itself is self-contained.
