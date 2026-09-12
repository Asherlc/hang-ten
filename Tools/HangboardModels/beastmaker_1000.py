#!/usr/bin/env python3
"""Astra-authored Beastmaker 1000 display geometry from approved primary evidence.

Run from the repository root, without import-path injection:
  rtk proxy blender --background --factory-startup --python-exit-code 1 \
    --python Tools/HangboardModels/beastmaker_1000.py -- \
    --output .context/shaky-rat-beastmaker-1000

The saved source contains model meshes only, in hang-ten-board-v1 metres.
The additional compiler-input source is a rigid axis-transport copy for the
existing compiler's documented native Blender (+X right, +Z up, -Y front).
All sections/positions/radii below are deliberate analytic display estimates,
not measurements, manufacturing CAD, traced paths, or training prescriptions.
Use --clay-only for the inexpensive shape checkpoint before material renders;
--render-source reuses this author's saved source without changing its shape.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import canonical_neutral_wood
from geometry_primitives import (create_recess, create_rounded_body,
                                 make_review_rig, split_contact_surface)

ROOT = Path(__file__).resolve().parents[2]
PACKET_SHA = "510def2516477dedb248ea85e3ec858129d0f298014b28c3e7ef9b19bd41cce0"
W, H, D = 580.0, 150.0, 58.0  # mm at the authoring boundary, converted once
FRAME = "hang-ten-board-v1"
OMISSIONS = ["screw holes", "mounting holes", "countersinks", "mounting hardware", "logos"]
TRIANGLE_CEILING = 200000


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clay-only", action="store_true")
    parser.add_argument("--render-source", action="store_true")
    parser.add_argument("--compiler-only", action="store_true",
                        help="create only a temporary compiler input from committed source code")
    parser.add_argument("--samples", type=int, default=48)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh_object(name, vertices, faces, materials=()):
    data = bpy.data.meshes.new(name)
    data.from_pydata([(x * .001, y * .001, z * .001) for x, y, z in vertices], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        data.materials.append(material)
    return obj


def recalculate(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x-a)/(b-a)))
    return t*t*(3-2*t)


def bezier(a, b, c, d, n=12):
    return [tuple((1-t)**3*a[j] + 3*(1-t)**2*t*b[j] +
                  3*(1-t)*t*t*c[j] + t**3*d[j] for j in range(2))
            for t in (i/n for i in range(n+1))]


def sloper_section(angle):
    """YZ profile: nominal sourced angle plus an estimated 6 mm front roll."""
    a, r = math.radians(angle), 6.0
    cy = H-(D-r)*math.tan(a)-r/math.cos(a)
    zt = D-r+r*math.sin(a)
    # Matching sample counts make the cross-board transitions true lofts.
    line = [(H-z*math.tan(a), z) for z in (zt*i/22 for i in range(23))]
    arc = [(cy+r*math.sin(t), D-r+r*math.cos(t))
           for t in ((math.pi/2-a)*(1-i/14) for i in range(1, 15))]
    return line + arc


def jug_section():
    """Continuous rounded jug rail with a shallow rear saddle and broad crest."""
    first = bezier((140.0, 0.0), (141.0, 10.0), (150.0, 14.0), (150.0, 27.0), 22)
    second = bezier((150.0, 27.0), (150.0, 45.0), (137.0, 58.0), (124.0, 58.0), 14)
    return first + second[1:]


def top_section(x):
    mirrored_x = min(x, W-x)
    jug, steep, center = jug_section(), sloper_section(35), sloper_section(20)
    mix_jug = smoothstep(111, 120, mirrored_x)
    mix_center = smoothstep(212, 219, mirrored_x)
    return [tuple(((1-mix_jug)*j[k]+mix_jug*s[k])*(1-mix_center)+c[k]*mix_center
                  for k in range(2)) for j, s, c in zip(jug, steep, center)]


def top_id(x):
    if x < 25 or x > W-25:
        return None
    if x < 116:
        return "jug-left"
    if x < 215.5:
        return "sloper-35-left"
    if x <= W-215.5:
        return "sloper-center"
    if x <= W-116:
        return "sloper-35-right"
    return "jug-right"


def body_section(x):
    top = top_section(x)
    section = [(3, 0), (top[0][0], 0)] + top[1:]
    top_start, top_end = 1, len(section)-1
    # The approved commerce-gap oblique shows a distinct step wall, with
    # rounded edges, rather than the first draft's broad S-shaped shoulder.
    # Human review found the outer middle cavities crowded by the rising end
    # of this step. Lower the step edge and give it its own tighter end taper;
    # the overall body's 65 mm end silhouette remains unchanged.
    step_start = len(section)
    section += [(47, 58)]
    section += [(47-4*math.sin(t), 54+4*math.cos(t))
                for t in (math.pi/2*i/10 for i in range(1, 11))]
    section += [(43, 44)]
    section += [(40+3*math.cos(t), 44-3*math.sin(t))
                for t in (math.pi/2*i/10 for i in range(1, 11))]
    step_end = len(section)
    section += [(8, 41)]
    section += [(8-8*math.sin(t), 33+8*math.cos(t))
                for t in (math.pi/2*i/12 for i in range(1, 13))]
    section += [(0, 3)]
    section += [(3-3*math.cos(t), 3-3*math.sin(t))
                for t in (math.pi/2*i/6 for i in range(1, 7))]
    # Elliptical end silhouette and a narrow rounded side-depth edge.
    near = min(x, W-x)
    sy = math.sqrt(max(0.0, 1-((65-near)/65)**2)) if near < 65 else 1.0
    step_sy = math.sqrt(max(0.0, 1-((30-near)/30)**2)) if near < 30 else 1.0
    sz = math.sqrt(max(0.0, 1-((6-near)/6)**2)) if near < 6 else 1.0
    return [(x, 75+(y-75)*(step_sy if step_start <= i < step_end else sy), 29+(z-29)*sz)
            for i, (y, z) in enumerate(section)], top_start, top_end


def author_body(materials, material_indices):
    special = [0, .1, .25, .5, 1, 1.5, 2.5, 3.5, 4.5, 5.5, 6, 25, 111, 116, 120, 212, 215.5, 219, 290]
    left = sorted(set(special + [float(i) for i in range(2, 290, 2)]))
    xs = left + [W-x for x in reversed(left[:-1])]
    sections = [body_section(x) for x in xs]
    count = len(sections[0][0])
    verts = [v for section, _, _ in sections for v in section]
    faces, indices = [], []
    for i in range(len(xs)-1):
        contact = top_id((xs[i]+xs[i+1])/2)
        for j in range(count):
            faces.append((i*count+j, (i+1)*count+j, (i+1)*count+(j+1)%count, i*count+(j+1)%count))
            is_top = sections[i][1] <= j < sections[i][2]
            indices.append(material_indices[contact] if is_top and contact else 0)
    faces.extend([tuple(range(count-1, -1, -1)), tuple((len(xs)-1)*count+j for j in range(count))])
    indices.extend([0, 0])
    obj = create_rounded_body("BeastmakerBody", verts, faces,
                              materials=materials, mesh_factory=mesh_object)
    for face, index in zip(obj.data.polygons, indices):
        face.material_index = index
    recalculate(obj)
    return obj


def capsule(cx, cy, width, height, inset=0, steps=20):
    """Direct analytic rounded rectangle; never fitted or extracted from pixels."""
    w, h = width/2+inset, height/2+inset
    r = h
    points = []
    for dx, dy, start in [(w-r, h-r, 0), (-w+r, h-r, 90), (-w+r, -h+r, 180), (w-r, -h+r, 270)]:
        for i in range(steps):
            angle = math.radians(start+90*i/steps)
            points.append((cx+dx+r*math.cos(angle), cy+dy+r*math.sin(angle)))
    return points


def pocket_specs():
    # Explicit authored millimetre estimates selected while viewing official media.
    # Existing logical depth labels are preserved outside this geometry file;
    # these display cavity depths do not certify the per-ID source mapping.
    pairs = [
        ("pocket-top-outer", 63, 105, 82, 22, 10, 58),
        ("pocket-top", 250, 105, 61, 22, 30, 58),
        # Preserve the inner end/neighbour gap; retract only the crowded outer
        # mouth end by 4 mm on each side, symmetrically.
        ("pocket-middle-outer", 59, 67, 82, 22, 45, 58),
        ("pocket-middle-mid", 135, 67, 43, 22, 50, 58),
        ("pocket-middle-inner", 201, 67, 62, 22, 45, 58),
        ("pocket-bottom-outer", 105, 22, 90, 22, 20, 41),
        ("pocket-bottom-mid", 184, 22, 44, 22, 25, 41),
        ("pocket-bottom-inner", 250, 22, 61, 22, 20, 41),
    ]
    result = []
    for base, x, y, w, h, depth, front in pairs:
        for side, cx in [("left", x), ("right", W-x)]:
            result.append(dict(holdID=f"{base}-{side}", centerMM=[cx, y], widthMM=w, heightMM=h,
                               displayDepthMM=depth, faceZMM=front, mouthRadiusMM=2.8, backRadiusMM=min(4.0, depth/3)))
    result.append(dict(holdID="pocket-middle-center", centerMM=[290, 67], widthMM=88, heightMM=22,
                       displayDepthMM=50, faceZMM=58, mouthRadiusMM=2.8, backRadiusMM=4.0))
    return result


def subtract_pocket(body, spec, materials, material_indices):
    cx, cy = spec["centerMM"]
    width, height, front = spec["widthMM"], spec["heightMM"], spec["faceZMM"]
    mouth, back = spec["mouthRadiusMM"], spec["backRadiusMM"]
    floor = front-spec["displayDepthMM"]
    # Sweep a mouth quarter-circle, true wall, then a back quarter-circle.
    rings = [(mouth, front+20), (mouth, front)]
    rings += [(mouth*(1-math.sin(t)), front-mouth*(1-math.cos(t)))
              for t in (math.pi/2*i/10 for i in range(1, 11))]
    rings += [(0, floor+back)]
    rings += [(-back*(1-math.cos(t)), floor+back-back*math.sin(t))
              for t in (math.pi/2*i/10 for i in range(1, 11))]
    verts = [(x, y, z) for inset, z in rings for x, y in capsule(cx, cy, width, height, inset)]
    n = len(verts)//len(rings)
    faces = [tuple(range(n-1, -1, -1))]
    faces += [(i*n+j, i*n+(j+1)%n, (i+1)*n+(j+1)%n, (i+1)*n+j)
              for i in range(len(rings)-1) for j in range(n)]
    faces.append(tuple((len(rings)-1)*n+j for j in range(n)))
    cutter = create_recess("TemporaryRecessCutter", verts, faces,
                           materials=materials, mesh_factory=mesh_object)
    for p in cutter.data.polygons:
        p.material_index = material_indices[spec["holdID"]]
    recalculate(cutter)
    active(body)
    modifier = body.modifiers.new("AuthoredRecess", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    if hasattr(modifier, "material_mode"):
        modifier.material_mode = "INDEX"
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    cutter_data = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    if cutter_data.users == 0:
        bpy.data.meshes.remove(cutter_data)


def wood_materials(hold_ids, output):
    """Use the single shared original light-neutral wood source."""
    materials = []
    for name in ["wood-body"]+hold_ids:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (.78, .73, .65, 1)
        materials.append(mat)
    canonical_neutral_wood.attach_to_materials(materials)
    return materials


def split_and_tag(body, hold_ids):
    for p in body.data.polygons:
        # Planar Boolean cap n-gons use flat shading. Curved strips interpolate.
        p.use_smooth = len(p.vertices) <= 4 and abs(p.normal.z) < .999999
    uv = body.data.uv_layers.new(name="OriginalWoodUV")
    for p in body.data.polygons:
        for li in p.loop_indices:
            co = body.data.vertices[body.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.x/(W*.001), (co.y+.35*co.z)/((H+.35*D)*.001))
    return split_contact_surface(
        body,
        hold_ids,
        tag=True,
        coordinate_frame=FRAME,
        display_estimate=True,
        name_for_material=lambda name: (
            "Hold_" + name.replace("-", "_") if name in hold_ids else "BeastmakerBody"
        ),
    )


def verify_outer_middle_wood_rims():
    """Check real body hits in three bands outside both complete pocket mouths.

    This is a display-geometry clearance regression, not a structural rating
    or a measurement/claim about the physical manufactured board.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    results = []
    targets = {"pocket-middle-outer-left", "pocket-middle-outer-right"}
    for spec in pocket_specs():
        if spec["holdID"] not in targets:
            continue
        tested = 0
        for band_mm in (2, 4, 6):
            for x, y in capsule(*spec["centerMM"], spec["widthMM"], spec["heightMM"],
                                spec["mouthRadiusMM"]+band_mm):
                hit, location, _, _, nearest, _ = bpy.context.scene.ray_cast(
                    depsgraph, Vector((x*.001, y*.001, .10)), Vector((0, 0, -1)), distance=.11)
                assert hit and nearest.get("role") == "body" and abs(location.z-.058) < 1e-6, (
                    "outer middle pocket rim lacks flat wood margin", spec["holdID"], band_mm,
                    (x, y), nearest.name if nearest else None, tuple(location))
                tested += 1
        results.append(dict(holdID=spec["holdID"], verifiedOutsideMouthBandsMM=[2, 4, 6],
                            nearestFlatBodyHits=tested, expectedFaceZMM=58,
                            status="display geometry only; not a physical strength claim"))
    assert len(results) == 2
    return results


