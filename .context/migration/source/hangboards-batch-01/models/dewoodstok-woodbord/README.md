# deWoodstok Woodbord

**Status: PARTIAL — actual usable GLB, not a complete physical-product certification.**

Revision: FSC bamboo / EAN 7426870707987  
GLB: `dewoodstok-woodbord.glb`  
SHA-256: `9622a07177b1421675c607b4eabbd88a43f3831f7d23168fb94ad2dcee1f5eff`  
Contacts: **17**; triangles: **42,000**; mesh objects: **18**.  
Material: Bamboo; neutral untextured approximation.  
Nominal width × height × projection: 590 × 148 × 40 mm. See source rulings.

## Integration and coordinates
Source units: metres. X points right, Y toward the rear, Z up. Rear plane Y=0; bottom Z=0;
origin is deliberately rear-bottom-centre. Physical front points **−Y**. The canonical source
camera looks **+Y**, with **+Z** up. These are opposite directions, not contradictory normals.
GLB converts `(x,y,z)` to `(x,z,-y)`; glTF is Y-up, front is **+Z**, canonical camera looks **−Z**.
All transforms are baked into vertices; node transforms are identity. The GLB is self-contained.

The nonselectable mesh is `body`. Each selectable object is named `hold-<logical-ID>`;
`hold-map.json` and glTF node extras provide the exact mapping. In Three.js, traverse meshes and
read `object.userData.logicalHoldId` and `object.userData.selectable`. Clone the shared material
only when highlighting. Every contact is a unique subset of the assembled physical surface,
not a shell over the body. Shared interface edges intentionally make individual patches open;
the assembled surface is watertight and has no duplicate triangles.

This is the fixed wall-mounted version. No cords, cord markers, moving parts, extra poses,
wall or external hardware are exported. Photographed mounting apertures are nonselectable.

## Editable source / rebuilding
`source/assembled-source-z-up.ply` is a standard editable Z-up mesh. The accompanying
`editable-assembled-mesh.npz` includes metre vertices, triangles and face labels;
label 0 is body and following labels follow `build-result.json` contactIds order.
`geometry-config.json` records every authored body section, cut, recess and selected contact.
The construction is numeric geometry; no image segmentation/tracing or generated masks are used.

Rebuild in a new directory with:
```sh
python -m pip install -r source/requirements.txt
python source/rebuild.py --output rebuilt --render
```
Blender can import the delivered GLB or PLY, but **there is no native .blend file** in this package.
The code was executed with Python 3.13.5, trimesh 4.11.1,
VTK 9.6.2 and scikit-image 0.26.0.

## Validation and actual renders
`validation/structural-results.json` checks the actual exported bytes, independent clean import,
metric bounds, topology, mapping, normals, materials, UVs, rays into cavities and open mounting bores.
`renders/` contains six actual VTK renders of a clean reimport of this exact GLB; the labelled
images and `render-provenance.json` carry the export hash. No generated illustration substitutes
for an asset render. `validation/visual-review.json` records a separate visual review.

## What is not fully verified
- The sixteen pocket locations and continuous upper rim are photo-supported; individual depth-to-position mapping is not published in the inspected references.
- All local radii, pocket widths/heights, mounting-hole centres and the 14-degree top slope are authored display estimates.
- The published depth families are preserved separately; do not interpret the estimated per-pocket depths as manufacturer measurements.
- Native .blend and Blender Outliner screenshot unavailable after installation attempts; supported fallback delivered.
- Original source photographs/diagrams could not be downloaded; source URLs, observations and failure logs are included.
- No physical specimen metrology; unresolved dimension/depth/profile matters are itemized, not certified.

## Materials, rights and scope
One original neutral untextured PBR material is used; no grain, logos or decorative features
were invented. See `texture-manifest.md` for UV limits. Source photographs are research
references, not licensed distributable app textures. No rights in product brands or designs
are asserted. Original reconstruction code and neutral material parameters are supplied for
integration; no third-party font files are included. This is a display/interaction asset, not
manufacturing CAD, mounting guidance or a load-bearing design.


## Revision 2 evidence update
Manufacturer source P3 now directly supports the nominal envelope/material/depth families. Original product photos could not be reloaded, so the previous layout observation is not newly independently verified. Geometry is unchanged; all six views were freshly rendered and checked.
