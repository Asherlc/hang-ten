"""Rebuild editable grip poses from the bundled MIT WebXR source. Blender 5.2."""
import bpy, bmesh, math, runpy
from mathutils import Vector, Quaternion, Matrix
from pathlib import Path
HERE = Path(__file__).resolve().parent
DIGITS = ("index", "middle", "ring", "pinky")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HERE / "SourceHand.glb"))
rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
mesh = bpy.data.objects["r_handMeshNode"]
for o in list(bpy.context.scene.objects):
    if o not in (rig, mesh): bpy.data.objects.remove(o, do_unlink=True)
rig.name = "GripHandRig"; mesh.name = "GripHandSurface"
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
# Imported WebXR joint transforms are flat siblings. Reparent without moving
# their supplied rest matrices; retain every source vertex deform weight.
for digit in ["thumb"] + [d + "-finger" for d in DIGITS]:
    suffixes = ["metacarpal", "phalanx-proximal"] + ([] if digit == "thumb" else ["phalanx-intermediate"]) + ["phalanx-distal", "tip"]
    names = [digit + "-" + s for s in suffixes]
    for i, name in enumerate(names):
        b = rig.data.edit_bones[name]; matrix = b.matrix.copy()
        b.parent = rig.data.edit_bones[names[i-1] if i else "wrist"]
        b.use_connect = False; b.matrix = matrix
bpy.ops.object.mode_set(mode="OBJECT")
for mod in mesh.modifiers:
    if mod.type == "ARMATURE": mod.use_deform_preserve_volume = False
bm = bmesh.new(); bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
bmesh.ops.join_triangles(bm, faces=list(bm.faces), angle_face_threshold=math.radians(45), angle_shape_threshold=math.radians(60), cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=False)
crease = bm.edges.layers.float.new("crease_edge")
for e in bm.edges:
    e.smooth = True
    if all(v.co.z > .04 for v in e.verts) and len(e.link_faces) == 2 and e.calc_face_angle() > math.radians(45): e[crease] = 1
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
mesh.data.normals_split_custom_set([(0,0,0)] * len(mesh.data.loops))
for p in mesh.data.polygons: p.use_smooth = True
# Continuous masks subdivide with the surface. Finger metacarpal weights do
# not color the palm; source phalanx weights identify the actual digits.
groups = {g.index:g.name for g in mesh.vertex_groups}
for digit in ["thumb"] + list(DIGITS):
    attr = mesh.data.attributes.new("highlight_" + digit, "FLOAT", "POINT")
    for v in mesh.data.vertices:
        strength = sum(g.weight for g in v.groups if groups[g.group].startswith(digit + ("-" if digit == "thumb" else "-finger-")) and ("phalanx" in groups[g.group] or groups[g.group].endswith("tip")))
        attr.data[v.index].value = min(1, strength)
sub = mesh.modifiers.new("Surface smoothing AFTER posing", "SUBSURF")
sub.levels = 2; sub.render_levels = 2

def bend(digit, suffix, degrees, spread=0):
    p = rig.pose.bones[digit + "-finger-phalanx-" + suffix]; b = p.bone
    nxt = {"proximal":"intermediate", "intermediate":"distal", "distal":"tip"}[suffix]
    end = rig.data.bones[digit + "-finger-" + ("tip" if nxt == "tip" else "phalanx-" + nxt)].head_local
    axis = (end - b.head_local).normalized().cross(Vector((-1,0,0))).normalized()
    inverse = b.matrix_local.to_quaternion().inverted()
    p.rotation_quaternion = Quaternion(inverse @ Vector((1,0,0)), math.radians(spread)) @ Quaternion(inverse @ axis, math.radians(degrees))

# These are illustrative artist controls, NOT measured anatomical joint angles.
# HalfCrimp keeps the shared support-plane fit and clearly bends all four fingers.
HALF = [(2,84,0,-2),(1.75,91,0,-1),(-2,75,0,6),(-10.75,60,0,10)]
POCKET_OPEN = [(8,12,8,-2),(8,40,8,-1),(8,35,8,6),(12,8,5,10)]
# The open-hand index has a visible, gentle middle-joint bend. Pocket contact
# controls stay independent so this illustration change cannot alter selections.
OPEN = [(8,35,8,-2),(8,40,8,-1),(8,35,8,6),(12,8,5,10)]
# Tighter middle joints and modest distal extension distinguish the full crimp
# from the flatter half-crimp shelf while keeping the thumb at rest.
FULL = [(8,118,-15,-2),(8,120,-15,-1),(6,115,-15,6),(8,95,-12,10)]
SLOPER = [(18,22,12,-2),(18,26,12,-1),(18,24,12,6),(18,20,10,10)]
TUCKED = [(55,78,28,-2),(55,78,28,-1),(55,78,28,6),(55,78,28,10)]
poses = {"Neutral": [(0,0,0,0)]*4, "OpenHand": OPEN, "HalfCrimp": HALF, "FullCrimp": FULL, "Sloper": SLOPER}
for mask in range(16): poses[f"Pocket{mask}"] = [POCKET_OPEN[i] if mask == 0 or mask & (1 << i) else TUCKED[i] for i in range(4)]
rig.animation_data_create()
for name, controls in poses.items():
    rig.animation_data.action = bpy.data.actions.new(name)
    rig.animation_data.action.use_fake_user = True
    for p in rig.pose.bones:
        p.rotation_mode = "QUATERNION"; p.rotation_quaternion = Quaternion()
    for digit, (mcp,pip,dip,spread) in zip(DIGITS, controls):
        bend(digit,"proximal",mcp,spread); bend(digit,"intermediate",pip); bend(digit,"distal",dip)
    for p in rig.pose.bones: p.keyframe_insert(data_path="rotation_quaternion", frame=1)
# Every thumb bone intentionally remains at supplied rest in every action.
rig.animation_data.action = bpy.data.actions["HalfCrimp"]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
bpy.context.scene.frame_set(1)
mat = bpy.data.materials.new("Matte grip hand"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.34,.41,.39,1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
mesh.data.materials.clear(); mesh.data.materials.append(mat)
scene = bpy.context.scene; scene.render.engine = "CYCLES"; scene.cycles.samples = 32
scene.world = bpy.data.worlds.new("Grip studio"); scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.38,.41,.4,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = .6
for loc,power,size in [((.25,.1,-.15),2.4,.25),((-.2,-.1,-.2),1.4,.3),((.1,-.25,.1),.9,.3)]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.object; light.data.energy=power; light.data.shape="DISK"; light.data.size=size
    light.rotation_euler = (Vector((.025,0,-.03))-light.location).to_track_quat("-Z","Y").to_euler()
bpy.ops.object.camera_add(location=(-.25,.21,-.12))
camera=bpy.context.object; direction=(Vector((.005,-.005,-.02))-camera.location).normalized()
right=direction.cross(Vector((0,0,-1))).normalized(); up=right.cross(direction).normalized()
camera.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler()
camera.data.type="ORTHO";camera.data.ortho_scale=.21;scene.camera=camera
scene.render.resolution_x=1100;scene.render.resolution_y=1000
scene.render.resolution_percentage=100
rig["pose_names"] = list(poses)
rig["illustration_note"] = "Illustrative grip geometry. Thumb relaxed in every pose. No training prescription."
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "GripHand.blend"))
runpy.run_path(str(HERE / "export_hand.py"), run_name="__main__")
