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


ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT / ".context/epic-whale-wood-grips-compact-ii")
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


def bevel(obj, width, segments=3):
    mod = obj.modifiers.new("Hand-selected soft edge radius", "BEVEL")
    mod.width = width / 1000
    mod.segments = segments
    apply(obj, mod)


def extrude(name, outline, back, front):
    n = len(outline)
    verts = [xyz(x, y, d) for d in (back, front) for x, y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces += [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)]
    obj = mesh(name, verts, faces)
    active(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = .6
    return mat


wood = material("Pale timber • baked grain", (.69, .49, .28))
hold_ids = [h["id"] for h in json.loads((ROOT / "Hangboards/metolius-wood-grips-compact-ii/board.json").read_text())["holds"]]
hold_mats = {name: material(name, (.69, .49, .28)) for name in hold_ids}

# Explicitly drawn symmetric outer profile; coordinates/radii are visual estimates.
# The inset shoulders on the upper outline are the two flat-sloper channels.
left = [(305,151), (198,151), (194,150), (192,146), (110,146),
        (104,151), (99,157), (26,157), (10,154), (2,146), (0,138),
        (3,125), (9,110), (14,91), (16,77), (15,72), (18,65),
        (22,53), (25,20), (24,13), (27,6), (35,1), (46,0), (305,0)]
outline = left + [(610-x, y) for x,y in reversed(left[1:-1])]
def top_profile(x, h, d):
    if h <= 132:
        return h
    mirrored_x=min(x,610-x)
    if mirrored_x < 104:  # outer rounded jug
        t=max(0,(d-23)/33)
        drop=(h-134)*(1-math.sqrt(max(0,1-t*t)))
    elif mirrored_x < 196:  # planar flat-sloper channel
        drop=5*d/56
    else:  # broad rounded central sloper
        t=d/56
        drop=(h-133)*(1-math.sqrt(max(0,1-t*t)))
    return h-drop

depth_rings=[0,7,14,21,28,35,42,47,51,54,56]
n=len(outline)
verts=[xyz(x,top_profile(x,h,d),d) for d in depth_rings for x,h in outline]
faces=[tuple(reversed(range(n))),tuple(range((len(depth_rings)-1)*n,len(depth_rings)*n))]
faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
          for j in range(len(depth_rings)-1) for i in range(n)]
body=mesh("Wood Grips Compact II",verts,faces)
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
body.data.materials.append(wood)
for mat in hold_mats.values():
    body.data.materials.append(mat)
bevel(body, 3.0, 4)


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
    bpy.data.objects.remove(cutter, do_unlink=True)


def capsule(cx, cy, width, height, radius=None):
    r = min(width, height) / 2 if radius is None else radius
    points = []
    for xx, yy, start in [(cx+width/2-r,cy+height/2-r,0),
                          (cx-width/2+r,cy+height/2-r,90),
                          (cx-width/2+r,cy-height/2+r,180),
                          (cx+width/2-r,cy-height/2+r,270)]:
        for i in range(9):
            theta = math.radians(start+i*90/8)
            points.append((xx+r*math.cos(theta), yy+r*math.sin(theta)))
    clean=[]
    for point in points:
        if not clean or math.dist(point,clean[-1])>1e-6:
            clean.append(point)
    if math.dist(clean[0],clean[-1])<1e-6:
        clean.pop()
    return clean


def recess(name, cx, cy, width, height, depth, radius=None):
    # Rounded transition into the back wall, through an explicit four-ring cutter.
    rings = [(56-depth, 4), (56-depth+2, 1.4), (56-depth+5, 0),
             (53,0),(55,-.6),(56,-2),(76,-2)]
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
# The lower row is slightly inset to follow the board's tapered ends.
for depth, cy, outer, inner, outer_w, inner_w in [(29,88,151,221,66,46),(19,29,161,227,66,46)]:
    for side, sign in [("left",1),("right",-1)]:
        x=lambda v: v if sign==1 else 610-v
        recess(f"pocket-{depth}-three-{side}",x(outer),cy,outer_w,25,depth)
        recess(f"pocket-{depth}-two-{side}",x(inner),cy,inner_w,25,depth)
    recess(f"pocket-{depth}-four-center",305,cy,96,25,depth)

# Outer edges open through the side of the board, as shown in both references.
for depth,cy,w,h,cx in [(29,102,131,56,39),(19,34,139,43,43)]:
    for side,x in [("left",cx),("right",610-cx)]:
        recess(f"edge-{depth}-{side}",x,cy,w,h,depth,8)

# Six production mounting holes are visible in the primary photograph.
for x,h in [(113,110),(253,110),(363,110),(500,110),(125,49),(487,49)]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0023,depth=.09,
        location=xyz(x,h,28),rotation=(math.pi/2,0,0))
    subtract(bpy.context.object)
    bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.0023,radius2=.0046,depth=.004,
        location=xyz(x,h,55),rotation=(math.pi/2,0,0))
    subtract(bpy.context.object)

