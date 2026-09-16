# Hangboard Collection model imports

## So iLL Training Tiles (`soill.training-tiles`)

Reviewed 2026-09-15. `Hangboards/soill-training-tiles/board.json` remains the
sole authority for this paired-tile revision's existing 20 `contacts[].id`
values, names, kinds, and deliberately empty optional factual fields. The
model conversion does not add or revise a contact fact. The catalog's 20
descriptive selection regions are retained exactly: the source manufacturer
evidence describes grouped families rather than a 20-contact factory map.

### Retained visual evidence

| ID | Publisher and URL | Retained local copy and SHA-256 | Supports | Does not support |
| --- | --- | --- | --- |
| ST-FRONT | So iLL — [official front photograph](https://soillholds.com/cdn/shop/products/training-tiles-so-ill-x-meagan-martin-so-ill-white-12-01-so-ill-670960_2048x.jpg?v=1677258630) | `.context/lumpy-liger-hangboard-collection/soill-training-tiles/retained-evidence/soill-training-tiles-front.jpg` — `1061453fa5110467cc0110007555bb70a946b8012b00bb5dc462d60677123c86` | Mirrored two-piece arrangement, visible contact-family positions, front contours, and visible mounting-opening existence. | A 20-contact factory inventory, contact depths, hole measurements, rear geometry, or a fixed installation gap. |
| ST-OBLIQUE | So iLL — [official oblique photograph](https://soillholds.com/cdn/shop/products/training-tiles-so-ill-x-meagan-martin-so-ill-white-12-01-so-ill-235347_2048x.jpg?v=1677258630) | `.context/lumpy-liger-hangboard-collection/soill-training-tiles/retained-evidence/soill-training-tiles-oblique.jpg` — `c1643a70b32b10b04d62ddc11bc1cd987976e883e26e9838f0509ce809d2b67a` | Relative front projection of the paired tiles, pocket/crown relationship, and non-contact body transitions. | Exact section profiles, material microtexture, unshown rear features, or a mapping of published grouped measurements to individual IDs. |

The So iLL [Training Tiles product page](https://soill.ca/products/training-tiles-so-ill-x-meagan-martin)
and existing `2026-08-12-soill-tension-board-packages.md` audit were also
reviewed for revision identity: it describes a two-piece So iLL x Meagan
Martin set, approximately 14 × 8 in per tile, and grouped pocket, sloper, and
edge families. It does not publish a 20-ID map. The source-delivery README
calls the 0.026 m inter-tile gap a display arrangement, not an installation
measurement; no gap fact is stored in the catalog.

### Source, omissions, and explicit mapping

The user-provided source delivery is retained at
`.context/lumpy-liger-hangboard-collection/soill-training-tiles/source-delivery/soill-training-tiles.glb`,
SHA-256 `775b5f985d47894836aa5bb897a82be68edee64e0c46d9567b136c3956576186`.
It contains 22 reviewed mesh nodes: `body-L`, `body-R`, and the exact 20
named contact meshes below. Its source document identifies the top pocket and
crown as three user-approved selection regions per tile—not distinct
manufacturer-listed holds. That decision is already represented by the
pre-existing contact IDs and is neither altered nor converted into a factual
measurement here.

The delivery does not include screws, but does visibly model ten mounting
bores per tile and an approximate body wordmark. Mounting holes and the
unverified approximate wordmarks are excluded by the model-package display
contract: a reviewed direct-author correction adds 20 nonselectable bore caps
and two plain wordmark covers. The supplied model's rear treatment, fillets,
bore locations, and display gap remain source model caveats only. No logo,
hardware, bore, spacing, or reconstruction detail is bound as a contact or
promoted to `board.json` facts.

| Left source node → stable contact ID | Right source node → stable contact ID |
| --- | --- |
| `hold-L-sloper-outer` → `upper-sloper-outer-left` | `hold-R-sloper-outer` → `upper-sloper-outer-right` |
| `hold-L-sloper-inner` → `upper-sloper-inner-left` | `hold-R-sloper-inner` → `upper-sloper-inner-right` |
| `hold-L-edge-middle-outer` → `middle-edge-outer-left` | `hold-R-edge-middle-outer` → `middle-edge-outer-right` |
| `hold-L-edge-middle-inner` → `middle-edge-inner-left` | `hold-R-edge-middle-inner` → `middle-edge-inner-right` |
| `hold-L-edge-bottom-center` → `bottom-edge-center-left` | `hold-R-edge-bottom-center` → `bottom-edge-center-right` |
| `top-pocket-left` → `top-pocket-outer-left` | `top-pocket-right` → `top-pocket-outer-right` |
| `hold-L-edge-bottom-inner` → `bottom-edge-inner-left` | `hold-R-edge-bottom-inner` → `bottom-edge-inner-right` |
| `hold-L-edge-bottom-outer` → `bottom-edge-outer-left` | `hold-R-edge-bottom-outer` → `bottom-edge-outer-right` |
| `top-pocket-inner-left` → `top-pocket-inner-left` | `top-pocket-inner-right` → `top-pocket-inner-right` |
| `top-jug-left` → `top-jug-left` | `top-jug-right` → `top-jug-right` |

`body-L`, `body-R`, and the direct-authored
`mounting-hardware-omission-caps` are the only nonselectable source nodes. The
complete ordered mapping is retained at
`.context/lumpy-liger-hangboard-collection/soill-training-tiles/contact-mapping.json`.
It maps every source node explicitly, binds each existing contact once, and
keeps the upper outer rim, recessed inner pocket, and upper jug/crown regions
separate on both tiles.

| Artifact | SHA-256 | Disposition |
| --- | --- | --- |
| Material-only transport source | `06179e3b5ca5c8fcdd2303e358f9575d927c02e248aace60e234a55ddc3ee198` | Empty-scene GLB import with one directly authored packed color image, required by the USDZ image-material contract; contact topology is unchanged. |
| Corrected transport source | `5b1aaeed8a05d76653453bd2bb693c3498b1cd1bcaaf3a2cd9005bba83ae9364` | Adds 20 nonselectable direct-authored mounting-bore caps and two plain wordmark covers only; all 20 contact mesh triangle counts are unchanged. |
| Promoted `assets/primary.usdz` | `4cb007105f5c70d57e739c884964d130f6ccf524d4c4adb974892bda4f670ebf` | Exact shipped USDZ, exported then imported into an empty Blender scene. |
| Promoted descriptor | `fa3e18d155a9ba3f808fef2ce9c1c4e6a076cd141f1d842440cf6dcb192395b8` | Hash-binds the shipped USDZ and is compiled from actual importer-visible triangles. |

The exact shipped asset verifier starts from an empty Blender scene and checks
the promoted USDZ hash, all 23 importer-visible triangulated mesh nodes, 20
contact keys, three nonselectable body nodes, usable image materials, and 494
triangles in the bore/wordmark-omission cap node. Its report is
`.context/lumpy-liger-hangboard-collection/soill-training-tiles/shipped-usdz-verification.json`.
The shipped package has only `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`; the raster presentation, primary PNG, canonical
paths, and fallback geometry are removed.

A human front render of the exact shipped USDZ was reviewed at
`.context/lumpy-liger-hangboard-collection/soill-training-tiles/reports/shipped-front-review.png`
(SHA-256 `a4a20d853f0e90cca3a909479f202380ee6ab87aa3d361e5dd6b4da9745727bb`):
it retains both mirrored tiles and the distinct rim/interior/jug regions while
the direct omission covers remove the approximate wordmarks and do not create
selectable contacts. Focused descriptor/importer/package tests passed, as did
`scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
and `status --root Hangboards`; the iOS `build-for-testing` product was also
generated from the exact package.

## Metolius Simulator 3-D (`metolius.simulator-3d`)

Re-reviewed 2026-09-16. `Hangboards/metolius-simulator-3d/board.json` is the
authority for this revision's 30 `contacts[].id` values and every name, kind,
shape, finger-capacity, depth, and product fact. The #2/#3 model-node split is
a factual catalog correction; it does not alter the USDZ.

### Retained visual evidence

| ID | Publisher and URL | Retained local copy and SHA-256 | Supports | Does not support |
| --- | --- | --- | --- | --- |
| MS-PHOTO | Metolius — [product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Simulator-black-white.jpg?v=1759460469) | `.context/lumpy-liger-hangboard-collection/metolius-simulator-3d/retained-evidence/metolius-simulator-product.jpg` — `5ac1677d6280dc90242cb1dcef47691647fd3f5a9adc3c465838e930075f58a9` | Exact Simulator 3-D silhouette, molded contact arrangement, broad arc, and mounting-opening existence. | Measured hole centers, radii, countersinks, rear geometry, or unsourced contact dimensions. |
| MS-DIAGRAM | Metolius — [numbered hold diagram](https://www.metoliusclimbing.com/cdn/shop/files/sim-num-dep_c543622d-e670-4601-8d4d-792cc8e46dea.jpg?v=1762201085) | `.context/lumpy-liger-hangboard-collection/metolius-simulator-3d/retained-evidence/metolius-simulator-numbered-hold-diagram.jpg` — `e9561ab3fb6d3a85014097dcbdb0bc3d9c4079f9cb0954bd87965d180329932a` | Numbered positions 1–18, pocket capacities/depths, edge depths, and distinct #2 flat / #3 round sloper labels. | Local profiles, recess depths, hidden geometry, or mounting dimensions. |

The Metolius [product page](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board)
was also reviewed for exact identity, 28 × 8.75 in (711 × 222 mm) envelope,
and the documented CAD/CAM symmetry. These two manufacturer visuals are
materially distinct exact-revision sources. They are evidence only: source
pixels were not traced, registered, segmented, or used to infer a contact map.

### Source, correction, and explicit mapping

The user-provided source GLB is retained at
`.context/lumpy-liger-hangboard-collection/metolius-simulator-3d/source-delivery/Metolius-Simulator-3D.glb`,
SHA-256 `1f71e8673d0682f27398d260a8320ae054b75a3d023436aa896549eeed22297a`.
Its explicit scene inventory is one `board_body` mesh and 31 contact meshes.
Every mesh has the supplied usable `Simulator_Clay_Image` image material.

The rendered source review identified eight visible mounting-hardware openings.
The display-model contract excludes mounting hardware, so a directly authored
native correction adds eight nonselectable body caps. The importer and compiler
remain transport-only: they do not create, repair, or infer this geometry.

| Artifact | SHA-256 | Disposition |
| --- | --- | --- |
| Native transport source before correction | `732be4c9ce2c58162ad40484268217db61ce97db2959256395119565ab982a49` | Preserves supplied topology; not promoted because the visible hardware openings violate the model-only display contract. |
| Corrected native source | `ab2d71965fc851bca6c1678dbac7d02d4bda73eba482690eae6e75ced6247b45` | Adds a second nonselectable body mesh, `mounting-hardware-omission-caps`, with eight direct display-only caps. Their reviewed source-frame locations/radius are recorded in `author_hardware_free_source.py` as display estimates, not physical mounting facts. |
| Promoted `assets/primary.usdz` | `3372f4d2b42a967d3ca65c2d1a0f56bd7762b32f9c1a80f79897841b020fbc94` | Exact shipped USDZ, cleanly reimported from an empty scene. |
| Promoted descriptor | `5d28f9ff8c33e7a2ae1a6cef472537fa4e26efdd208253ecb1758dae1ea33812` | Hash-binds the unchanged shipped USDZ and records the corrected #2/#3 contact ownership. |

`contact-mapping.json` preserves catalog contact order exactly. Source
`hold_01_left/right`, `hold_04`–`hold_13_left/right`, and
`hold_14`–`hold_18_center` bind one-to-one to their identically numbered
stable contacts. `hold_02_left` and `hold_02_right` bind the two factual #2
flat zones; `hold_03_left` and `hold_03_right` jointly bind the one factual #3
central round zone. Thus 31 selectable mesh pieces bind exactly 30 logical
contacts. `board_body` and
`mounting-hardware-omission-caps` are the only two body nodes and never carry a
contact identity.

The exact shipped asset verifier starts with an empty Blender scene and checks
the descriptor's USDZ hash, importer-visible triangulated image materials,
all 33 node bindings, two body nodes, 31 contact mesh bindings, and the exact
30-contact descriptor keyset. Its retained report is
`.context/lumpy-liger-hangboard-collection/metolius-simulator-3d/shipped-usdz-verification.json`.
The package root contains only `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`; its prior raster asset and canonical paths are
removed.

## Metolius Contact (`metolius.contact`)

Reviewed 2026-09-15. The catalog `Hangboards/metolius-contact/board.json` is
the sole authority for the existing revision identity, 33 `contacts[].id`
values, names, kinds, capacity/depth facts, and product metadata. No factual
catalog fields were changed during this conversion.

### Retained visual evidence

| ID | Publisher and URL | Retained local copy and SHA-256 | Supports | Does not support |
| --- | --- | --- | --- | --- |
| MC-PHOTO | Metolius — [product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Contact-Hangboard-black-white.jpg?v=1759459002) | `.context/lumpy-liger-hangboard-collection/metolius-contact/retained-evidence/metolius-contact-product.jpg` — `b9cf153d82f0072ae2e4b0064821dee1d666ff1d8b34ba21fed1fcfd6944c055` | Exact Contact silhouette, molded relief, contact arrangement, and mounting-opening existence. | Measured fillets, rear geometry, bore centers/radii/countersinks, or contact depth beyond published labeling. |
| MC-DIAGRAM | Metolius — [numbered hold diagram](https://www.metoliusclimbing.com/cdn/shop/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170) | `.context/lumpy-liger-hangboard-collection/metolius-contact/retained-evidence/metolius-contact-numbered-hold-diagram.jpg` — `6c824af42552a9ed12f7e336dac47d9a2c61441b6f90515d196f3484ad0a1202` | Positions 1–14 on each side, center positions 15–19, published pocket capacities/depths, center-edge depths, and the 63/53 mm sloper labels. | Sloper curvature radii or recess depths. |

The Metolius [product page](https://www.metoliusclimbing.com/products/contact-training-board)
was also reviewed for the exact Contact identity and published 826 × 279 × 67
mm metric envelope. These manufacturer sources are the two materially distinct
exact-revision visuals retained before promotion. They are evidence only; no
source pixels, image tracing, or positional inference was used for contact
binding or source correction.

### Audited source and corrective ruling

The supplied user-provided source GLB is
`~/Downloads/hangboard-collection/models/metolius-contact/metolius-contact.glb`,
SHA-256 `3da9c625144aec6686c2a99438b91325278cc81e855a2f68e920c72fcdaad93c`.
It explicitly contains 33 contact meshes plus a body, but its own validation
record and ten direct bore-center ray checks confirm ten open mounting-bore
tunnels. Such openings cannot be promoted into a display model.

The approved display-only correction was directly authored in the
workspace-owned native source, not by the exporter/compiler:

| Artifact | SHA-256 | Ruling |
| --- | --- | --- |
| Native reconstruction before correction | `e5982601281eebbc41f3762f92522fcd0109f1f42329bf18af1ab3b9afd92395` | Reproduces the delivered GLB topology, including all ten open bore rays; not promotable. |
| Native source after correction | `f47ad193e87b40db8213252d45252d84a1784ec278ae3180f5e631fa72ecead5` | Removes the ten bore tunnel surfaces and adds 20 nonselectable body caps. Eight bores use their audited source boundary loops. The two perimeter-connected mouths use deliberately authored planar nonselectable body caps at recorded display estimates (`y=-0.0551 m` and `-0.0550 m`, radius `0.0041 m`). These are hardware omissions, not physical bore facts. |
| Promoted `assets/primary.usdz` | `b944c78e1621bb0fece926e2f8d45608c2d391c6311e8557010ad153b8bcaa59` | Deterministic compiler export/reimport from the corrected source. |
| Promoted descriptor | `2ada55e49a8fe951aed6205cd0e5a206af98b1d4f684ace0ba1b4177aec9ff41` | Generated from importer-visible USDZ triangles; model SHA is hash-bound. |

The source correction report, pre-correction failure, post-correction ray
check, loop diagnostic, source manifest, explicit mapping, compiler output,
and import report are retained under
`.context/lumpy-liger-hangboard-collection/metolius-contact/`. The correction
does not add, remove, rename, or bind a catalog contact differently.

### Explicit binding audit

`contact-mapping.json` lists every source node and is ordered exactly as the
catalog contact inventory. Each of the 33 reviewed source mesh names maps to
the same-named catalog contact ID: the two pinches, two jugs, both round
slopers, center flat sloper, all pockets 4–14 left/right, and center edges
16–19. `body` and `bore-free-body-caps` are explicit `body` nodes with no
contact identity, so mounting-bore corrective surfaces are never selectable.
The imported descriptor contains 35 nodes, 33 contact mappings, and exactly
the catalog's 33-contact keyset.

### Verification

`Tools/HangboardModels/import_contact_model_source.py` compiled the corrected
blend through the explicit manifest/mapping, exported the USDZ, reopened it in
an empty Blender scene, checked triangulated importer-visible material-bearing
nodes, preserved bindings and bounds, and generated the hash-bound descriptor.
The actual corrected source passes all ten bore-center ray intersections. On
2026-09-15, `verify_promoted_usdz.py` also imported the exact shipped
`Hangboards/metolius-contact/assets/primary.usdz` from an empty Blender scene
after verifying SHA-256
`b944c78e1621bb0fece926e2f8d45608c2d391c6311e8557010ad153b8bcaa59`
against both the expected promotion hash and the shipped descriptor. Its
retained `shipped-usdz-bore-validation.json` records all ten center rays as
intersecting the imported nonselectable `bore_free_body_caps_001` node; it does
not inspect a compiler staging asset or source blend.
`scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
and `status --root Hangboards` passed after promotion. The package has exactly
`board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; it has no
raster asset, canonical path, or fallback geometry.

## Metolius Climber's Edge (`metolius.climbers-edge`)

Reviewed 2026-09-15. `Hangboards/metolius-climbers-edge/board.json` remains
the authority for the current redesigned Climber's Edge identity and its
existing 15-contact inventory, names, kinds, depth facts, and product metadata.
No catalog contact or factual field was added, removed, renamed, or edited.

### Retained visual evidence

| ID | Publisher and URL | Retained local copy and SHA-256 | Supports | Does not support |
| --- | --- | --- | --- | --- |
| CE-DIAGRAM | Metolius — [dimension/hold diagram](https://www.metoliusclimbing.com/cdn/shop/files/Climber_s-Edge-Spec.jpg?v=1765309719) | `.context/lumpy-liger-hangboard-collection/metolius-climbers-edge/retained-evidence/climbers-edge-spec.jpg` — `a96263a9b46e148ddc6817f5173494c871e38871d7c02c6b8ce5ba1e98ee38c8` | Exact 600 × 160 mm revision envelope, 15-contact layout, six edge depths, two jugs, two flat slopers, central round sloper, and mounting-opening existence. | Body thickness, bore centers/radii/countersinks, rear construction, or local curvature. |
| CE-PHOTO | Metolius — [product photograph](https://www.metoliusclimbing.com/cdn/shop/files/The-Climber_s-Edge-Training-Board_67ebe212-d205-4f2c-9ca9-048b1792351d.jpg?v=1765309719) | `.context/lumpy-liger-hangboard-collection/metolius-climbers-edge/retained-evidence/climbers-edge-product.jpg` — `f77709e5ef37fea421bdf08cd85b6fa88709da76e4ea3a861a3a4e2c673ae3ed` | Exact revision’s oblique silhouette, open-ended sculpted tiers, tapered ends, top-contact arrangement, and wood appearance. | A scan, exact bore dimensions/locations, hidden geometry, or machining sections. |

The user-supplied download’s source register is retained at
`.context/lumpy-liger-hangboard-collection/metolius-climbers-edge/retained-evidence/source-register.json`
(SHA-256 `af2b1588b0325826fea5e60f12284c4b5705512ad485380aa76588ebfd375b68`).
The product page was also reviewed for identity and the documented 20-degree
flat slopers and 40 mm-radius round sloper. These sources establish factual
identity only. No source pixels, image tracing, positional inference, or
visual auto-geometry process was used in the mapping or correction.

### Audited source and approved corrective ruling

The supplied user-provided source GLB is
`~/Downloads/hangboard-collection/models/metolius-climbers-edge/metolius-climbers-edge.glb`,
SHA-256 `32f9b1d0c851536b61ca8d900b8d8488ebc2f707844598741f75793537271bb1`
(7,885,360 bytes). The retained delivery structural record declares 16 mesh
nodes—one `body` plus the 15 mapped contacts—and confirms eight open authored
mounting bores. Those unsupported hardware openings are body topology, not
standalone source nodes.

The user expressly authorized a narrow pre-export correction. The importer and
compiler remain transport-only. The correction was authored directly in the
workspace-owned native source as follows:

| Artifact | SHA-256 | Ruling |
| --- | --- | --- |
| Supplied GLB | `32f9b1d0c851536b61ca8d900b8d8488ebc2f707844598741f75793537271bb1` | Contains eight open body bore rays; not promoted. |
| Corrected native source | `d7d052a716e25b2f4348882f265ec8c33fdf87db06d5ef9296011ca33fdcd4d8` | Deletes 1,239 body-only bore/countersink triangles and adds 16 nonselectable planar body caps. Every cap uses the supplied authored bore center/countersink radius and the exact exterior mouth plane read from the deleted source faces; no planar cap estimate was introduced. |
| Promoted `assets/primary.usdz` | `b17ea53a25d2050ab1424748ceab10fb7da0ba15faddcede8ec39c256b9c5fe3` | Deterministic transport/export/reimport from the corrected source. |
| Promoted descriptor | `d2805c4735239508e6bf9b3b146cc06a3f4d0ace22130e8c79013cb2716d0952` | Generated from importer-visible USDZ triangles and hash-binds the promoted USDZ. |

The supplied GLB expands to unwelded triangles on native import, so source
boundary loops cannot be relied upon as a closed-loop authoring interface. The
correction therefore uses only the retained source’s explicit bore records and
the selected source faces’ exterior planes: front `0 m`, with rear mouth planes
`-0.041 m` for bores 1–3, `-0.047 m` for bores 4–5, and `-0.055 m` for bores
6–8. These are source-derived display geometry values, not new product facts
or positional estimates. The 15 contact meshes retain their exact supplied
triangle counts. Records, pre-correction failure, corrected-source check,
mapping, manifest, compiler report, and shipped-USDZ check are retained under
`.context/lumpy-liger-hangboard-collection/metolius-climbers-edge/`.

### Explicit binding and shipped-asset verification

`contact-mapping.json` is ordered exactly as the board’s existing 15 contact
IDs. Each named source contact maps identically to its catalog ID. `body` and
`bore-free-body-caps` are the only nonselectable `body` nodes; neither has a
contact identity. The compiler cleanly reimported the USDZ from an empty scene,
producing 17 importer-visible mesh nodes, 15 contact bindings, and a descriptor
whose contact keyset exactly equals the catalog inventory.

`verify_promoted_usdz.py` verified the exact shipped USDZ hash against both
the expected promotion hash and the shipped descriptor, then imported that
shipping asset into an empty Blender scene. Its retained
`shipped-usdz-bore-validation.json` records all eight audited bore-center rays
intersecting the nonselectable `bore_free_body_caps_001` node. It does not
inspect an intermediate source or staging asset. The promoted package contains
only `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; it
has no raster media, canonical path, or fallback geometry.

P1 follow-up: `Tools/HangboardModels/verify_metolius_climbers_edge.py` is the
committed reproducible shipped-asset verifier. It starts from an empty Blender
scene, hash-checks the descriptor-bound shipped USDZ, imports that exact asset,
rebuilds the descriptor from the imported material-bearing triangles, and
requires exact equality with the shipped descriptor plus all eight rays to
hit exactly `bore_free_body_caps_001`. Its
Blender-free contract test is `test_verify_metolius_climbers_edge.py`.

The fixed front presentation uses a 3.75 display aspect ratio from its imported
0.600000024 × 0.159999996 m front bounds, replacing the former raster ratio.
The runtime fits both projected dimensions within that viewport; this layout
estimate does not change the model geometry or source-backed dimensions.

## The Hangboard (`the-hangboard.the-hangboard`)

Reviewed 2026-09-15. `Hangboards/the-hangboard/board.json` remains the source
of truth for the current The Hangboard revision and for every existing contact
ID, name, kind, depth, capacity, grip type, product fact, and presentation
identity. The conversion makes no contact or factual catalog edit.

### Retained visual evidence

| ID | Publisher and URL | Retained local copy and SHA-256 | Supports | Does not support |
| --- | --- | --- | --- | --- |
| TH-FRONT | The Hangboard — [official straight-on product image](https://cdn.shopify.com/s/files/1/0764/5210/2426/files/hangboard-straight-2.png) | `.context/lumpy-liger-hangboard-collection/the-hangboard/retained-evidence/hangboard-straight.png` — `4db9e95721bd43cf6df3ee5974865948c9353f2f366c4f2957b08206442122d3` | Exact front layout: two outer deep jugs, one continuous center sloper, four routed edge channels, and three separate edge contacts in each channel. | Hidden geometry, local section measurements, or mounting-hole measurements. |
| TH-OBLIQUE | The Hangboard — [official right oblique gallery image](https://thehangboard.com/cdn/shop/files/half-right-hangboard.png?v=1747623739) | `.context/lumpy-liger-hangboard-collection/the-hangboard/retained-evidence/hangboard-oblique-right.png` — `128efa32244f2d0a20a70c468f483c135baec8797e88e8cc3732f88111eaf147` | Routed edge-floor relief, separation between adjacent edges, top relief, and the existence of mounting hardware. | A scan, exact hardware geometry, rear geometry, or unsourced contact dimensions. |

The manufacturer [product page](https://thehangboard.com/products/hangboard)
and [landing page](https://thehangboard.com/) were retained as the existing
catalog authority for the exact product name, six labeled edge depths, deep
jugs, 40-degree sloper, and 23.5 × 6.25 × 2 in envelope. The retained visuals
were reviewed only to confirm the exact physical revision and existing
inventory; no pixels were traced, registered, segmented, or used to infer a
contact binding or product fact.

### Audited source and narrow corrective ruling

The user-provided source is
`~/Downloads/hangboard-collection/models/the-hangboard/the-hangboard.glb`,
retained under `.context/lumpy-liger-hangboard-collection/the-hangboard/`,
SHA-256 `dadfa6978129e01f57384deb606fb654c8787045dedf292f4a3daaa8a48d8c31`.
It has one `body` mesh and 15 source-named contact meshes. Its rendered front
review exposes two rows of four visible mounting-hardware recesses. Mounting
hardware is excluded by the display-model contract, so the approved correction
adds eight direct-authored, nonselectable plain body caps at reviewed source
frame display estimates. The cap locations and 4.1 mm radius are not physical
product facts or contact measurements. All 15 contact-mesh triangle counts are
unchanged.

| Artifact | SHA-256 | Disposition |
| --- | --- | --- |
| Supplied GLB | `dadfa6978129e01f57384deb606fb654c8787045dedf292f4a3daaa8a48d8c31` | User-provided source delivery; not promoted because visible mounting hardware is outside the model contract. |
| Corrected native source | `ed5ca990784e8afc47dd6ecaeea08dc93b99d05a1da49ea74e5d541407efdf1d` | Adds only eight nonselectable `mounting-hardware-omission-caps` body faces over the reviewed recesses. |
| Promoted `assets/primary.usdz` | `212a6353427244fd881c66f7cbc456b1e91a108b50a132730fe8e6dbdb4f4d4f` | Deterministic transport/export and clean USDZ reimport. |
| Promoted descriptor | `a106a3710d354244a73664fc95faac0db5fe9700b0b46482a4d49c2c328b36a8` | Generated from importer-visible USDZ triangles and hash-binds the shipped model. |

### Explicit contact binding and exact-shipped validation

`contact-mapping.json` lists the catalog contact inventory in its original
order. Each supplied source contact is one-to-one with the same stable contact
ID: `jug-left`, `jug-right`, `sloper-40-center`, each upper 40/30/25 mm left
and right edge, and each lower 20/15/10 mm left and right edge. `body` and
`mounting-hardware-omission-caps` are the only nonselectable body nodes. The
center sloper is exactly one source mesh bound only to `sloper-40-center`; no
left/right sloper was invented. Likewise, every bilateral edge remains a
separate source mesh and separate existing logical ID.

`Tools/HangboardModels/verify_the_hangboard.py` hash-checks the actual shipped
asset, imports it from an empty Blender scene, rebuilds the descriptor from
importer-visible triangulated material-bearing meshes, requires the exact
15-contact keyset and 17-node descriptor, and confirms all eight reviewed
hardware-cover rays hit only `mounting_hardware_omission_caps_001`. Its report
is `.context/lumpy-liger-hangboard-collection/the-hangboard/shipped-usdz-verification.json`.
The model-only package contains only `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`; its raster media, canonical paths, and fallback
geometry are removed. `test_verify_the_hangboard.py` locks the ordered
15-contact inventory and rejects a hardware-cover ray that resolves to the
body rather than the cap node.

## Trango Rock Prodigy Training Center (`trango.rock-prodigy-training-center`)

Reviewed 2026-09-15. This migration is limited to the exact Training Center revision documented in `2026-08-12-rock-prodigy-board-package.md`. Its existing `board.json` remains the sole authority for its revision identity, 24 stable contact IDs, ordering, names, kinds, optional facts, and product metadata. No Forge, Natural, or Pivot claim, contact map, dimension, or model detail was used as a substitute; those are separate Trango revisions.

### Retained visual evidence

| ID | Publisher and URL | Retained local copy and SHA-256 | Supports | Does not support |
| --- | --- | --- | --- | --- |
| RPTC-FRONT | Trango — [official Training Center main image](https://trango.com/cdn/shop/files/22830_Rock_Prodigy_Training_Center_Main_Image.jpg?v=1737728750&width=1946) | `.context/lumpy-liger-hangboard-collection/trango-rock-prodigy-training-center/retained-evidence/trango-training-center-main.jpg` — `8293f7bd2c2517f8fda72d7ad678671cc801cd7d31fecd4e20ee42eea7170ebf` | Exact two-piece Training Center revision, bilateral presentation, visible contact arrangement, and exterior silhouette. | Per-contact depths/capacities, hidden geometry, or a Forge/Natural/Pivot equivalence. |
| RPTC-GUIDE | Trango — [official Training Center use instructions](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) | `.context/lumpy-liger-hangboard-collection/trango-rock-prodigy-training-center/retained-evidence/rptc-use-instructions.pdf` — `9800be405e9aa58fd8d9bd1fefbf9ac5bcd738baaa344c6af084fbf98a44465c` | Training Center identity and broad jug, edge, pocket, pinch, and sloper grip families. | A one-to-one cavity/rail map, individual pocket capacity/depth, or any fact for a different Rock Prodigy revision. |

The existing Trango product page and audit establish the Training Center's two-piece symmetric construction and source-limited contact interpretation. These files were reviewed to preserve that existing inventory, not to trace, register, segment, or infer new model geometry.

### Source decision and explicit mapping

The user-provided source delivery is retained at `.context/lumpy-liger-hangboard-collection/trango-rock-prodigy-training-center/source-delivery/trango-rock-prodigy-training-center.glb`, SHA-256 `59bb4bc1d1930b2fa14266d5f17e67859815912e2decab15dd1861c07f452c57`. It has two nonselectable body meshes and 22 named selectable meshes. Every corrected source node is explicitly recorded in `contact-mapping.json`; its ordered logical IDs exactly equal the catalog’s current ordered 24 IDs.

The initial transport correction duplicated each `pinch-combination-*` mesh
under two linked nodes. Final review rejected that export: separate node names
over identical surfaces do not provide independent nearest-hit selection.
That source (`44f578442c2b80e05e4c790d81b99790defdf147ea7e5a1b3ab13f7faedf5ac5`)
is superseded by the disjoint source below.

The corrected source assigns every original pinch triangle exactly once. On
each side the lower ledge binds `pinch-medium-*` and the upper projecting block
binds `pinch-wide-*`. RPTC-FRONT supports the visible two-tier shape; RPTC-GUIDE
supports the pinch family. Neither source locates the legacy medium/wide names.
Consequently this assignment is explicitly an authored **display binding
estimate**, not a manufacturer positional mapping or width measurement. The
existing names, IDs, kinds, and empty optional factual fields remain unchanged.

`prepare_native_source.py` retains all original triangles, coordinates, UVs,
materials, and their combined shape. An operator-selected source-coordinate
boundary through the recessed step riser uses
`0.3564 * abs(x) + 0.93434 * z < 0.137` for the lower region; the remainder
binds the upper region. The coefficients and boundary are display selection
parameters, not measured product facts. The mirrored assignments contain
3,613 lower and 5,087 upper triangles per side, partitioning the original 8,700
without duplication. No tracing, generated contour, geometry simplification,
or compiler repair is involved. The corrected native source SHA-256 is
`a07855a4d81dd05e9dd849b7001e12c6b059acbac3e93320b7b3e24679c2055e`.

The explicit mapping preserves two independent body nodes; two jugs; each bilateral variable rail and thin crimp; all ten bilateral pocket identities; both bilateral slopers; and all four bilateral pinch identities. In particular, `pinch-medium-left`, `pinch-wide-left`, `pinch-medium-right`, and `pinch-wide-right` are never merged. Delivery source names are transport labels only; the pre-existing catalog IDs and facts remain the factual identity source.

### Promoted model-only package and exact shipped validation

| Artifact | SHA-256 | Disposition |
| --- | --- | --- |
| Promoted `assets/primary.usdz` | `f56c6da3e001f445810dfeaa3afd69e658d3c19780664952980a28ac4b5992c1` | Exact shipped model generated through the explicit importer/compiler and reopened from an empty Blender scene. |
| Promoted descriptor | `45b51d0390a71c0f21540dd6e682e5aa2afa15bc6e234c67edc2ffdd7c931073` | Generated from importer-visible USDZ triangles and hash-binds the shipped model. |

`Tools/HangboardModels/verify_trango_rock_prodigy_training_center.py` checks the exact shipped package inventory and model hash, starts with an empty Blender scene, imports the shipped USDZ, validates 26 tagged nodes (two body, 24 contact), rebuilds the descriptor from material-bearing triangulated meshes, and requires the exact 24-contact keyset plus four distinct bilateral-pinch bindings. Its retained report is `.context/lumpy-liger-hangboard-collection/trango-rock-prodigy-training-center/shipped-usdz-verification.json`. The package contains only `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; the raster asset, canonical paths, cached frames, and fallback geometry are removed.

## Task 7 final validation attempt — BLOCKED by the host iOS toolchain

Reviewed 2026-09-15 in workspace `lumpy-liger`. This record makes no package
or source-fact change. The six-package final inventory and retained
model/package suites passed, but isolated Simulator review and focused XCTest
execution could not start because the host CoreSimulator framework is
incompatible with Xcode. No app-code correction was made.

| Command | Result |
| --- | --- |
| `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` | Passed; valid final inventory, no drafts. |
| `rtk scripts/hangboard-packages.sh status --root Hangboards` | Passed; `drafts: []`. |
| `rtk Tools/HangboardPackages/.venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_descriptor.py Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py Tools/HangboardModels/test_verify_metolius_climbers_edge.py Tools/HangboardModels/test_verify_the_hangboard.py Tools/HangboardModels/test_verify_trango_rock_prodigy_training_center.py -q` | 12 passed. |
| `rtk Tools/HangboardPackages/.venv/bin/python -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_trango_rock_prodigy_training_center_board_package.py -q` | 119 passed. |

Current SHA-256 reads, including the final Training Center pinch correction, are retained in
`.context/lumpy-liger-hangboard-collection/final-validation.json`; the passing
model-first/package suites check that each USDZ is descriptor-bound.

| Package | USDZ SHA-256 | Descriptor SHA-256 |
| --- | --- | --- |
| `metolius.climbers-edge` | `b17ea53a25d2050ab1424748ceab10fb7da0ba15faddcede8ec39c256b9c5fe3` | `d2805c4735239508e6bf9b3b146cc06a3f4d0ace22130e8c79013cb2716d0952` |
| `metolius.contact` | `b944c78e1621bb0fece926e2f8d45608c2d391c6311e8557010ad153b8bcaa59` | `2ada55e49a8fe951aed6205cd0e5a206af98b1d4f684ace0ba1b4177aec9ff41` |
| `metolius.simulator-3d` | `3372f4d2b42a967d3ca65c2d1a0f56bd7762b32f9c1a80f79897841b020fbc94` | `783e0a0e808a31d8f4d11c69c15477e6ef70c93eed2da9c195639ef014b302ee` |
| `soill.training-tiles` | `4cb007105f5c70d57e739c884964d130f6ccf524d4c4adb974892bda4f670ebf` | `fa3e18d155a9ba3f808fef2ce9c1c4e6a076cd141f1d842440cf6dcb192395b8` |
| `the-hangboard.the-hangboard` | `212a6353427244fd881c66f7cbc456b1e91a108b50a132730fe8e6dbdb4f4d4f` | `a106a3710d354244a73664fc95faac0db5fe9700b0b46482a4d49c2c328b36a8` |
| `trango.rock-prodigy-training-center` | `f56c6da3e001f445810dfeaa3afd69e658d3c19780664952980a28ac4b5992c1` | `45b51d0390a71c0f21540dd6e682e5aa2afa15bc6e234c67edc2ffdd7c931073` |

### Simulator/XCTest blocker and omissions

Sandbox simulator discovery reported a disconnected `CoreSimulatorService`.
Host-context `simctl` discovery and XcodeBuildMCP simulator listing did not
yield a usable runtime/device. The compile-only attempt was:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData CODE_SIGNING_ALLOWED=NO build-for-testing
```

It identified the root cause: Xcode 27.0 (`27A266a`) requires CoreSimulator
build `1171.7.0`, but macOS 26.6.2 (`25G83`) supplies `1051.55.0`.
`DVTCoreDeviceCore` also failed to load the required
`CoreDevice.DetailedOperation.metrics` symbol, and Xcode reported `Simulator
device support disabled`. Build-for-testing produced a runner but no owned UUID
existed, so focused `BoardModelTests`/`BoardPackageStoreTests` were not
launched.

No simulator was created, booted, installed, or launched; no pending/owned
manifest record and no screenshot exists. Thus all six normal and
selected-contact states, picking alignment, model-unavailable behavior,
landscape review, and HealthKit permission flow remain unperformed. The
physical-device HealthKit limitations in `docs/IOS_RUNTIME_SERVICES.md` also
remain outside this attempt.

### Cleanup

The exact workspace-owned `.context/DerivedData`, raw/landscape screenshot
paths, and temporary discovery files were removed. Archive cleanup ran with
`PASEO_WORKTREE_PATH` set to this workspace; both owned and pending simulator
manifests were absent afterward, as expected because creation never succeeded.
No shared or unknown simulator was addressed. Re-run the simulator and focused
XCTest portions after installing a CoreSimulator version compatible with Xcode
27.0, then obtain the plan's final broad review.

### Resumed isolated simulator validation — BLOCKED on ODR provisioning

CoreSimulator became available later on 2026-09-15. An exact owned device,
`Hang Ten Paseo lumpy-liger Review`
(`87B3E8DF-B73E-4CDF-A0A3-5629F356F69B`), was created, written first to the
pending and then to the owned manifest, booted, built with that exact
destination, installed, and deleted through archive cleanup. No existing
simulator was addressed.

`xcodebuild ... test -only-testing:HangTenTests/BoardModelTests
-only-testing:HangTenTests/BoardPackageStoreTests` on that UUID passed: 177
tests, 0 failures (45 BoardModelTests and 132 BoardPackageStoreTests). Each of
the six DEBUG board-detail routes exposed the expected board-specific hold
legend; selecting the documented contact updated its selected-hold card. Normal
and selected screenshots were captured and visually inspected for Climber's
Edge/left jug, Contact/left pinch, Simulator 3-D/left #1 jug, Training
Tiles/outer-left upper sloper, The Hangboard/left jug, and Training
Center/left jug. Their hashes and paths are retained in the final-validation
JSON; all temporary PNGs were deleted after review.

The visual result is consistently the intended fail-closed unavailable state,
not a rendered model: each screenshot says `3D model unavailable`. The device
log identifies the common cause for all six: `NSBundleResourceRequest` fails
with `NSCocoaErrorDomain` 4994, `The requested application data doesn’t
exist`, for the exact `hang-ten-model-<board>` tag. An Xcode-managed
build/install/relaunch produced the same result. This prevents validating
normal 3D geometry, highlight alignment, or SceneKit picking; selected hold
legend controls remain functional but are not model picking evidence. This is
reported as a runtime packaging/provisioning blocker with no code change.

Archive cleanup removed the exact UUID; the emptied owned/pending manifests,
workspace Derived Data, and all temporary screenshots were removed and the
UUID no longer appears in `simctl list devices`.

### ODR-fix retry — six-board rendering and selection states passed

After `9342db1cc` corrected the ODR provisioning, an independently owned
`Hang Ten Paseo lumpy-liger Review` simulator
(`AE29B039-BAA0-413B-89D4-C9EED2842834`, iPhone 16 / iOS 26.5) was recorded in
the pending manifest before the owned manifest, booted to launch-service
readiness, clean-built with its exact destination and workspace-local Derived
Data, then installed by explicit UUID. `xcodebuild ... test
-only-testing:HangTenTests/BoardModelTests
-only-testing:HangTenTests/BoardPackageStoreTests` passed all 177 tests (45
model and 132 package tests; zero failures).

Each DEBUG `HANGTEN_REVIEW_BOARD_DETAIL=1` + `HANGTEN_REVIEW_BOARD_ID` route
rendered its model and initial highlighted hold. The retained selected-state
accessibility snapshots show matching `boardModel.contact.<id>` and
`boardDetail.selectedHold.<id>` IDs, and the reviewed selected PNGs show the
corresponding red model highlight. This records the model-linked selection end
state; it is not a raw `SCNView.hitTest` event log or independent proof of
triangle-picking input. These were the reviewed normal/selected pairs:

| Board | Selected model contact |
| --- | --- |
| Climber's Edge | `flat-sloper-left` |
| Contact | `jug-left` |
| Simulator 3-D | `round-sloper-3-center` |
| Training Tiles | `upper-sloper-outer-right` |
| The Hangboard | `edge-40-left` |
| Rock Prodigy Training Center | `pinch-medium-left` |

The 12 reviewed PNGs, their accessibility snapshots, signed-build log, test
log, installed-container path, and durable
[`visual-sha256.txt`](../../.context/lumpy-liger-hangboard-collection/odr-retry/visual-sha256.txt)
inventory are retained only under `.context/lumpy-liger-hangboard-collection/odr-retry/`.
No snapshot exposed `boardModel.unavailable` or `3D model unavailable`.
Training Tiles required a ten-second initial SceneKit paint wait before its
normal capture; the subsequent rendered normal state and a distinct
right-upper-sloper selection were both reviewed. This is simulator integration
evidence, not physical-device PBR or HealthKit permission validation.

The registered archive trap then deleted only UUID
`AE29B039-BAA0-413B-89D4-C9EED2842834`; the retained
[`post-cleanup status`](../../.context/lumpy-liger-hangboard-collection/odr-retry/post-cleanup-status.md)
records the no-match UUID query, an absent pending manifest, a zero-byte owned
manifest, and an absent workspace-local DerivedData path. The retained review
evidence is the only output left by this retry.

### Final review corrections and direct picking evidence

The final review replaces the Training Center's coincident pinch meshes with
the disjoint original-triangle partition documented above. Its shipped USDZ
verifier now rejects shared medium/wide triangles even when node IDs differ;
the four imported meshes contain 3,613/5,087 lower/upper triangles per side.
Only the four pinch bounds/bindings and the model hash changed in its
descriptor. All non-media catalog fields and all other contacts are unchanged.

`testCollectionModelsNativeNearestTrianglePickingCoversEveryContactPiece`
loads each actual shipped model through the normal loader. For every one of
the six boards' 136 logical contacts / 138 mesh pieces, it finds at least one
native triangle-center sample, across nine bounded camera angles, whose
nearest SceneKit segment hit and projected `SCNView.hitTest` both return that
**exact mesh node** and contact ID. The same helper also strengthens the
existing Baguette test. This demonstrates a reachable pick for each piece,
not correctness at every pixel or every camera angle. Body and attachment
nodes retain the production non-pickable category.

Simulator `Hang Ten Paseo lumpy-liger Review`
(`F6161489-348C-442B-A3B1-629AFB45FF08`, iPhone 16 / iOS 26.5) built and ran
the corrected asset. Direct coordinate taps in its 393 × 852 point portrait
screen selected the four separate pinch regions:

| Tap point | Observed selected ID | Reviewed PNG SHA-256 |
| --- | --- | --- |
| `(62, 311)` | `pinch-wide-left` | `d1c2d7db8e18ca446b719f97857f1676c6c8ccd4169941d81c5d7e0b6669a1e8` |
| `(66, 329)` | `pinch-medium-left` | `1e1c95742f4cd09b9c62755aceee6f91eaac30d61eeac869cfdd8f7b733b2419` |
| `(333, 308)` | `pinch-wide-right` | `d45ba8280eaab8875cd280e6e11c38503a6db197b08aa4f18382ef6de282c46f` |
| `(329, 329)` | `pinch-medium-right` | `06af9089ea191dbe3a43bd74c0a8e80f952d38046090960f19a04da680d40aca` |

Each screenshot shows only its corresponding upper block or lower ledge
highlighted red, with the selected-hold label matching the tapped region.
The initial left-jug state was also reviewed (PNG SHA-256
`54a3d67c89e0e061656c22642d09ef6bb93ad3183944dccf82e5012b4e6aad9f`).
PNGs and accessibility trees are retained under
`.context/lumpy-liger-hangboard-collection/final-review/`. These are actual
screen-coordinate taps, with the XCTest hits independently covering all six
models. No physical-device material or HealthKit claim is made.

Migration-specific stale tests now use the twenty-package model inventory,
model descriptor bounds and node ownership for converted mirrored pairs, the
retained verifier inventory, and Training Tiles' model-only fixture. The
Simulator source mesh has submillimeter bilateral tessellation differences:
its maximum mirrored X-bound difference is approximately 0.43 mm, so that
model uses an explicit 0.5 mm bounds tolerance; raster paths retain their
exact-mirror assertions. The other converted model pair uses a normalized
`1e-6` tolerance. The final package/model Python suite passes all 609 tests;
focused iOS model/package validation passes all 178 tests.

The complete iOS unit suite then passed: 1,136 tests executed, two existing
skips, zero failures. Exact command:

```sh
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=F6161489-348C-442B-A3B1-629AFB45FF08' \
  -derivedDataPath .context/DerivedData test -only-testing:HangTenTests
```

Its log is `final-review/full-ios-final.log`. The initial full run identified
the same old model inventory in `BoardSourceBoundaryTests`; adding the six
migrated IDs fixed all six assertions. The complete final suite includes the
exact-node picking assertions. Package final-inventory validation and status
both pass with no drafts, and `git diff --check d7ca9c5c9` passes.

The ownership trap deleted the exact simulator UUID and consumed its pending
record; the owned manifest is empty. The earlier failed full-test process
remained alive after reporting its results, so its exact verified PID was
terminated before removing its late-created test-log manifest. Final checks
confirm no owned simulator, pending record, DerivedData, or temporary raw/
landscape screenshots remain. Only the workspace-owned review evidence is
retained. No shared simulator or global build cache was touched.
