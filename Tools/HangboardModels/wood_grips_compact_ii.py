"""Manually authored, evidence-referenced display model; not fabrication geometry.

Run from repo root with Blender --background --python this_file -- --output DIR.
No image is read by this script. See README.md for provenance and estimates.
"""
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


ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT / ".context" / f"{ROOT.name}-wood-grips-compact-ii")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ownership.json").write_text(json.dumps({"owner": ROOT.name, "resources": [str(OUT)], "external_resources": []}, indent=2))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def xyz(x, h, d):
    """Millimeters, left-origin width, bottom-origin height, depth from back."""
    return ((x - 305) / 1000, -d / 1000, h / 1000)


def mesh(name, verts, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply(obj, modifier):
    active(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = .6
    return mat


wood = material("wood_body_material", (.69, .49, .28))
hold_ids = [h["id"] for h in json.loads((ROOT / "Hangboards/metolius-wood-grips-compact-ii/board.json").read_text())["holds"]]
hold_mats = {name: material(name, (.69, .49, .28)) for name in hold_ids}

# Only the 610 × 157 mm face and contact-specific depth labels are sourced.
# The approved Bergfreunde oblique supports a substantial rounded top section,
# not a measured overall thickness. 64 mm is an independent display estimate.
BODY_DEPTH_MM = 64.0
SLOPER_CONTACT_DEPTH_MM = 56.0  # Official Compact diagram #2 and #9 only.
SLOPER_BACK_START_MM = BODY_DEPTH_MM - SLOPER_CONTACT_DEPTH_MM

# Cubic silhouette spans are deliberately drawn from the manufacturer photograph.
# Their control points, roundover radius and all unseen sections are estimates.
def cubic(p0, p1, p2, p3, steps=8):
    return [tuple((1-t)**3*p0[k]+3*(1-t)**2*t*p1[k]
                  +3*(1-t)*t*t*p2[k]+t**3*p3[k] for k in range(2))
            for t in [i/steps for i in range(steps)]]

spans = [
    ((305,151),(268,151),(228,151),(204,151)),
    ((204,151),(197,151),(198,146),(190,146)),
    ((190,146),(163,146),(133,146),(111,146)),
    ((111,146),(103,146),(103,157),(94,157)),
    ((94,157),(72,157),(44,157),(29,155)),
    ((29,155),(10,153),(0,148),(0,139)),
    ((0,139),(0,128),(14,110),(16,88)),
    ((16,88),(18,76),(13,75),(16,68)),
    ((16,68),(20,62),(23,52),(24,40)),
    ((24,40),(26,25),(26,20),(25,15)),
    ((25,15),(23,6),(34,0),(48,0)),
    ((48,0),(112,0),(222,0),(305,0)),
]
left=[point for span in spans for point in cubic(*span)] + [(305,0)]
outline=left + [(610-x,h) for x,h in reversed(left[1:-1])]
n=len(outline)
# Unit inward normals to this counterclockwise silhouette provide an explicit
# body roundover, independent of tiny edges introduced later by the Booleans.
inward=[]
for i in range(n):
    prev,after=outline[(i-1)%n],outline[(i+1)%n]
    dx,dh=after[0]-prev[0],after[1]-prev[1]
    length=math.hypot(dx,dh)
    inward.append((-dh/length,dx/length))

def smoothstep(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)

def top_profile(x,h,d):
    if h<=132:
        return h
    mirrored_x=min(x,610-x)
    # The outer jugs have a broad plateau followed by a continuous front roll.
    # Flat slopers have a shallow pitched plane; the central sloper has a
    # continuous convex section. Heights, pitch and roll radii are estimates.
    jug_t=max(0,min(1,(d-(BODY_DEPTH_MM-34))/34))
    sloper_t=max(0,min(1,(d-SLOPER_BACK_START_MM)/SLOPER_CONTACT_DEPTH_MM))
    jug_drop=18*(h-132)/25*(1-math.sqrt(max(0,1-jug_t*jug_t)))
    flat_drop=8*(h-132)/14*sloper_t
    center_drop=16*(h-132)/19*(1-math.sqrt(max(0,1-sloper_t*sloper_t)))
    jug_mix=smoothstep(99,113,mirrored_x)
    center_mix=smoothstep(185,204,mirrored_x)
    drop=(jug_drop*(1-jug_mix)+flat_drop*jug_mix)*(1-center_mix)+center_drop*center_mix
    return h-drop

# Angular sampling resolves the near-vertical ends of circular rolls. Front
# and back roundovers are actual geometry, not shading or a global bevel.
depth_rings=sorted(set([0,.25,.6,1.2,2,3,5,7,8,10,14,20,26,30,34,40,46,52]
                     + [BODY_DEPTH_MM*math.sin(i*math.pi/2/48) for i in range(1,49)]))
verts=[]
for d in depth_rings:
    for (x,h),(nx,nh) in zip(outline,inward):
        # The bottom rail allows a broad 7 mm roll. Concave top channels need
        # 2 mm so their inward offset does not cross the shoulder curvature.
        radius=7-5*smoothstep(15,40,h)
        inset=(2-math.sqrt(max(0,4-(d-2)**2)) if d<2 else
               radius-math.sqrt(max(0,radius**2-(d-(BODY_DEPTH_MM-radius))**2))
               if d>BODY_DEPTH_MM-radius else 0)
        verts.append(xyz(x+nx*inset,top_profile(x,h,d)+nh*inset,d))
faces=[tuple(reversed(range(n))),tuple(range((len(depth_rings)-1)*n,len(depth_rings)*n))]
# Choose matching reflected diagonals for the authored curved body strips.
# Across sloper/jug blends these quads are not planar. Letting a renderer pick
# the same winding-relative diagonal on both sides makes different physical
# facets despite identical mirrored control points.
for j in range(len(depth_rings)-1):
    for i in range(n):
        a,b,c,d = j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i
        if outline[i][0]+outline[(i+1)%n][0] <= 610:
            faces += [(a,b,c),(a,c,d)]
        else:
            faces += [(a,b,d),(b,c,d)]
body=mesh("Wood Grips Compact II",verts,faces)
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
body.data.materials.append(wood)
for mat in hold_mats.values():
    body.data.materials.append(mat)


def subtract(cutter, hold_id=None):
    cutter.data.materials.clear()
    for mat in body.data.materials:
        cutter.data.materials.append(mat)
    if hold_id:
        idx = list(hold_mats).index(hold_id) + 1
        for poly in cutter.data.polygons:
            poly.material_index = idx
    mod = body.modifiers.new("Carve " + (hold_id or cutter.name), "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    apply(body, mod)
    assert body.data.polygons, f"Carving {hold_id or cutter.name} removed the body"
    bpy.data.objects.remove(cutter, do_unlink=True)


def capsule(cx, cy, width, height, radius=None):
    r = min(width, height) / 2 if radius is None else radius
    points = []
    for xx, yy, start in [(cx+width/2-r,cy+height/2-r,0),
                          (cx-width/2+r,cy+height/2-r,90),
                          (cx-width/2+r,cy-height/2+r,180),
                          (cx+width/2-r,cy-height/2+r,270)]:
        for i in range(17):
            theta = math.radians(start+i*90/16)
            points.append((xx+r*math.cos(theta), yy+r*math.sin(theta)))
    clean=[]
    for point in points:
        if not clean or math.dist(point,clean[-1])>1e-6:
            clean.append(point)
    if math.dist(clean[0],clean[-1])<1e-6:
        clean.pop()
    return clean


def recess(name, cx, cy, width, height, depth, radius=None):
    # Two tangent quarter-circle fillets: back-to-wall and wall-to-front.
    # Shelves get the visibly fuller rolled rail radius seen in the photograph.
    back_r=6.0 if name.startswith("edge-") else 4.5
    mouth_r=6.0 if name.startswith("edge-") else 3.5
    rings=[(BODY_DEPTH_MM-depth+back_r*(1-math.cos(i*math.pi/2/12)),
            back_r*(1-math.sin(i*math.pi/2/12))) for i in range(13)]
    rings += [(BODY_DEPTH_MM-mouth_r+mouth_r*math.sin(i*math.pi/2/12),
               -mouth_r*(1-math.cos(i*math.pi/2/12))) for i in range(13)]
    rings += [(BODY_DEPTH_MM+20,-mouth_r)]
    profiles = [capsule(cx,cy,width-inset*2,height-inset*2,
                        max(1,(radius if radius else min(width,height)/2)-inset))
                for _,inset in rings]
    n=len(profiles[0])
    verts=[xyz(x,y,d) for (d,_),points in zip(rings,profiles) for x,y in points]
    faces=[tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
              for j in range(len(rings)-1) for i in range(n)]
    cut=mesh(name+" cutter",verts,faces)
    active(cut)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    subtract(cut,name)


# Explicit pocket layouts read visually from the official Compact photograph.
# The lower row is slightly inset to follow the board's tapered ends. Its
# narrower mouths leave continuous wood between every adjacent pair, including
# both two-finger pockets and the centre pocket. All aperture sizes/positions
# are authored estimates; the 29/19 mm contact depth labels remain source facts.
POCKET_LAYOUT = [(29,88,151,221,66,46),(19,29,161,224.5,62,39)]
for depth, cy, outer, inner, outer_w, inner_w in POCKET_LAYOUT:
    for side, sign in [("left",1),("right",-1)]:
        x=lambda v: v if sign==1 else 610-v
        recess(f"pocket-{depth}-three-{side}",x(outer),cy,outer_w,25,depth)
        recess(f"pocket-{depth}-two-{side}",x(inner),cy,inner_w,25,depth)
    recess(f"pocket-{depth}-four-center",305,cy,96,25,depth)

# Outer edges open through the side of the board, as shown in both references.
# Their inner ends leave at least 10 mm of wood before the outer pocket mouths;
# both approved views show a complete ligament at this stepped transition.
for depth,cy,w,h,cx in [(29,98,119,48,39),(19,34,131,43,43)]:
    for side,x in [("left",cx),("right",610-cx)]:
        recess(f"edge-{depth}-{side}",x,cy,w,h,depth,8)

# The six mounting holes visible in the primary photograph are deliberately
# omitted from this display model at the user's request.

# Do not bevel the Boolean result: tiny intersection edges clamp global bevels
# and destroy intentional cross-sections. Every contact fillet is authored above.
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=.0000001)
bpy.ops.object.mode_set(mode="OBJECT")

# Partition actual top contact faces into the five existing top hold IDs.
for poly in body.data.polygons:
    if poly.material_index != 0:
        continue
    center=poly.center
    x=center.x*1000+305
    h=center.z*1000
    if h>126 and poly.normal.z>.12:
        name=("jug-left" if x<106 else "sloper-flat-left" if x<196 else
              "sloper-round-center" if x<414 else "sloper-flat-right" if x<504 else "jug-right")
        poly.material_index=list(hold_mats).index(name)+1

# Preserve the authored UVs while binding the shared source image. Exported
# USDZs remain self-contained because the exact committed PNG is packed.
if not body.data.uv_layers:
    body.data.uv_layers.new(name="UVMap")
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.008)
bpy.ops.object.mode_set(mode="OBJECT")
canonical_neutral_wood.attach_to_materials(body.data.materials)
scene=bpy.context.scene

# Large Boolean cap faces remain mathematically flat, avoiding pinched shading
# around recesses. Dense curved strips use ordinary interpolated normals;
# weighted normals can introduce triangular artifacts on Boolean cap topology.
for poly in body.data.polygons:
    poly.use_smooth=True
for poly in body.data.polygons:
    if len(poly.vertices)>4:
        origin=body.data.vertices[poly.vertices[0]].co
        if all(abs((body.data.vertices[v].co-origin).dot(poly.normal))<1e-7
               for v in poly.vertices):
            poly.use_smooth=False

# Split by material so each true carved contact is independently selectable.
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="MATERIAL")
bpy.ops.object.mode_set(mode="OBJECT")
model=list(bpy.context.selected_objects)