def verify_model(objects, hold_ids):
    from collections import Counter
    found = Counter(o.get("hold_id") for o in objects if o.get("role") == "hold")
    assert set(found) == set(hold_ids), (set(hold_ids)-set(found), set(found)-set(hold_ids))
    assert all(n == 1 for n in found.values())
    assert sum(o.get("role") == "body" for o in objects) == 1
    assert all(o.type == "MESH" and o.get("role") in {"hold", "body"} for o in objects)
    positions = [o.matrix_world@v.co for o in objects for v in o.data.vertices]
    assert all(math.isfinite(c) for p in positions for c in p)
    low = [min(p[j] for p in positions) for j in range(3)]
    high = [max(p[j] for p in positions) for j in range(3)]
    assert all(abs(v) < 1e-6 for v in low), low
    assert all(abs(a-b) < 1e-6 for a, b in zip(high, [.58, .15, .058])), high
    triangles = sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
    assert triangles < TRIANGLE_CEILING, triangles
    records = []
    head_on_hits = []
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(objects, key=lambda o: o.name):
        obj.data.calc_loop_triangles()
        assert len(obj.data.materials) > 0
        record = dict(nodeID=obj.name, role=obj["role"], vertices=len(obj.data.vertices),
                      triangles=len(obj.data.loop_triangles), modifiers=len(obj.modifiers))
        if obj.get("hold_id"):
            record["holdID"] = obj["hold_id"]
            vertices = [obj.matrix_world@v.co for v in obj.data.vertices]
            xy = [(min(v[j] for v in vertices)+max(v[j] for v in vertices))/2 for j in range(2)]
            hit, _, _, _, nearest, _ = bpy.context.scene.ray_cast(
                depsgraph, Vector((xy[0], xy[1], .10)), Vector((0, 0, -1)), distance=.11)
            assert hit and nearest.get("hold_id") == obj["hold_id"], (obj.name, nearest.name if nearest else None)
            head_on_hits.append(dict(expectedID=obj["hold_id"], nearestID=nearest["hold_id"], faceCenterMeters=xy))
        records.append(record)
    return dict(boundsMeters=dict(min=low, max=high), triangles=triangles,
                triangleCeiling=TRIANGLE_CEILING, hold_ids_preserved=len(found),
                body_mesh_count=1, hardware_mesh_count=0, meshes=records,
                authoredHeadOnNearestHits=head_on_hits,
                authoredHeadOnNearestHitCount=len(head_on_hits),
                outerMiddlePocketWoodRims=verify_outer_middle_wood_rims())


