# Nature Climbing Stone Hanger — Granite

Editable, evidence-constrained display asset for independent hold highlighting.

**Revision identification:** updated standard natural-oak / Granite product in the manufacturer's gallery accessed **2026-09-11**. Manufacturer SKU `STONE_HANGER`; Shopify product `8768741048658`; non-personalized Granite variant `47783638597970`. No numbered revision or precise production change date is published. `current-gallery-2026-09-11` is this project's snapshot key, not a manufacturer revision number. The older 23 mm Stone Hanger and Stone Hanger Mini are excluded.

**Fidelity limits:** overall dimensions and nominal edge depths are published. The fine machining dimensions below are visual approximations. Unknown internal cord routing is not reconstructed. Branding is omitted because no redistribution license for the artwork was established. This is a display model, not an exact manufacturing reconstruction.

**One requested deliverable is blocked:** no real Blender Outliner screenshot could be captured. The runtime denied local display sockets, and its approval policy rejected the request to start a virtual display. `scripts/outliner_view.py` prepares a real GUI view when run in desktop Blender. The mesh inventory and selection proof are provided separately and are not represented as screenshots.

## Included files

- `Nature-Climbing-Stone-Hanger.blend`: clean, editable source scene, Blender **4.0.2**.
- `Nature-Climbing-Stone-Hanger.glb`: additional embedded-texture runtime export.
- `integration.json`: complete object, hold and passage mapping.
- `textures/` and `texture-manifest.md`: two original 1K base-color textures; also packed into the Blender file.
- `renders/`: five labeled views of the actual mesh under neutral studio lighting.
- `evidence/`: retained source images, original product metadata, page snapshots, URL indexes and source assessments.
- `qa/`: independent validation results and hold selection proof.
- `scripts/`: editable model generator, texture generator, validation and desktop Outliner view setup.

## Published specification

| Field | Manufacturer information |
|---|---|
| Size | 105 × 105 × 35 mm |
| Weight | 0.4 kg; no model mass/density simulation is implied |
| Materials | FSC-certified oak and Norwegian granite for the selected variant |
| Nominal edge depths | 20, 15, 10 and 6 mm |
| Contact inventory | Current technical drawing labels eight physical edge contacts; see mapping below |
| Training positions | Manufacturer advertises more than ten grip/pinch positions; no ten-hold geometry is inferred |
| Origin | Made in Denmark |
| Suspension | Photographs show one cord forming two external branches, lateral openings and side adjustment notches |
| Capacity claim | Current page says over 100 kg; recorded as a manufacturer claim only |
| Included items | Cord is shown with the product. No complete product-specific hardware packing list was located. Carabiners and exercise accessories in use photos do not establish inclusion. |

Sources and conflicts are assessed in [evidence/sources.md](evidence/sources.md). In particular, the generic mounting, stone-type and treatment sections on the store page apply to other product families and do not establish screw mounting or a surface coating for this product.

## Coordinates and scene contract

- Units: meters, unit scale **1.0**, **Z up**. Width along X, thickness along Y. The granite/front face looks toward **−Y**. Top of the reference product photograph is **+Z**.
- Combined mesh bounds: X = ±0.0525, Y = ±0.0175, Z = ±0.0525 m. Mesh object origins share the board center. Mesh location/rotation are zero and scale is one.
- All nine meshes are editable. No live modifiers, Geometry Nodes, external texture dependencies, curves, rope meshes, hardware, cameras, lights or environment meshes are saved in the asset.
- Body and contact objects partition the visible wooden surface. Highlight meshes are actual contact surfaces, not slightly offset overlays. Recess backs, decorative/non-contact areas, notch cuts, exterior transitions and cord-port sleeves remain `body-oak`.
- The wooden contact meshes are open surface partitions by design. They are not individually watertight solids. Their boundary vertices coincide with neighboring parts. Preserve their authored split normals when exporting or recompute normals on the assembled surface before splitting again.
- Granite is a separate solid insert. Small buried overlap at the insert seat is intentional and invisible; no source-derived interior joinery is claimed.
- GLB uses the glTF standard +Y-up conversion. Node names, custom properties, two materials and embedded textures are preserved. Convert marker coordinates with the same root transform as the mesh when using the GLB.

