# Zlagboard.Pro 2.0 — repaired v2

**Status: PARTIAL.** The repaired display/interaction export is real and structurally validated. Original-source binary retention and native Blender deliverables remain unavailable; no physical-device or manufacturer-accuracy certification is claimed.

Revision: Zlagboard.Pro 2.0, 2019 three-row board; explicitly NOT Pro1.

## Current asset
`zlagboard-pro-2-0.glb` — SHA-256 `e71482d155485acd5ad710f7fb8cf2ac2a055ef14a634a6026733f2e970f3b56`.

28 independently selectable physical contacts; 54,006 triangles; 43,871 vertex records; 1,978,016 bytes. Original export: 9,886,980 bytes and 96,970 triangles. File-size reduction: 80.0%.

## Repair details
The per-triangle UV vertex explosion was replaced with indexed surfaces and connected charts. Original geometry across curved lips/normal transitions is protected during simplification; global beveling or smoothing does not conceal lost curvature. Every logical contact boundary edge is preserved, and shared body/contact positions retain matching assembled-source normals.
Largest sampled two-way vertex/centroid deviation from this revision's source master: 0.009958 mm; budget 0.25 mm. This is a sampled comparison, not an analytic global Hausdorff certificate and not measurement against the physical product.

## Coordinates and integration
Source: metres, X right, Z up, physical front -Y. Canonical front camera LOOKS +Y, up +Z. Origin: board/pair centered in X, authored Z=0 datum, rear mounting plane Y=0. Pair spacing is an authored display choice, not a training instruction.
GLB: Y up, physical front +Z, camera LOOKS -Z with +Y up. One deliberate root `SOURCE-ZUP_to_GLTF-YUP` maps (x,y,z) to (x,z,-y), quaternion [-0.70710678,0,0,0.70710678] in xyzw order. Individual mesh transforms are applied; do not convert axes twice.

Use the stable `nodeName` / `holdId` in hold-map.json or node extras. Every contact owns actual surface faces, not an overlapping highlight shell. Bodies are nonselectable. Clone a selected node's material before highlighting, so the shared neutral material is not changed globally.

## Specifications and mounting
Material: Lime wood per manufacturer, neutral untextured approximation.
Published dimensions (mm): None; scope/order: Bare-board X width, Y thickness, Z height; calibration estimates.
Estimated calibration (mm), where recorded: [705, 42, 152].

Wall-mounted metal frame/phone sensing system omitted as external hardware. No invented hidden rear mounting holes.
No source-supported cord suspension: no cord markers, ropes, knots or external mounting hardware are included. Fixed boards need no redundant orientation file. Observed openings and estimated placements are in mounting-interface.json. Hidden routing is not invented.

## Research and limitations
Sources.md preserves exact revisions, source URLs, publisher/evidence tier, access date, supported and unknown facts, and explicit conflict rulings. Evidence/feature-to-evidence.json maps the physical contacts to those sources. Published values, photo estimates and authored display choices remain distinguished.
- Bare-wood 705 x 152 x 42 mm is a calibration estimate; listed 25/8 cm dimensions have unclear assembled/package scope.
- Reverse unverified and simplified. Unlabelled sloper floor angles estimated 12 degrees; incut floor angles estimated -8 degrees.
- Nominal grip depths follow the pro2 chart, not old Pro 1 specifications.
- Original reference image/PDF binaries are not retained. Source URLs and inspected feature notes exist; failed downloads are not represented as originals.
- Blender/bpy unavailable after installation/download attempts. Editable geometry and executed Python source are the genuine fallback; no .blend or Blender Outliner image is fabricated.
- Physical target-phone and user-application testing remain unperformed. Separate browser-harness tests, when supplied, are not device certification.

## UV/materials
One neutral PBR material is embedded. No wood grain, logo, photograph, baked lighting or other distinctive texture was invented. UV0 uses 1,129 connected angular-cone charts, maximum local stretch ratio 1.094623. Different mesh objects deliberately reuse the 0–1 domain. This is NOT a continuous cross-object directional grain atlas. No image texture is applied, so atlas overlap does not create a texture seam. See texture-manifest.md.

## Editable source and rebuild
Source/geometry.npz is the indexed editable master (vertices, triangles, normals, face_groups); geometry-groups.json carries stable groups. Runtime-geometry.npz stores optimized indexed geometry before UV splitting. The OBJ/MTL is exported from the actual GLB in metric source coordinates. Product-specific original parameter definitions remain in products.py/geometry.py. Forge_mesh_repair.py is the separately executed, explicitly mapped loft edit; it does not rediscover geometry from pictures.

```sh
python source/rebuild.py --output /a/new/directory
```
Requires Python, NumPy, SciPy, trimesh, VTK, Shapely and Pillow. On a headless Linux host use a working software OpenGL display (for example xvfb-run -a). The packaged builder regenerates GLB, clean-import validation and five actual renders from the frozen editable master. An edited master invalidates earlier review hashes.

## Validation and rights
Validation/results.json, optimization.json, validation/visual-review.json and renders/render-records.json identify this exact export. Structural checks, visual review and evidence coverage are separate. Every review image is a genuine GLB render, not generated artwork or a simulated Blender screenshot.
Authored code/mesh/material license: source/LICENSE.txt. Product names, designs, trademarks and manufacturer photography remain their owners' property; those rights are not granted by the source-code license.
Display/interaction asset only, not manufacturing CAD, load-bearing design or safety instructions.