bevel(body, 2.0, 4)

# Partition actual top contact faces into the five existing top hold IDs.
for poly in body.data.polygons:
    if poly.material_index != 0:
        continue
    center=poly.center
    x=center.x*1000+305
    h=center.z*1000
    if h>132 and poly.normal.z>.20:
        name=("jug-left" if x<106 else "sloper-flat-left" if x<196 else
              "sloper-round-center" if x<414 else "sloper-flat-right" if x<504 else "jug-right")
        poly.material_index=list(hold_mats).index(name)+1

# Bake the same continuous procedural timber onto a shared UV atlas; exported
# GLB/USDZ use standard image-textured PBR, not Blender-only procedural nodes.
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.008)
bpy.ops.object.mode_set(mode="OBJECT")
atlas=bpy.data.images.new("Compact II pale timber",width=2048,height=2048)
atlas.filepath_raw=str(OUT/"wood-basecolor.png")
atlas.file_format="PNG"
for mat in body.data.materials:
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    tex=nodes.new("ShaderNodeTexCoord")
    stretch=nodes.new("ShaderNodeVectorMath")
    stretch.operation="MULTIPLY"
    stretch.inputs[1].default_value=(5,100,75)
    links.new(tex.outputs["Position"] if "Position" in tex.outputs else tex.outputs["Generated"],stretch.inputs[0])
    noise=nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=1
    noise.inputs["Detail"].default_value=3
    noise.inputs["Roughness"].default_value=.66
    links.new(stretch.outputs[0],noise.inputs["Vector"])
    ramp=nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position=.18
    ramp.color_ramp.elements[0].color=(.45,.30,.155,1)
    ramp.color_ramp.elements[1].position=.83
    ramp.color_ramp.elements[1].color=(.79,.64,.42,1)
    links.new(noise.outputs["Fac"],ramp.inputs[0])
    links.new(ramp.outputs[0],nodes.get("Principled BSDF").inputs["Base Color"])
    target=nodes.new("ShaderNodeTexImage")
    target.image=atlas
    nodes.active=target

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=16
scene.render.bake.use_pass_direct=False
scene.render.bake.use_pass_indirect=False
scene.render.bake.use_pass_color=True
scene.render.bake.margin=12
bpy.ops.object.bake(type="DIFFUSE")
atlas.save()
atlas.pack()
for mat in body.data.materials:
    nodes=mat.node_tree.nodes
    target=next(n for n in nodes if n.type=="TEX_IMAGE")
    bsdf=nodes.get("Principled BSDF")
    mat.node_tree.links.new(target.outputs["Color"],bsdf.inputs["Base Color"])
    for n in list(nodes):
        if n not in (target,bsdf,nodes.get("Material Output")):
            nodes.remove(n)

# Split by material so each true carved contact is independently selectable.
active(body)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="MATERIAL")
bpy.ops.object.mode_set(mode="OBJECT")
model=list(bpy.context.selected_objects)
for obj in model:
    used=sorted({p.material_index for p in obj.data.polygons})
    mat=obj.data.materials[used[0]]
    obj.name=mat.name if mat.name in hold_ids else "wood-body"
    obj["display_estimate"]=True
    if obj.name in hold_ids:
        obj["hold_id"]=obj.name
    for poly in obj.data.polygons:
        poly.use_smooth=True
    normals=obj.modifiers.new("Weighted surface normals","WEIGHTED_NORMAL")
    normals.keep_sharp=True
    apply(obj,normals)

def select_model():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in model:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=model[0]

select_model()
bpy.ops.export_scene.gltf(filepath=str(OUT/"wood-grips-compact-ii.glb"),export_format="GLB",
    use_selection=True,export_extras=True,export_cameras=False,export_lights=False)
bpy.ops.wm.usd_export(filepath=str(OUT/"wood-grips-compact-ii.usdz"),selected_objects_only=True,
    export_materials=True,generate_preview_surface=True)

report={"owner":ROOT.name,"model":"metolius.wood-grips-compact-ii","units":"meters",
    "source_dimensions_mm":{"width":610,"height":157},"display_estimate_depth_mm":56,
    "hold_ids":sorted(o.name for o in model if o.name in hold_ids),
    "hold_count":sum(o.name in hold_ids for o in model),
    "mesh_count":len(model),"triangles":sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in model),
    "texture_resolution":[2048,2048],"estimated_geometry":True,
    "limitations":["Display only, not manufacturing geometry","Widths, placement, radii, side and back profiles estimated from manufacturer images","Not installed into the Hang Ten runtime or canonical board package"]}
assert report["hold_ids"]==sorted(hold_ids),report
assert report["triangles"]<80000,report
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
select_model()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"wood-grips-compact-ii.blend"))
print("MODEL_REPORT",json.dumps(report))
