# Metolius Wood Grips II Deluxe — geometry revision 2

**PARTIAL: corrected usable display model; not a fully source-verified replica.**

Exact product: WOOD005 / Deluxe, not Compact  
Export: `metolius-wood-grips-ii-deluxe.glb`  
SHA-256: `cc8dd4f09dda2685672445e974c698ac5c704bcbc805b87e1bcb6fa3726ad67a`  
26 selectable contacts; 65,000 triangles; 27 mesh objects.  
Nominal width × height × projection: 610 × 216 × 70 mm.  
Material: FSC wood; neutral untextured approximation.

## Actual changes
- Replaced the incorrect four-bore arrangement with six board apertures in three left/right pairs.
- Retained 31/32/38 mm and 25/25/28 mm nonuniform rows because the readable numbered diagram corroborates them.
- Resolved the earlier uniform-row audit allegation in favour of the numbered Deluxe diagram, with explicit provenance and limits.
- Regenerated geometry, exact mappings, source, validation, fresh renders and checksums.

## Coordinates and selection
Source geometry is **metres, X right / Y rear / Z up**. Physical front points -Y; the canonical
source camera looks +Y, with +Z up. Origin/pivot is rear-bottom-centre (rear Y=0, bottom Z=0).
The export maps source `(x,y,z)` to glTF `(x,z,-y)`: glTF is Y-up, front is +Z, camera looks -Z.
Node transforms are identity; geometry is already transformed into metric glTF coordinates.
All production nodes are meshes. `body` is nonselectable. Each actual contact surface is a
separate `hold-<ID>` mesh, with `selectable` and `logicalHoldId` in node extras. `hold-map.json`
records the exact stable object names and the CURRENT node indices. Node indices may change
between revisions; bind interaction to logicalHoldId or objectName, not array indices.
The physical surface is partitioned, not overlaid. Individual patches are intentionally open;
only the assembled geometry is required to form a closed solid. No duplicate highlight shells.
No cords, walls, external screws, cameras, lights or rigs are included. This is a fixed board.

## Editing and rebuilding
`source/assembled-source-z-up.ply` is standard editable geometry in metres.
`source/editable-assembled-mesh.npz` adds face labels: zero=body; subsequent labels follow
`build-result.json` geometry.contactIds. The saved numeric profiles/cuts/pockets are in
`source/geometry-config.json`; no image segmentation or automatic tracing is used.

```sh
python -m pip install -r source/requirements.txt
python source/rebuild.py --output rebuilt --render
```

The source was executed and compared against this exact GLB; see validation/rebuild-results.json.
No `.blend` or Blender Outliner screenshot is included: Blender/bpy was unavailable after a
reasonable installation attempt. GLB/PLY/NPZ and executed authoring code are the permitted fallback,
not files disguised as native Blender. Python/VTK/trimesh versions are recorded under source/.

## Validation and visual review
All current structural checks, actual measurements and clean-import details are in validation/.
The 6 labelled images are genuine renders of THIS GLB after independent isolated VTK import;
render-provenance.json binds every image to the export hash. The separate visual review states
what matches the product and what remains an estimate. No source-certification is inferred
merely from a valid GLB or a passing ZIP check.

## Evidence and remaining limits
- Overall width and height are manufacturer values. Projection 70 mm follows a rounded retailer listing, not a manufacturer dimensioned drawing.
- The 26 physical contacts and nonuniform 31/32/38 mm and 25/25/28 mm rows are corroborated by the readable Deluxe numbered diagram M-DIAGRAM-V2. Six mounting bores are now present; centres are estimates, not a drilling template.
- Tier profiles, outer-jug undercut, stopper curvature, pocket widths/heights and mounting centres are authored photo-derived estimates. The model does not claim a measured replica.
- Top 55/58 mm labels are grip surface dimensions and are not treated as blind-cavity depths. External screws and wood grain are omitted.
- Original reference-image bytes were not retained; download attempts failed.
- Native Blender unavailable; actual editable GLB/PLY/NPZ and executed construction source provided under the allowed fallback.

## Materials and rights
One neutral untextured PBR material is shared across body/contact boundaries. No invented grain,
logos or decorative textures. UVs are isometric per-triangle islands; there is no per-triangle
stretch but density and seams vary. Not suitable for seamless painted decals without reunwrapping.
Reference photos are research, not licensed shippable textures. No rights in trademarks/product
shapes are asserted. No font files are included. Display/interaction use only, not manufacturing,
load-bearing equipment, installation instructions or a measured physical replica.