def aim(obj, target):
    forward = (Vector(target)-obj.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward).normalized()
    obj.rotation_euler = Matrix((right, up, -forward)).transposed().to_euler()


def save_compiler_input(objects, output):
    """Transport axes only; preserve local vertices, topology and materials."""
    transform = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    matrices = {obj: obj.matrix_world.copy() for obj in objects}
    scene = bpy.context.scene
    try:
        for obj in objects:
            obj.matrix_world = transform@matrices[obj]
        scene["compiler_storage_frame"] = "blender-x-right-z-up-negative-y-front"
        scene["source_canonical_frame"] = FRAME
        bpy.context.view_layer.update()
        path = output/"beastmaker-1000-compiler-input.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
    finally:
        for obj, matrix in matrices.items():
            obj.matrix_world = matrix
        del scene["compiler_storage_frame"]
        del scene["source_canonical_frame"]
        bpy.context.view_layer.update()
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path),
                boardToStorageMatrix=[list(row) for row in transform],
                operation="rigid axis transport only; unchanged local vertices/topology/materials")


def review_rig(samples):
    return make_review_rig(samples)


def render_view(output, name, camera, location, target, scale, resolution, *, clay=False):
    scene = bpy.context.scene
    camera.location = location
    aim(camera, target)
    camera.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.engine = "BLENDER_WORKBENCH" if clay else "CYCLES"
    if clay:
        sh = scene.display.shading
        sh.light = "STUDIO"
        sh.studio_light = "paint.sl"
        sh.color_type = "OBJECT"
        sh.show_shadows = True
        sh.show_cavity = True
        sh.cavity_type = "BOTH"
        sh.curvature_ridge_factor = 1.2
        sh.curvature_valley_factor = 1.0
        sh.background_type = "WORLD"
    scene.render.filepath = str(output/(name+".png"))
    bpy.ops.render.render(write_still=True)
    return dict(file=name+".png", engine=scene.render.engine,
                camera=dict(type="orthographic", locationMeters=location, targetMeters=target,
                            up=[0, 1, 0], orthographicScaleMeters=scale, resolution=resolution),
                sha256=sha(output/(name+".png")))