## Hold ID → object mapping

The **hold ID equals the mesh object name** exactly. The upper/lower descriptions refer to the supplied upright front or reverse photograph. Upper contacts are intended to be used with the block inverted; `load_direction_z` in `integration.json` records this distinction. No arbitrary left/right subdivision is made within an edge.

| Hold ID / object | Face and recess | Contact | Depth |
|---|---|---|---:|
| `edge-front-15mm-incut` | Front, upper recess | Upper incut edge | 15 mm |
| `edge-front-15mm-flat` | Front, upper recess | Lower flat edge | 15 mm |
| `edge-front-20mm-wood-flat` | Front, lower recess | Upper wooden edge | 20 mm |
| `edge-front-20mm-granite` | Front, lower recess | Lower granite edge/insert | 20 mm |
| `edge-reverse-10mm-incut` | Reverse, upper recess | Upper incut edge | 10 mm |
| `edge-reverse-10mm-flat` | Reverse, upper recess | Lower flat edge | 10 mm |
| `edge-reverse-06mm-flat` | Reverse, lower recess | Upper flat edge | 6 mm |
| `edge-reverse-06mm-incut` | Reverse, lower recess | Lower incut edge | 6 mm |

The current manufacturer drawing establishes all eight contacts. Pinch exercises can combine contact regions or use a whole-block grip; the available current evidence does not enumerate additional independent pinch surfaces. No extra pinch mesh, jug, shallow ledge or adjustment notch is invented as a selectable hold.

For an app highlight, change the selected object's material assignment to a temporary highlight material. Seven wooden holds share the same oak material as the body: changing that shared material in place would recolor every oak part. Clone/swap the material per selected object or use the renderer's per-node highlight facility. The provided selection proof exercises this distinction.

## Mesh inventory

One nonselectable mesh `body-oak`, eight selectable meshes above, and two Empty objects in `03 Cord passages`. The clean scene contains **11 objects**. Authoritative final vertex/triangle counts are in `integration.json` and the reopened-file validation report. Collection names are `01 Body`, `02 Selectable holds`, and `03 Cord passages`.

## Suspension and cord markers

This is a portable suspended/pulled tool. Although one continuous cord is visible, it forms **two external support branches**; the asset therefore uses the requested multi-branch marker convention, not a fictitious central attachment.

| Marker | Physical location | Position in meters (X, Y, Z) | Outward direction |
|---|---|---|---|
| `cord-passage-1` | Front-view left lateral opening | (−0.0525, 0, −0.0024) | −X |
| `cord-passage-2` | Front-view right lateral opening | (+0.0525, 0, −0.0024) | +X |

Order is front-view left to right. Positions and diameter are scaled photographic approximations. M03 directly shows a lateral opening; M01 and the drawing establish paired branches. The app owns rope length, knots, off-board anchor location, gravity, branch shape and interaction with the adjustment notches.

**Hidden route is unknown.** Only the visible mouths and short sleeves are modeled; the sleeve ends are intentionally uncapped inside the body. No straight cross-drilled tunnel, knot pocket or other unseen route is asserted. The internal sleeve depth is an arbitrary display termination. The current technical drawing is not a sectional engineering drawing.

Three U-shaped front-to-reverse adjustment grooves are modeled on each side at Z ≈ +24, −1.2 and −19 mm. They are nonselectable body geometry, not additional cord-passage markers. The exterior cord may be redirected using these notches, as the manufacturer illustrates, but this asset does not prescribe a complete app-side route or create an unsupported overhead convergence point.

## Unpublished parameters and approximations

