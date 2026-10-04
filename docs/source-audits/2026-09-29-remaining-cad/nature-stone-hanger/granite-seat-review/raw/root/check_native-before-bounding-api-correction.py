"""Independent native checks against the exact previously committed source."""
from pathlib import Path
import hashlib
import json
import FreeCAD as App
import Part

ROOT = Path.cwd()
LANE = Path(__file__).resolve().parent
before = LANE / 'committed-before/nature-stone-hanger.FCStd'
after = LANE / 'native-author/nature-stone-hanger.FCStd'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = App.openDocument(str(before))
new = App.openDocument(str(after))
try:
    old.recompute()
    new.recompute()
    assert old.HangTenBoardManifest == new.HangTenBoardManifest
    assert old.HangTenTessellationDeflection == new.HangTenTessellationDeflection
    b0 = old.getObject('CordSeat_Right').Shape
    b1 = new.getObject('CordSeat_Right').Shape
    assert b1.isValid() and len(b1.Solids) == 1
    bb = b1.BoundBox
    print('Independent envelope diagnostic', old.Name, new.Name, [bb.XLength,bb.YLength,bb.ZLength], str(b1.BoundBox), flush=True)
    assert all(abs(a-b) < 1e-5 for a,b in zip(
        [bb.XLength, bb.YLength, bb.ZLength], [105,35,105]))
    seat = new.getObject('GraniteInsertSeat').Shape
    stone = new.getObject('StoneRoundover').Shape
    assert seat.isValid() and stone.isValid()
    overlap = seat.common(stone).Volume
    assert overlap < 1e-6, 'Wood and granite solids overlap'
    source_overlap = old.getObject('Cavity3').Shape.common(old.getObject('StoneRoundover').Shape).Volume
    assert source_overlap > 1, 'Prior geometry must reproduce overlap'
    contact = new.getObject('Region_edge_front_20mm_granite').Shape
    stone_faces = Part.makeCompound(list(stone.Faces))
    assert contact.cut(stone_faces).Area < 1e-5, 'Granite contact extends beyond the stone'
    assert contact.cut(new.getObject('BodySkin').Shape).Area < 1e-5, 'Granite contact is not exposed'
    exposed = new.getObject('BodySkin').Shape.common(stone_faces)
    assert exposed.cut(contact).Area < 1e-5, 'Exposed stone left on the wood node'
    assert abs(contact.BoundBox.YLength - 20) < 1e-5
    contacts = {}
    regions = [o for o in new.Objects if getattr(o,'NodeRole','') == 'contact']
    assert len(regions) == 8
    for obj in regions:
        prior = old.getObject(obj.Name)
        assert prior is not None and obj.Shape.isValid() and obj.Shape.Area > 0
        changes = {'oldMinusNewAreaMM2': prior.Shape.cut(obj.Shape).Area,
                   'newMinusOldAreaMM2': obj.Shape.cut(prior.Shape).Area}
        cid = obj.ContactID
        if cid != 'edge-front-20mm-granite':
            assert max(changes.values()) < 1e-5, cid
        contacts[cid] = dict(changes, areaMM2=obj.Shape.Area,
                            depthMM=obj.Shape.BoundBox.YLength)
    intersections = {}
    for i, a in enumerate(regions):
        for b in regions[i+1:]:
            area = a.Shape.common(b.Shape).Area
            intersections[a.ContactID+' / '+b.ContactID] = area
            assert area < 1e-5, 'Contact areas overlap'
    feature_checks = {}
    for name in ['LeftVerticalCordGroove','RightVerticalCordGroove','LeftVisibleMouth','RightVisibleMouth']:
        a, b = old.getObject(name).Shape, new.getObject(name).Shape
        diff = a.cut(b).Volume + b.cut(a).Volume
        assert diff < 1e-6, name
        feature_checks[name] = diff
    for sign in [-1,1]:
        box = Part.makeBox(10,60,130,App.Vector(-56 if sign < 0 else 46,-30,-65))
        a, b = b0.common(box), b1.common(box)
        assert a.cut(b).Volume + b.cut(a).Volume < 1e-5, 'Outer cord-bearing region changed'
    result = {'status':'pass', 'sourceSHA256':sha(after), 'beforeSHA256':sha(before),
              'manifestRawPreserved':True, 'nativeEnvelopeMM':[bb.XLength,bb.YLength,bb.ZLength],
              'priorWoodStoneOverlapMM3':source_overlap,'correctedWoodStoneOverlapMM3':overlap,
              'graniteOnlyOnExposedStone':True,'allExposedStoneAssignedToGranite':True,
              'contactInventory':contacts,'contactPairIntersectionAreasMM2':intersections,
              'nativeCordFeatureSymmetricDifferenceMM3':feature_checks,
              'outerCordBearingRegionPreserved':True}
    (LANE/'independent-native-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    App.closeDocument(new.Name)
    App.closeDocument(old.Name)
