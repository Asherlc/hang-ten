# Evolv Basic Training Board (Long)

**PARTIAL — usable display/interaction asset; the evidence blocker is resolved.**

Product identity: black-resin Long, SKU 66-0000082105. The user supplied front, rear, oblique and side photographs in direct response to the Long gallery request. They are retained byte-for-byte under `evidence/originals/`. The public manufacturer product text was reread on 2026-09-15; exact CDN byte identity of the uploads is not asserted.

## What is delivered

- `evolv-basic-training-board-long.glb`: self-contained metric asset, 50,000 triangles, one nonselectable body and four real independently addressable contact surfaces.
- `source/assembled-source-z-up.ply` and `source/editable-assembled-mesh.npz`: editable assembled mesh in metres; NPZ includes contact face labels.
- `source/rebuild.py`, `geometry.py`, numeric configuration, deterministic export and render code: executed authoring source, not an unrun substitute for geometry.
- `hold-map.json`, source register, feature map, explicit rulings, eight authentic clean-import renders and hash-bound verification.
- No `.blend` or Blender UI screenshot was created: Blender/bpy was absent and the official download attempt failed DNS resolution. This is the permitted fallback, not a pretend native Blender file.

## Scale, axes and origin

Numeric authoring sections are in millimetres. Editable PLY/NPZ and GLB geometry use metres. Source axes: X right, Y rear, Z up. The physical front-facing direction is **-Y**; the canonical source camera looks **+Y**, with +Z up. Origin/pivot: rear-bottom-centre.

The integration conversion is `(x, y, z) -> (x, z, -y)` with unit scale preserved. GLB is Y-up; its front faces +Z and the canonical camera looks -Z. All object transforms are baked, with no conversion root or hidden nonidentity object transform. This fixed board needs no orientation presets or cord markers.

## Evidence-backed construction and estimates

The images establish one continuous jug and three continuous rail contacts, stepped projection, two hollow rear bays, a central spine, mounting bosses and eleven visible mounting apertures. Cavities and bores are actual openings in the shell; no dark planes or highlight shells are used. The contact IDs are `jug`, `edge-upper`, `edge-middle`, `edge-lower`; no left/right duplicates are invented.

Evolv gives 790 x 160 x 60 mm and, inconsistently, 31 x 6.5 x 2.25 inches. This asset uses the metric listing. Nominal edge types are 10, 15 and 20 mm. Their top-to-bottom assignment is a **photo-inferred interpretation** of the side view, not an individually published depth map. Object IDs therefore use positions, not claimed certified dimensions. The authored model measures depth from the frontmost rounded tip to the adjacent back plane; it does not establish a usable flat surface length or an installation gauge.

Rear wall thickness, local curvature, aperture coordinates/radii and fine casting features are not measured. A 6 mm authored minimum front-wall guard prevents a numerical rear-cavity cut from puncturing a rail; it is not a physical or load-bearing specification. Do not manufacture or install equipment from this display asset.

## Material, UVs and selection

One shared neutral charcoal resin PBR approximation, no textures. Triangle-island UVs are nonstretched but vary in density and overlap between separate objects. Do not treat reference photography as licensed app texture. Clone a selected object's material before highlighting, because all objects share the base material.

Load with a glTF 2.0 loader. Resolve `hold-<holdId>` by node name or `extras.logicalHoldId`; `extras.selectable` is false on `body`. All contact meshes are partitions of the physical boundary, not overlapping highlights. No ropes, screws, wall, camera, lights or reference planes are exported.

## Rebuild and verify

Use the Python versions/dependencies recorded under `source/`. From this folder:

```sh
python source/rebuild.py --output /tmp/evolv-rebuilt
python source/render_views.py /tmp/evolv-rebuilt/evolv-basic-training-board-long.glb --output /tmp/evolv-renders
python -m unittest discover -s tests -v
```

Authoring does not read the photos or trace pixels. The numeric section and rear cut are explicitly authored from visual observations, then meshed, optimized as one assembled shell and partitioned. Validation checks the assembled surface rather than requiring each contact patch to be a solid. Structural success does not certify physical dimensions or appearance.

## Rights

Product names identify the research target. No ownership of the commercial product design, branding or third-party photography is asserted. Uploaded photos are retained for this requested research review; commercial image rights remain unestablished. Original reconstruction code is provided for editing and integration. No fonts are distributed.

## Remaining limits

- The top-to-bottom 10/15/20 mm depth assignment is photo-inferred, not a manufacturer-numbered position map; depth labels remain explicitly non-certified.
- The metric and imperial manufacturer dimensions conflict. This asset uses the metric envelope under a recorded ruling, not a measured reconciliation.
- Local curves, shell thickness, rear relief, bore positions/radii and countersink dimensions are photo-derived display estimates. Fine casting wrinkles and surface texture are not reproduced.
- Native Blender and an Outliner screenshot are unavailable after the documented installation attempt; the permitted GLB/PLY/NPZ plus executed-source fallback is delivered.

Current GLB SHA-256: `bc094af7b276749438852b79066fdda4f9f1a937ac32f22ab07c0432d17f81ab`.
