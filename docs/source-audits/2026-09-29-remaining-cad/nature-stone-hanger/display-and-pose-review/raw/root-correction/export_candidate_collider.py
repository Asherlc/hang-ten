from pathlib import Path
import json,hashlib,sys
import FreeCAD as App
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));from native_cord_features import extract_native_cord_features
source=w/'native-author/nature-stone-hanger.FCStd';d=App.openDocument(str(source));d.recompute();body=d.getObject('CordSeat_Right').Shape;assert body.isValid() and len(body.Solids)==1
points,triangles=body.tessellate(.25)
r={'sourcePackage':'nature-stone-hanger','sourceFeature':'CordSeat_Right','sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'vertices':[[p.x/1000,p.z/1000,-p.y/1000] for p in points],'triangles':[list(t) for t in triangles],'nativeCordFeatures':extract_native_cord_features(d,body,['LeftVerticalCordGroove','RightVerticalCordGroove'],['LeftVisibleMouth','RightVisibleMouth'])}
(w/'native-collision-vertical.json').write_text(json.dumps(r)+'\n');print(len(points),len(triangles));App.closeDocument(d.Name)
