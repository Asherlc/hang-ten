# Moon Armstrong — geometry revision 2

**PARTIAL: corrected usable display model; not a fully source-verified replica.**

Exact product: 60-112-ASH / sustainable Ash wooden revision  
Export: `moon-armstrong-ash.glb`  
SHA-256: `80d796c3d5ab126cb9abd501e16621dd044e555f08e54b82179bcabf3735bbf8`  
21 selectable contacts; 46,000 triangles; 22 mesh objects.  
Nominal width × height × projection: 650 × 165 × 55 mm.  
Material: Ash; neutral untextured approximation.

## Actual changes
- Replaced the central capsule recess with an integral upper lip and arched underside notch.
- Replaced the two central capsule pockets with continuous 22 mm and 18 mm nominal open shelves.
- Removed the false rear caps on both mono openings; front nominal grip length is distinguished from the estimated rear continuation.
- Kept all 21 logical IDs; regenerated current node indices, meshes, authoring source, mappings, validation and renders.

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
The 8 labelled images are genuine renders of THIS GLB after independent isolated VTK import;
render-provenance.json binds every image to the export hash. The separate visual review states
what matches the product and what remains an estimate. No source-certification is inferred
merely from a valid GLB or a passing ZIP check.

## Evidence and remaining limits
- The Ash manufacturer photograph has an asymmetric column layout: four-edge columns at far left and right-of-centre, jug columns left-of-centre and far right. The asset preserves this layout rather than imposing mirror symmetry.
- The 21-contact inventory is manufacturer-supported. Local widths, heights, bores, radii and body relief are display estimates.
- The two mono openings now pass through as shown by the Ash photo. Their front nominal contact length remains 22 mm; a straight continuation to the planar estimated rear is an explicit display approximation, not verified rear machining or pulley routing.
- The central jug is now a rolled upper lip with an arched underside notch, not a capsule recess. Arch radius, undercut depth and rear termination are photo-derived display estimates. Logos, grain, pulley hardware and external mounting hardware are omitted.
- Central 22/18 mm contacts are continuous open shelves. Tier Z positions, lip rounding and rear projection are photo-derived display estimates.
- Original reference-image bytes were not retained; download attempts failed.
- Native Blender unavailable; actual editable GLB/PLY/NPZ and executed construction source provided under the allowed fallback.

## Materials and rights
One neutral untextured PBR material is shared across body/contact boundaries. No invented grain,
logos or decorative textures. UVs are isometric per-triangle islands; there is no per-triangle
stretch but density and seams vary. Not suitable for seamless painted decals without reunwrapping.
Reference photos are research, not licensed shippable textures. No rights in trademarks/product
shapes are asserted. No font files are included. Display/interaction use only, not manufacturing,
load-bearing equipment, installation instructions or a measured physical replica.
