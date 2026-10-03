from pathlib import Path
import hashlib
import json
import sys
import FreeCAD as App

ROOT = Path.cwd()
LANE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'Tools/HangboardCAD'))
from native_cord_features import extract_native_cord_features

source = LANE/'native-author/nature-stone-hanger.FCStd'
document = App.openDocument(str(source))
try:
    document.recompute()
    body = document.getObject('CordSeat_Right').Shape
    assert body.isValid() and len(body.Solids) == 1
    points, triangles = body.tessellate(.25)
    result = {
        'sourcePackage':'nature-stone-hanger', 'sourceFeature':'CordSeat_Right',
        'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'vertices':[[p.x/1000,p.z/1000,-p.y/1000] for p in points],
        'triangles':[list(t) for t in triangles],
        'nativeCordFeatures':extract_native_cord_features(document,body,
            ['LeftVerticalCordGroove','RightVerticalCordGroove'],
            ['LeftVisibleMouth','RightVisibleMouth'])}
    (LANE/'native-collision-solid.json').write_text(json.dumps(result)+'\n')
    print(json.dumps({'sourceSHA256':result['sourceSHA256'],
                      'vertices':len(points),'triangles':len(triangles)}))
finally:
    App.closeDocument(document.Name)
