"""Directly authored Flash Board display geometry, not manufacturing CAD.

Evidence: docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md
and the approved manufacturer/commerce snapshots plus all six user closeups
in the workspace evidence packet. Filenames are not face-identification data.
No source image, old raster path, detection, tracing, or fitted contour is used
by this generator. Every numeric dimension below is an authored estimate;
published global edge depths are deliberately not assigned to specific holds.

Blender --background --factory-startup --python this_file -- --output DIR
Add --render for source-shape review images. The saved .blend contains only
physical wood: one body and the seven stable contact meshes. Cord passages
are integral body geometry, not screw/mounting holes. There is no display cord,
anchor, knot, logo, mounting hardware, or environment mesh.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import canonical_neutral_wood

ROOT = TOOLS.parents[1]
HOLD_IDS = (
    "three-edge-left", "three-edge-center", "three-edge-right",
    "two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right",
)
# Shape estimates from direct visual review, never source-backed dimensions.
WIDTH_MM = 500.0
DIAMETER_MM = 76.0
RADIUS_MM = DIAMETER_MM / 2
END_ROUND_MM = 3.0


def xyz(x, height, depth):
    """Board mm -> Blender metres (+X right, +Z up, front toward -Y).

    Compiler conversion yields hang-ten-board-v1, with its minimum corner at
    (0, 0, 0), +Y up, +Z toward the three-edge face. Opposite usable face is -Z.
    """
    return x / 1000, -depth / 1000, height / 1000


def mesh(name, vertices, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    active(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .62
    return mat


def rounded_rectangle(cx, cy, width, height, radius):
    """Analytic, deliberately chosen profile; no pixel-derived coordinates."""
    radius = min(radius, width / 2, height / 2)
    points = []
    for xx, yy, start in (
        (cx + width/2-radius, cy + height/2-radius, 0),
        (cx - width/2+radius, cy + height/2-radius, 90),
        (cx - width/2+radius, cy - height/2+radius, 180),
        (cx + width/2-radius, cy - height/2+radius, 270),
    ):
        for i in range(13):
            a = math.radians(start + 90*i/12)
            point = (xx + radius*math.cos(a), yy + radius*math.sin(a))
            if not points or math.dist(points[-1], point) > 1e-8:
                points.append(point)
    if math.dist(points[0], points[-1]) < 1e-8:
        points.pop()
    return points


def carve(body, cutter, material_index=0, body_face_indices=()):
    for mat in body.data.materials:
        cutter.data.materials.append(mat)
    for face in cutter.data.polygons:
        face.material_index = 0 if face.index in body_face_indices else material_index
    active(body)
    modifier = body.modifiers.new("Authored recess", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    if not body.data.polygons:
        raise RuntimeError("Authored subtraction unexpectedly removed the body")


def recess(body, name, cx, cy, width, height, floor, mouth, radius,
           back_fillet, mouth_fillet, face_sign=1, hold_id=None, inner_step=0,
           top_face=False, radial_angle=None):
    """Explicit tangent mouth/back rounds and straight intervening walls.

    Depth is measured inward from each face's local 76 mm extremum. Flipping
    the face rigidly mirrors the same construction onto the opposite surface.
    """
    rings = [(floor + back_fillet*(1-math.cos(i*math.pi/2/12)),
              inner_step+back_fillet*(1-math.sin(i*math.pi/2/12))) for i in range(13)]
    if inner_step:
        # The reviewed wells have a distinct inset inner ledge. Its short
        # smooth shoulder and both adjacent walls are geometry, not painted
        # lines or a material cue. This section's dimensions are estimates.
        rings += [(floor+5.5+1.5*i/12,
                   inner_step*(1-3*(i/12)**2+2*(i/12)**3)) for i in range(13)]
    rings += [(mouth-mouth_fillet+mouth_fillet*math.sin(i*math.pi/2/12),
               -mouth_fillet*(1-math.cos(i*math.pi/2/12))) for i in range(13)]
    rings += [(100, -mouth_fillet)]
    profiles = [rounded_rectangle(cx, cy, width-2*inset, height-2*inset,
                                  radius-inset) for _, inset in rings]
    n = len(profiles[0])
    assert all(len(profile) == n for profile in profiles)
    def point(x, y, d):
        if radial_angle is not None:
            angle = math.radians(radial_angle)
            tangent, radial = y-RADIUS_MM, d-RADIUS_MM
            return xyz(x, RADIUS_MM+radial*math.sin(angle)+tangent*math.cos(angle),
                       RADIUS_MM+radial*math.cos(angle)-tangent*math.sin(angle))
        return (xyz(x, d, DIAMETER_MM-y) if top_face else
                xyz(x, y, d if face_sign == 1 else DIAMETER_MM-d))
    vertices = [point(x, y, d)
                for (d, _), profile in zip(rings, profiles) for x, y in profile]
    faces = [tuple(reversed(range(n))),
             tuple(range((len(rings)-1)*n, len(rings)*n))]
    faces += [(j*n+i, j*n+(i+1)%n, (j+1)*n+(i+1)%n, (j+1)*n+i)
              for j in range(len(rings)-1) for i in range(n)]
    carve(body, mesh(name, vertices, faces),
          0 if hold_id is None else HOLD_IDS.index(hold_id)+1)


def stepped_edge(body, hold_id, cx, *, face_sign=1, center=False):
    """A single well with an asymmetric lower shelf and a tapered upper wall.

    Direct visual construction from the labelled three-well photograph and
    both oblique two-well photographs. The old concentric inset made a bowl;
    the visible section has one broad lower shelf, rounded end walls, and a
    substantially taller mouth. All section values remain display estimates.
    """
    width, height, cy, radius = 110.0, 40.0, 38.0, 8.0
    floor = 47.0 if center else 49.0
    shelf_depth, mouth = 58.0, 66.0
    shelf_height, back_round, lip_round = 7.0, 2.5, 2.0
    # (depth, inset around the inner profile, lower-shelf intrusion).
    # The upper back edge is tapered into the deep wall; the lower edge has a
    # horizontal bearing shelf. These are unequal profiles, not nested bowls.
    sections = [(floor + back_round*(1-math.cos(i*math.pi/2/10)),
                 back_round*(1-math.sin(i*math.pi/2/10)), shelf_height)
                for i in range(11)]
    sections += [(shelf_depth-1.2, 0, shelf_height)]
    sections += [(shelf_depth-1.2+1.2*math.sin(i*math.pi/2/8),
                  0, shelf_height-1.2*(1-math.cos(i*math.pi/2/8)))
                 for i in range(1,9)]
    sections += [(shelf_depth, 0, 1.2)]
    sections += [(shelf_depth+1.2*(1-math.cos(i*math.pi/2/8)),
                  0, 1.2*(1-math.sin(i*math.pi/2/8))) for i in range(1,9)]
    sections += [(mouth-lip_round+lip_round*math.sin(i*math.pi/2/10),
                  -lip_round*(1-math.cos(i*math.pi/2/10)), 0)
                 for i in range(11)]
    sections += [(100, -lip_round, 0)]
    profiles = []
    for depth, inset, intrusion in sections:
        # A small taper of the top wall, visibly different from the flat
        # lower shelf. Keep the same analytically authored end-wall curve.
        top_taper = max(0, (shelf_depth-depth)/(shelf_depth-floor))*2.0
        profiles.append(rounded_rectangle(
            cx, cy+(intrusion-top_taper)/2,
            width-2*inset, height-intrusion-top_taper-2*inset,
            radius-inset))
    count = len(profiles[0])
    assert all(len(profile) == count for profile in profiles)
    # The rear reference is shown with the board inverted: its shelf is on
    # the small-crimp side of the barrel. A rigid half-turn around the long
    # axis preserves that relationship; reflecting only depth reverses it.
    vertices = [xyz(x, y, depth) if face_sign == 1 else
                xyz(x, DIAMETER_MM-y, DIAMETER_MM-depth)
                for (depth, _, _), profile in zip(sections, profiles)
                for x, y in profile]
    faces = [tuple(reversed(range(count))),
             tuple(range((len(sections)-1)*count, len(sections)*count))]
    faces += [(j*count+i, j*count+(i+1)%count,
               (j+1)*count+(i+1)%count, (j+1)*count+i)
              for j in range(len(sections)-1) for i in range(count)]
    # Keep the existing well ID on its back and rounded end walls. The upper
    # and lower bearing ledges remain actual wood, but have body material/role
    # because the approved inventory does not give each ledge a separate ID.
    # This selects authored surface strips, never image-derived masks/bounds.
    body_faces = set()
    for j in range(len(sections)-1):
        for i in range(count):
            a, b = profiles[j][i], profiles[j][(i+1) % count]
            if abs(a[1]-b[1]) < 1e-8 and abs(a[0]-b[0]) > 1e-8:
                body_faces.add(2+j*count+i)
    carve(body, mesh(hold_id, vertices, faces), HOLD_IDS.index(hold_id)+1,
          body_face_indices=body_faces)


def build():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # A horizontal circular billet with authored quarter-circle end rounds.
    ring_sections = [(END_ROUND_MM*(1-math.cos(i*math.pi/2/12)),
                      RADIUS_MM-END_ROUND_MM+END_ROUND_MM*math.sin(i*math.pi/2/12))
                     for i in range(13)]
    end_sections = [(WIDTH_MM-x, radius) for x, radius in reversed(ring_sections)]
    # Split the identical barrel surface through each transverse opening.
    # Otherwise multiple enclosed Boolean holes fall in one long angular
    # quad, and n-gon tessellation can cover a floor or cord passage.
    # Preserve the previous pending split through all four passage axes.
    # Additional uniform analytic sections bound each Boolean face locally;
    # they do not change the circular billet's intended surface.
    sections = sorted(set(range(5, 500, 5)) | {17, 31, 469, 483})
    ring_sections += [(x, RADIUS_MM) for x in sections]
    ring_sections += end_sections
    samples = 192
    vertices = [xyz(x, RADIUS_MM+radius*math.sin(i*2*math.pi/samples),
                       RADIUS_MM+radius*math.cos(i*2*math.pi/samples))
                for x, radius in ring_sections for i in range(samples)]
    faces = [tuple(reversed(range(samples))),
             tuple(range((len(ring_sections)-1)*samples, len(ring_sections)*samples))]
    faces += [(j*samples+i, j*samples+(i+1)%samples,
               (j+1)*samples+(i+1)%samples, (j+1)*samples+i)
              for j in range(len(ring_sections)-1) for i in range(samples)]
    body = mesh("flash-board-body", vertices, faces)
    for name in ("flash-board-wood", *HOLD_IDS):
        body.data.materials.append(material(name))

    # Three-edge face: broad shallow machined face and three independent wells.
    # The labelled photograph supports rounded rectangular mouths and rolled
    # edges; exact widths, locations, and all recess depths remain estimates.
    recess(body, "three-face-flat", 250, 38, 416, 76, 66, 76, 10, 1, 1)
    for hold_id, x in zip(HOLD_IDS[:3], (115, 250, 385)):
        stepped_edge(body, hold_id, x, center=hold_id == "three-edge-center")

    # Manufacturer and hanging views show two separated saddle-like milled
    # panels on the opposite side, with a continuous untouched central barrel.
    for hold_id, x in (("two-edge-left", 121), ("two-edge-right", 379)):
        recess(body, "two-face-saddle", x, 38, 144, 76, 66, 76, 12, 1.5, 1.5, -1)
        stepped_edge(body, hold_id, x, face_sign=-1)

    # The two outboard small contacts keep their existing IDs. Their long
    # shallow mouths lie on the shoulder above the outer three-well contacts,
    # rather than at the silhouette on the very top of the billet. The label
    # arrows and closeups support that physical placement; all values remain
    # estimates. This does not create additional lower-groove logical IDs.
    for hold_id, x in (("small-crimp-left", 115), ("small-crimp-right", 385)):
        recess(body, hold_id, x, 38, 86, 9, 72, 75.4, 2.5, .6, .6,
               hold_id=hold_id, radial_angle=62)

    # The two-well/central-logo photographs also show one long central notch
    # on the opposite shoulder. It was absent from the previous model. This
    # is nonselectable body geometry, with no new contact or depth claim.
    recess(body, "two-face-central-notch", 250, 38, 98, 9, 72, 75.4,
           2.5, .6, .6, radial_angle=242)

    # Evidence-supported paired transverse cord passages at both ends. These
    # are suspension apertures integral to the cylinder, not added hardware.
    # Diameter, drill axis, spacing, and entrance round are display estimates.
    for x in (17, 31, WIDTH_MM-31, WIDTH_MM-17):
        recess(body, "integral-cord-passage", x, 48, 6.5, 6.5,
               -8, 74.66, 3.25, .5, .6)

    active(body)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-8)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.008)
    bpy.ops.object.mode_set(mode="OBJECT")
    canonical_neutral_wood.attach_to_materials(body.data.materials)
    for poly in body.data.polygons:
        # Boolean cap n-gons are planar. Their smooth interpolation would
        # falsely bend a flat machined surface; short planar cap fragments
        # need the same rule. Polygon vertex count alone left a dark square
        # on a coplanar face beside a well. The actual rounds stay smooth.
        axis_planar = max(abs(value) for value in poly.normal) > 1-1e-7
        poly.use_smooth = len(poly.vertices) <= 4 and not axis_planar
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    model = list(bpy.context.selected_objects)
    for obj in model:
        used = {poly.material_index for poly in obj.data.polygons}
        assert len(used) == 1
        name = obj.data.materials[next(iter(used))].name
        if name in HOLD_IDS:
            obj.name = name
            obj["role"] = "hold"
            obj["hold_id"] = name
        else:
            obj.name = "flash-board-body"
            obj["role"] = "body"
        obj["display_estimate"] = True
        obj["geometry_provenance"] = "approved visual evidence; authored numeric estimates"
    assert len(model) == 8
    assert {obj.get("hold_id") for obj in model if obj["role"] == "hold"} == set(HOLD_IDS)
    return model


def render_review(output, model):
    """Inspection cameras/lights are transient, never saved or exported."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.world.color = (.45, .45, .45)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    camera_data = bpy.data.cameras.new("Transient shape review")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Transient shape review", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    for name, position, energy in (("Front review light", (.08,-.4,.4), 12),
                                    ("Rear review light", (.42,.3,.3), 9),
                                    ("Reverse pose review light", (.42,.3,-.3), 9)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = .4
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (Vector(xyz(250,38,38))-obj.location).to_track_quat("-Z", "Y").to_euler()
    clay = material("Transient clay")
    clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.38,.42,.46,1)
    views = (
        ("front", (.25,-.8,.038), (250,38,38), .57, False),
        ("three-quarter", (.49,-.8,.28), (250,38,38), .57, False),
        ("opposite-face", (.25,.8,.038), (250,38,38), .57, False),
        ("opposite-three-quarter", (.02,.8,-.204), (250,38,38), .57, False),
        ("upper-barrel", (.25,-.16,.65), (250,38,38), .57, True),
        ("clay-detail", (.11,-.35,.14), (112,36,65), .19, True),
        ("attachment-region", (-.12,-.32,.22), (24,44,38), .13, True),
        ("opposite-notch-detail", (.25,.34,-.18), (250,8,24), .16, True),
    )
    output.mkdir(exist_ok=True)
    for name, location, target, scale, is_clay in views:
        camera.location = location
        camera.rotation_euler = (Vector(xyz(*target))-camera.location).to_track_quat("-Z", "Y").to_euler()
        if name.startswith("opposite"):
            camera.rotation_euler.rotate_axis("Z", math.pi)
        camera_data.ortho_scale = scale
        scene.view_layers[0].material_override = clay if is_clay else None
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override = None
    for obj in list(scene.objects):
        if obj not in model:
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / ".context" / f"{ROOT.name}-tension-flash-board")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "geometry-ownership.json").write_text(json.dumps({
        "owner": ROOT.name, "output": str(output), "externalResources": [],
        "retainedArtifacts": ["flash-board.blend", "geometry-report.json", "renders/"],
    }, indent=2)+"\n")
    actual_ids = {hold["id"] for hold in json.loads(
        (ROOT / "Hangboards/tension-flash-board/board.json").read_text())["holds"]}
    assert actual_ids == set(HOLD_IDS), "Logical inventory changed; re-review geometry contract"
    model = build()
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "flash-board.blend"))
    (output / "geometry-report.json").write_text(json.dumps({
        "owner": ROOT.name, "board": "tension.flash-board", "geometryRevision": 9,
        "coordinateFrame": "hang-ten-board-v1 after standard compiler axis transport",
        "estimatedDimensionsMM": {"width": WIDTH_MM, "diameter": DIAMETER_MM},
        "sourcedDimensionsMM": {}, "numericGeometryIsEstimated": True,
        "holdIDs": list(HOLD_IDS), "bodyMeshes": 1, "holdMeshes": 7,
        "attachmentMeshes": 0, "cordPassages": 4,
        "attachmentEligibleSourceNode": "flash-board-body",
        "nonSelectableFeatures": ["upper and lower well ledge strips", "two-face-central-notch",
                                  "four integral cord passage surfaces", "machined face panels"],
        "estimatedPassageAxesInBoardMM": [
            {"x": x, "y": 48, "axis": "+Z", "radius": 3.25}
            for x in (17,31,469,483)],
        "sourceTriangleEquivalent": sum(len(p.vertices)-2 for o in model for p in o.data.polygons),
        "evidenceAudit": "docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md",
        "approvedSnapshots": ["sources/manufacturer-front.png", "sources/commerce-hanging.jpg",
                              "sources/commerce-labelled-faces.jpg"],
        "userCloseupsReviewed": [
            "sources/user-closeup-front-cord-and-wells.png",
            "sources/user-closeup-end-attachment.png",
            "sources/user-closeup-opposite-face.png",
            "sources/user-closeup-three-well-face.png",
            "sources/user-closeup-two-well-face.png",
            "sources/user-closeup-two-well-face-wide.png"],
        "visualEvidenceCorrections": [
            "user-closeup-two-well-face-wide.png visibly shows three wells in an inverted orientation",
            "user-closeup-opposite-face.png shows three wells; opposite is a viewpoint label only"],
        "limitations": [
            "Not manufacturing CAD: every dimension, recess depth, radius and placement is estimated",
            "Published global edge sizes are not assigned to particular contact IDs",
            "Paired transverse passage geometry is estimated; no exact internal drill path is sourced",
            "No cord, knots, anchor, hardware, logo or mounting environment",
            "Canonical poses, camera metadata and runtime attachment point are outside geometry scope",
            "Source review does not establish actual USDZ or native-renderer verification",
        ],
    }, indent=2)+"\n")
    if args.render:
        render_review(output / "renders", model)
    print("FLASH_BOARD_SOURCE", output / "flash-board.blend")


if __name__ == "__main__":
    main()
