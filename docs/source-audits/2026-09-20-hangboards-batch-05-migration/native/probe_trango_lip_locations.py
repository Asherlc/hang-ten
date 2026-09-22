import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
variant=sys.argv[-1];root=Path.cwd();out=root/".context/hangboards-batch-05-astra-migration"/("trango-seam-original-location-"+variant);out.mkdir(exist_ok=True)
records=[]
for slug in ["trango-rock-prodigy-forge","trango-rock-prodigy-natural"]:
 model=root/"Hangboards"/slug/"assets/primary.usdz" if variant=="final" else root/".context/hangboards-batch-05-astra-migration/trango-seam-checkpoint"/(slug+".usdz")
 model_hash=hashlib.sha256(model.read_bytes()).hexdigest()
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.wm.usd_import(filepath=str(model))
 meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
 vertices=[];faces=[];owners=[]
 for o in meshes:
  offset=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices)
  for p in o.data.polygons:faces.append([offset+i for i in p.vertices]);owners.append((o,p.index))
 tree=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
 scene=bpy.context.scene;scene.render.engine="CYCLES";scene.cycles.samples=24
 scene.render.resolution_x=1400;scene.render.resolution_y=750;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new("Review studio");scene.world.use_nodes=True;scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.82,.82,.82,1);scene.world.node_tree.nodes["Background"].inputs[1].default_value=.5
 scene.view_settings.view_transform="AgX"
 for name,location,energy,size in [("Key",(-.5,-.8,1),70,1.0),("Fill",(.7,-.4,.4),30,.8)]:
  data=bpy.data.lights.new(name,"AREA");data.energy=energy;data.shape="DISK";data.size=size;obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
 cam=bpy.data.objects.new("ReviewCamera",bpy.data.cameras.new("ReviewCamera"));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.80
 for view,pos in [("crimp",(-.16,-.5,.2))]:
  target=Vector((-.16,-.025,-.025)) if view=='crimp' else Vector((0,0,0)); cam.data.ortho_scale=(.22 if slug.endswith('natural') else .27) if view=='crimp' else (.60 if slug.endswith('natural') else .90); cam.location=pos;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();
  bpy.context.view_layer.update()
  frames=cam.data.view_frame(scene=scene);xs=[p.x for p in frames];ys=[p.y for p in frames]
  samples=[]
  pixels=[(126,304),(341,304),(463,304)] if slug.endswith('forge') else [(277,361),(312,365),(435,351)]
  pixels=[(x+dx,y+dy) for x,y in pixels for dx in range(-16,17,2) for dy in range(-16,17,2)]
  for px,py in pixels:
   start=cam.matrix_world@Vector((min(xs)+(px+.5)/1400*(max(xs)-min(xs)),max(ys)-(py+.5)/750*(max(ys)-min(ys)),0))
   direction=cam.matrix_world.to_quaternion()@Vector((0,0,-1))
   point,normal,face_id,distance=tree.ray_cast(start,direction)
   hit=point is not None
   if hit:obj,index=owners[face_id];matrix=obj.matrix_world
   sample={'pixel':[px,py],'hit':hit,'modelSHA256':model_hash}
   if hit:
    poly=obj.data.polygons[index]
    sample.update({'point':list(point),'faceNormal':list(normal),'object':obj.name,'polygon':index,'vertices':[list(matrix@obj.data.vertices[v].co) for v in poly.vertices],'normals':[list(obj.data.corner_normals[i].vector) for i in poly.loop_indices]})
   samples.append(sample)
  samples_path=out/(slug+'-samples.json')
  samples_path.write_text(json.dumps(samples,indent=2)+'\n')
  records.append({"model":str(model.relative_to(root)),"modelSHA256":model_hash,"view":view,"artifactType":"native-ray-samples","path":str(samples_path.relative_to(root)),"sha256":hashlib.sha256(samples_path.read_bytes()).hexdigest(),"blenderVersion":bpy.app.version_string,"purpose":"Exact exported USDZ camera-ray samples; no render or app acceptance"})
for record in records:
 artifact=root/record['path']
 assert artifact.suffix=='.json' and artifact.is_file()
 assert record['sha256']==hashlib.sha256(artifact.read_bytes()).hexdigest()
(out/'provenance.json').write_text(json.dumps(records,indent=2)+'\n')
