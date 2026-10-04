from pathlib import Path
import json,sys,copy,logging,trimesh,hashlib
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
from native_cord_guides import solve_groove_guided_routes
source=json.loads((w/'native-collision-vertical.json').read_text());mesh=trimesh.Trimesh(source['vertices'],source['triangles'],process=False);data=json.loads((w/'vertical-input-final-metadata.json').read_text());pose='edge-front-15mm-flat'
full=data['suspension']['canonicalPoses'];data['suspension']['canonicalPoses']={pose:full[pose]};full=data['ropeSolver']['grooveGuides']['byPoseID'];data['ropeSolver']['grooveGuides']['byPoseID']={pose:full[pose]}
descriptor=json.loads((w/'assets/primary.model.json').read_text());result=solve_groove_guided_routes(mesh,data,descriptor,source);out=w/'vertical-front-flat-planar.json';out.write_text(json.dumps({'sourceSHA256':source['sourceSHA256'],'helperSHA256':hashlib.sha256((Path.cwd()/'Tools/HangboardCAD/native_cord_guides.py').read_bytes()).hexdigest(),'colliderSHA256':hashlib.sha256((w/'native-collision-vertical.json').read_bytes()).hexdigest(),'inputSHA256':hashlib.sha256((w/'vertical-input-final-metadata.json').read_bytes()).hexdigest(),'poses':result},indent=2)+'\n');print(str(out),flush=True)