These values are editable in `scripts/build_asset.py`. **They are not verified product measurements or additional published specifications.** They establish a visually proportioned display surface from M01–M04, with M07 used for contact semantics.

| Parameter | Display approximation / limitation |
|---|---|
| Exterior corner and front/back roll | 7 mm plan corner radius; 2.8 mm perimeter roll |
| Recess widths | 80 mm internal span; lip footprint expands by its fillet |
| Front 15 mm opening | 21.6 mm internal height, centered Z = +24 mm |
| Front 20 mm opening | 32.4 mm height, centered Z = −22.8 mm; rounded upper corners and smaller lower corners |
| Reverse openings | 20 mm internal heights, centered Z = +24 and −26 mm |
| Lip rounding | 2.8 mm for deeper pockets; 1.7 mm for the 6 mm pocket |
| Incut profile | Direction is source-backed. Curved profile relief of 1.4 mm (15/10) and 0.7 mm (6) is unmeasured; no exact incut angle is claimed |
| Granite insert | Approximately 80 × 20 × 13 mm; plain rounded lip, no invented specimen-specific chips or cracks |
| Side notches | Approx. 2.35 mm cutting radius with a U-shaped opening; spacing from image proportions |
| Port mouth | Approx. 4.3 mm sleeve diameter with a softened entrance; matching opposite side is supported by branch arrangement |
| Sleeve interior | Stops 4.8 mm inside the outer envelope, without a cap. This is display-only truncation, not a measured tunnel depth |
| Surface finish | Neutral matte oak and granite approximation; exact coating and measured roughness are unknown |

The geometric approximation cannot satisfy an interpretation of “exact” that requires unpublished machining measurements. Orthographic/section measurements or a scan would be needed to remove these limits.

## Materials, texture use and licensing

Two self-contained Principled BSDF materials are used: `Oak | neutral matte` and `Granite | neutral matte`. Their base colors use packed 1024² sRGB PNGs. Scalar roughness values are appearance approximations. No normal, displacement, AO, metallic or roughness maps are claimed as measured data.

The oak map is a uniform warm neutral color: it does not invent a board-specific wood grain. The granite map contains original, low-contrast, isotropic mineral-like variation; it does not reproduce a photographed stone sample. No photo pixels, logo, engraving, stains, chalk deposits, shadows, reflections or backgrounds are incorporated in either texture.

Original texture maps and generator code are offered under **CC0-1.0**, to the extent rights exist in them. See `texture-manifest.md` and `LICENSE-original-assets.txt`. Manufacturer/reviewer photographs and page snapshots in `evidence/` remain third-party reference material; no redistribution license was established for them. Keep that folder out of a shipped app. This is an unofficial descriptive model; the project does not grant trademark or product-design rights.

## Rebuild and verify

The source generator uses Blender 4.0.2 mesh-normal APIs. Final renders use Blender 4.2.0 LTS with CPU OpenImageDenoise. Run the source build and validation in Blender 4.0.2, and the dedicated render script in Blender 4.2 LTS:

```sh
blender --background --factory-startup --python scripts/build_asset.py
blender --background Nature-Climbing-Stone-Hanger.blend --python scripts/validate_asset.py
blender --background Nature-Climbing-Stone-Hanger.blend --python scripts/render_asset.py
python scripts/label_renders.py
blender Nature-Climbing-Stone-Hanger.blend --python scripts/outliner_view.py
```

Run `python scripts/make_textures.py` only if regenerating the original maps; it requires NumPy and Pillow. The label script requires Pillow. A render rig is created only while rendering the saved clean asset. It is never written back into the delivered `.blend`. Original unlabeled render pixels are retained in `renders/raw/`.

The final independent check reopens the saved file and verifies the hold/marker inventory, transforms, bounds, materials, packed textures and UV validity. The five labeled PNGs show the front, reverse, oblique, attachment/hold detail and neutral material close-up. Render labels are presentation captions, not product markings.