def source_report(output, report):
    rows = "\n".join(f"| {s['holdID']} | {s['centerMM']} | {s['widthMM']} × {s['heightMM']} | {s['displayDepthMM']} | {s['faceZMM']} |"
                     for s in pocket_specs())
    (output/"source-versus-estimate.md").write_text(f"""# Beastmaker 1000 authored display model — Astra correction round 2

Human evidence approval: granted in the controlling session before authoring.
Human visual fidelity approval: **pending**. This pass is not approved for package promotion.

## Retained source facts

Approved packet SHA-256: `{PACKET_SHA}`. The packet retains exact manufacturer page/media hashes. Sourced face size is 580 × 150 mm; 58 mm depth follows the approved qualified Beech/shared-layout ruling. The Tulip page's conflicting 5 mm text is not a thickness fact. The official front supports 2 jugs, 3 slopers and 17 cavities. The manufacturer names 35° paired and 20° centre slopers. Stable per-ID names/kinds/depth labels are inherited package metadata; the sources do not assign every ID its exact measurement.

The two human-approved shape references are retained manufacturer `references/beastmaker-1000-tulip.jpg` and commerce-gap `references/fluxperfect-beastmaker-1000-ansicht-1.jpg`, both manually inspected at original detail. Their exact hashes are recorded in the approved packet and model report. The second view qualitatively supports the top/side/end continuity and more definite lower step; it supplies no measured radii, depth or hidden sections and cannot override manufacturer claims. No legacy PNG, canonical 2D path, prior candidate geometry, image processing, tracing, segmentation, registration/alignment, cropping, or vectorization is used. This generator deliberately authors mathematical sections and mirrored recesses.

## Authored estimates

All exact positions, aperture dimensions, cavity depths and cross-sections, end silhouette, tier profile, back profile, transition widths, mouth/back fillets, and jug sections are **display estimates**, not manufacturer measurements. Nominal sloper angles follow the named families, while their placement and blending are estimated. No model measurement changes logical metadata or training content.

The estimated lower front face is at Z=41 mm; upper face at Z=58 mm. After reviewing the added true three-quarter view, Astra replaced the first draft's broad S-shaped shoulder with a distinct step wall. Human feedback on the rendered pass then identified crowded outer middle pocket rims. In correction round 2, Astra lowered the upper flat's step edge from Y=52 to 47 mm, with a wall at Y=43 mm, a 4 mm upper roll and 3 mm lower fillet; the lower flat begins at Y=40 mm. That step now uses its own 30 mm end taper instead of inheriting the body's 65 mm taper, preserving a flat wood band around the outer middle cavities. Both affected throat widths changed from 86 to 82 mm and their symmetric centres from X=57/523 to 59/521 mm, preserving each mouth's inner end and neighbour gap. The overall end silhouette still uses a 65 mm horizontal ellipse radius and 75 mm vertical half-height, with the same 6 mm depth-edge roll. Jugs use continuous cubic sections with a 150 mm high crest; slopers use nominal angled sections with a 6 mm front roll. Mirroring is exact around X=290 mm.

Each pocket uses an explicitly authored capsule-like mouth, a 2.8 mm mouth fillet, a true wall, a back fillet up to 4 mm, and a planar back. The back remains closed; the narrowest estimated rear thickness is 8 mm. Geometry is split into material-bound pieces after carving, so the selectable mesh is the actual visible carved surface.

| Logical ID | Estimated centre XY mm | Estimated throat W × H mm | Estimated display depth mm | Estimated face Z mm |
| --- | --- | --- | --- | --- |
{rows}

## Materials and deliberate omissions

Original analytic pale-wood texture, shared UV field across all physical surfaces; generic wood, no species-match claim. Screw holes, mounting holes, countersinks, mounting hardware, and logos are deliberately omitted from this display model. The physical product does have mounting features.

## Geometry checkpoint

Bounds in `{FRAME}`: `{report['boundsMeters']}` metres. `{report['triangles']}` triangles (ceiling {TRIANGLE_CEILING}); exactly one body mesh and 22 individually tagged hold meshes. No unbound mesh or hardware geometry is present. Source `.blend` contains model meshes only; review cameras/lights are created after saving and are not part of the compiler input. All 22 rays at mesh-derived face-bound centres hit their exact expected hold as the nearest authored Blender surface; this is not a substitute for later native SceneKit tests.

The targeted outer-middle rim regression probes the actual model in 2, 4 and 6 mm bands outside each complete mouth (240 nearest flat-body hits per pocket). The prior exported pass failed even the 2 mm band at its rounded end. The corrected source must pass all 480 probes. These are authored display-clearance checks, not a physical strength rating or manufacturing measurement. Cameras, lights and wood material are unchanged from the human-reviewed pass. The prior sources/reports/renders are archived under `review-round-1/`; the prior USDZ remains under `package-first-pass/`.

`beastmaker-1000.blend` remains in the canonical frame. `beastmaker-1000-compiler-input.blend` is a rigid +90° X-axis transport copy for the existing compiler's documented Blender-native storage convention; local vertex positions, topology, material assignments and physical shape are unchanged. The report records the exact matrix and both hashes. The compiler converts that copy back into the exact canonical USDZ frame. Neither source contains a camera, light, or other non-mesh object.

Cycles is the recorded previous production-engine choice and is used for final material images. Workbench clay views are the inexpensive first shape review. All camera, light, material, renderer, and image hashes are in `model-report.json`. The generator does not compile or promote a package.

Known limitations: exact rear shape, cavity sections, wall inclinations, lip radii and physical per-ID depth mapping lack manufacturer measurements. This pass needs human comparison of silhouette, tier height, rail transitions, cavity spacing and mouth shape against the official front. Inventory checks alone do not establish fidelity. Native USDZ reimport/material/picking checks belong to the subsequent approved export task.

## Ownership and lifecycle

Owner: `{report['workspaceOwner']}`. Durable editable source, image texture, evidence, review images and reports are retained in this owned directory. The authoring process removes its exact temporary cutter meshes as they are consumed; no external server/simulator/tunnel is created. No source package, runtime file, or raster resource is changed.
""", encoding="utf-8")