def tag_model_piece(obj, known_hold_ids):
    """Attach the closed compiler contract without deriving any geometry."""
    if obj.name in known_hold_ids:
        obj["role"]="hold"
        obj["hold_id"]=obj.name
    else:
        obj["role"]="body"


def discard_render_only_scene_objects(scene_objects, model_objects, remove_object):
    """Keep review-only wall/camera/light objects out of editable compiler input."""
    for obj in list(scene_objects):
        if obj not in model_objects:
            remove_object(obj)


for obj in model:
    used=sorted({p.material_index for p in obj.data.polygons})
    mat=obj.data.materials[used[0]]
    obj.name=mat.name if mat.name in hold_ids else "wood-body"
    obj["display_estimate"]=True
    tag_model_piece(obj, hold_ids)

def select_model():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in model:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=model[0]

select_model()
bpy.ops.export_scene.gltf(filepath=str(OUT/"wood-grips-compact-ii.glb"),export_format="GLB",
    use_selection=True,export_extras=True,export_cameras=False,export_lights=False)
# SceneKit misimports complex Boolean cap n-gons: explicit export triangles
# preserve the intended cavities and per-face material bindings. These temporary
# modifiers leave the editable source mesh and its vertex positions unchanged.
usd_triangulators=[]
for obj in model:
    modifier=obj.modifiers.new("Portable USD triangles","TRIANGULATE")
    modifier.quad_method="FIXED"
    modifier.ngon_method="BEAUTY"
    usd_triangulators.append((obj,modifier))
