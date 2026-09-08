"""Render the actual exported surfaces as a contact sheet; no asset mutation."""
import bpy, json, os
from pathlib import Path
from mathutils import Vector, Matrix
ROOT = Path(__file__).resolve().parents[2]
owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(ROOT))).name
OUT = ROOT / ".context"; OUT.mkdir(exist_ok=True)
data = json.loads((ROOT / "HangTen/Resources/GripHand/hand-mesh.json").read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; scene.render.engine = "CYCLES"; scene.cycles.samples=24
scene.world = bpy.data.worlds.new("Review world"); scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.38,.41,.4,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.6
mat=bpy.data.materials.new("Matte hand");mat.use_nodes=True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(.34,.41,.39,1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=.8
ink=bpy.data.materials.new("Labels");ink.diffuse_color=(.02,.03,.025,1)
direction=Vector((.55,.30,1)).normalized();right=Vector((0,1,0)).cross(direction).normalized();up=direction.cross(right).normalized()
rot=Matrix((right,up,direction)).transposed()
names=["Neutral","OpenHand","HalfCrimp","FullCrimp","Sloper","Pocket6","Pocket9","Pocket1"]
faces=[data["indices"][i:i+3] for i in range(0,len(data["indices"]),3)]
for index,name in enumerate(names):
    p=data["poses"][name]["positions"];verts=[p[i:i+3] for i in range(0,len(p),3)]
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update()
    obj=bpy.data.objects.new(name,m);scene.collection.objects.link(obj);m.materials.append(mat)
    for poly in m.polygons:poly.use_smooth=True
    center=Vector((0,2,.2));offset=right*((index%4-1.5)*3.7)+up*((.5-index//4)*5)
    obj.location=offset-center
    for delta,power,size in [(Vector((5,6,8)),600,5),(Vector((-5,2,4)),250,5)]:
        bpy.ops.object.light_add(type="AREA",location=offset+delta)
        light=bpy.context.object;light.data.energy=power;light.data.shape="DISK";light.data.size=size
        light.rotation_euler=(offset-light.location).to_track_quat("-Z","Y").to_euler()
    curve=bpy.data.curves.new(name+" label","FONT");curve.body=name;curve.align_x="CENTER";curve.size=.28
    label=bpy.data.objects.new(name+" label",curve);scene.collection.objects.link(label)
    label.location=offset-up*2.5+direction*.4;label.rotation_euler=rot.to_euler();curve.materials.append(ink)
bpy.ops.object.camera_add(location=direction*30);camera=bpy.context.object;camera.rotation_euler=rot.to_euler();camera.data.type="ORTHO";camera.data.ortho_scale=16;scene.camera=camera
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG";scene.render.filepath=str(OUT/f"{owner}-xr-grip-surface-sheet.png")
bpy.ops.render.render(write_still=True)