def main():
    args = arguments()
    output = args.output.resolve()
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", ROOT)).name
    if args.compiler_only:
        # The package rebuild provisions this source from committed generator
        # inputs in its owned temporary directory.  It deliberately neither
        # reads nor overwrites the durable review source under .context.
        assert output.is_relative_to(ROOT / ".context")
        assert not args.render_source
        output.mkdir(parents=True, exist_ok=True)
        (output / "ownership.json").write_text(
            json.dumps({"owner": owner, "resources": [str(output)], "external_resources": []}, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        assert output.parent == ROOT/".context" and output.name == owner+"-beastmaker-1000"
        assert sha(output/"evidence-packet.json") == PACKET_SHA
        assert json.loads((output/"ownership.json").read_text())["workspaceOwner"] == owner
    # Read only logical inventory; presentation paths are never interpreted.
    document = json.loads((ROOT/"Hangboards/beastmaker-1000/board.json").read_text())
    hold_ids = [hold["id"] for hold in document["holds"]]
    assert len(hold_ids) == 22 and len(set(hold_ids)) == 22
    bpy.context.preferences.filepaths.save_version = 0
    source = output/"beastmaker-1000.blend"
    if args.render_source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        objects = list(bpy.context.scene.objects)
    else:
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        materials = wood_materials(hold_ids, output)
        indices = {hold_id: i+1 for i, hold_id in enumerate(hold_ids)}
        body = author_body(materials, indices)
        for spec in pocket_specs():
            subtract_pocket(body, spec, materials, indices)
            print("AUTHORED", spec["holdID"], flush=True)
        objects = split_and_tag(body, hold_ids)
    checks = verify_model(objects, hold_ids)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    bpy.context.scene["coordinate_frame"] = FRAME
    bpy.context.scene["geometry_author"] = "gpt-6-astra"
    bpy.context.scene["evidence_packet_sha256"] = PACKET_SHA
    if not args.render_source:
        bpy.ops.wm.save_as_mainfile(filepath=str(source))
    compiler_input = save_compiler_input(objects, output)
    if args.compiler_only:
        print(json.dumps({"compilerInput": compiler_input, **checks}), flush=True)
        return
    camera, lights = review_rig(args.samples)
    views = []
    front = dict(location=(.29, .075, 1.05), target=(.29, .075, .029), scale=.65, resolution=(1950, 630))
    oblique = dict(location=(.60, .48, .70), target=(.29, .075, .029), scale=.65, resolution=(1800, 820))
    detail = dict(location=(.275, .148, .33), target=(.244, .071, .035), scale=.205, resolution=(1400, 1050))
    views.append(render_view(output, "clay-front", camera, clay=True, **front))
    views.append(render_view(output, "clay-three-quarter", camera, clay=True, **oblique))
    views.append(render_view(output, "clay-detail", camera, clay=True, **detail))
    if not args.clay_only:
        views.append(render_view(output, "front", camera, **front))
        views.append(render_view(output, "three-quarter", camera, **oblique))
        views.append(render_view(output, "material-detail", camera, **detail))
        selected = {"jug-left", "sloper-center", "pocket-middle-center", "pocket-bottom-mid-right"}
        original = {}
        for obj in objects:
            if obj.get("hold_id") not in selected:
                continue
            for mat in obj.data.materials:
                if mat.name not in selected or mat.name in original:
                    continue
                nodes = mat.node_tree
                bsdf = nodes.nodes.get("Principled BSDF")
                link = next(iter(bsdf.inputs["Base Color"].links))
                original[mat.name] = link.from_socket
                nodes.links.remove(link)
                bsdf.inputs["Base Color"].default_value = (.015, .38, .18, 1)
        views.append(render_view(output, "selected-holds", camera, **front))
        for mat_name, socket in original.items():
            mat = bpy.data.materials[mat_name]
            mat.node_tree.links.new(socket, mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    # Diagnostic identity overview uses actual mesh pieces, not overlay paths.
    for index, obj in enumerate(sorted(objects, key=lambda o: o.name)):
        if obj.get("role") == "hold":
            import colorsys
            obj.color = (*colorsys.hsv_to_rgb((index*.61803398875)%1, .52, .8), 1)
        else:
            obj.color = (.56, .56, .56, 1)
    views.append(render_view(output, "contact-overview", camera, clay=True, **front))
    report = dict(schemaVersion=1, boardID="beastmaker-1000", geometryAuthor="gpt-6-astra",
                  workspaceOwner=owner, coordinateFrame=FRAME, evidencePacketSHA256=PACKET_SHA,
                  sourceBlend=str(source.relative_to(ROOT)), sourceSHA256=sha(source),
                  approvedVisualReferences=[dict(path="references/beastmaker-1000-tulip.jpg", tier="manufacturer",
                                                 sha256=sha(output/"references/beastmaker-1000-tulip.jpg")),
                                            dict(path="references/fluxperfect-beastmaker-1000-ansicht-1.jpg", tier="commerce-gap",
                                                 sha256=sha(output/"references/fluxperfect-beastmaker-1000-ansicht-1.jpg"))],
                  generatorSHA256=sha(Path(__file__)), compilerInput=compiler_input,
                  humanEvidenceApproval="granted in controlling session, including exact four-image multi-angle set",
                  humanVisualApproval="pending", deliberateOmissions=OMISSIONS,
                  humanFeedbackRound=dict(number=2, defect="outer middle pockets crowded by rounded body ends",
                                          correctedHoldIDs=["pocket-middle-outer-left", "pocket-middle-outer-right"],
                                          scope="physical step/end transition and pocket mouths; unchanged camera/lights/material"),
                  sourceFacts=dict(faceMillimeters=[580, 150], qualifiedSharedLayoutDepthMillimeters=58),
                  estimateStatus="Every authored position, radius, section and cavity depth is a display estimate",
                  pocketEstimates=pocket_specs(), reviewViews=views, reviewLights=lights,
                  renderer=dict(production="CYCLES", diagnostic="BLENDER_WORKBENCH", samples=args.samples,
                                device="CPU", denoising=True, viewTransform="AgX", look="AgX - Medium High Contrast", exposure=-1.0),
                  material=dict(type="original generic light-neutral wood", image=canonical_neutral_wood.CANONICAL_TEXTURE_NAME,
                                imageSHA256=sha(canonical_neutral_wood.CANONICAL_TEXTURE_PATH), speciesMatch=False,
                                generatorVersion=canonical_neutral_wood.GENERATOR_VERSION), **checks)
    (output/"model-report.json").write_text(json.dumps(report, indent=2)+"\n")
    source_report(output, report)
    print(json.dumps({k: report[k] for k in ["boundsMeters", "triangles", "hold_ids_preserved", "body_mesh_count", "hardware_mesh_count", "sourceSHA256"]}), flush=True)


if __name__ == "__main__":
    main()