bpy.ops.wm.usd_export(filepath=str(OUT/"wood-grips-compact-ii.usdz"),selected_objects_only=True,
    export_materials=True,generate_preview_surface=True)
for obj,modifier in usd_triangulators:
    obj.modifiers.remove(modifier)

report={"owner":ROOT.name,"model":"metolius.wood-grips-compact-ii","units":"meters",
    "source_dimensions_mm":{"width":610,"height":157},
    "display_estimate_body_depth_mm":BODY_DEPTH_MM,
    "source_sloper_contact_depth_mm":SLOPER_CONTACT_DEPTH_MM,
    "hold_ids":sorted(o.name for o in model if o.name in hold_ids),
    "hold_count":sum(o.name in hold_ids for o in model),
    "mesh_count":len(model),"triangles":sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in model),
    "texture_resolution":[canonical_neutral_wood.WIDTH,canonical_neutral_wood.HEIGHT],"estimated_geometry":True,
    "canonical_texture":canonical_neutral_wood.CANONICAL_TEXTURE_NAME,
    "canonical_texture_sha256":canonical_neutral_wood.hashlib.sha256(canonical_neutral_wood.CANONICAL_TEXTURE_PATH.read_bytes()).hexdigest(),
    "geometry_revision":4,"body_depth_rings":len(depth_rings),
    "mounting_holes_omitted":True,"mounting_hole_count":0,
    "pocket_fillet_segments":12,"silhouette_cubic_spans":24,
    "limitations":["Display only, not manufacturing geometry","Widths, placement, radii, side and back profiles estimated from manufacturer images","Six physical mounting holes deliberately omitted at user request for app display","Generated exports require validation and an explicit app bundle refresh; canonical 2D paths remain in use for editor and fallback"]}
