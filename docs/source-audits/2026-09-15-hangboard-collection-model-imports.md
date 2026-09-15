# Hangboard Collection model imports

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