assert report["hold_ids"]==sorted(hold_ids),report
assert report["triangles"]<150000,report
(OUT/"model-report.json").write_text(json.dumps(report,indent=2)+"\n")

# Neutral studio wall, deliberately separate from selected exportable geometry.
wall=material("Warm white studio",(.89,.88,.85))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,.015,0),rotation=(math.pi/2,0,0))
bpy.context.object.name="Studio wall — render only"
bpy.context.object.data.materials.append(wall)
scene.world.color=(.35,.35,.35)
def light(name,location,power,size):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power
    data.shape="DISK"
    data.size=size
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector((0,-.028,.078))-obj.location).to_track_quat("-Z","Y").to_euler()
light("Large soft key",(-.28,-.40,.55),10,.50)
light("Soft fill",(.38,-.25,.20),3,.40)
cam_data=bpy.data.cameras.new("Review camera")
cam=bpy.data.objects.new("Review camera",cam_data)
bpy.context.collection.objects.link(cam)
scene.camera=cam
cam_data.type="ORTHO"
cam_data.ortho_scale=.76
scene.render.resolution_x=1800
scene.render.resolution_y=750
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.view_settings.view_transform="AgX"
def render(name,location):
    cam.location=location
    cam.rotation_euler=(Vector((0,-.028,.0785))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(OUT/name)
    bpy.ops.render.render(write_still=True)
render("front.png",(0,-1,.0785))
render("three-quarter.png",(.31,-1,.34))
clay=material("Geometry review clay",(.38,.42,.46))
scene.view_layers[0].material_override=clay
render("clay-three-quarter.png",(.31,-1,.34))
cam_data.ortho_scale=.34
scene.render.resolution_x=1500
scene.render.resolution_y=1100
cam.location=(-.43,-.58,.36)
cam.rotation_euler=(Vector((-.175,-.028,.086))-cam.location).to_track_quat("-Z","Y").to_euler()
scene.render.filepath=str(OUT/"clay-detail.png")
bpy.ops.render.render(write_still=True)
scene.view_layers[0].material_override=None
cam_data.ortho_scale=.76
scene.render.resolution_x=1800
scene.render.resolution_y=750
highlight=material("Selection amber",(.94,.35,.035))
selected=[]
for obj in model:
    if obj.name in ["pocket-29-three-left","pocket-29-three-right"]:
        selected.append((obj,list(obj.data.materials)))
        for i in range(len(obj.data.materials)):
            obj.data.materials[i]=highlight
render("selected-holds.png",(.31,-1,.34))
for obj,mats in selected:
    for i,mat in enumerate(mats):
        obj.data.materials[i]=mat
discard_render_only_scene_objects(
    bpy.context.scene.objects,
    model,
    lambda obj: bpy.data.objects.remove(obj, do_unlink=True),
)
select_model()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"wood-grips-compact-ii.blend"))
print("MODEL_REPORT",json.dumps(report))
