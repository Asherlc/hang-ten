"""Refresh exact hold mapping, editable modules and independent structural validation."""
import sys,json,shutil
from pathlib import Path
from configs import get
from asset_io import atomic_bytes,sha256
from validate import validate,glb_json
root=Path(__file__).resolve().parents[1]
def refresh(slug):
    out=root/'models'/slug; cfg=get(slug); asset=out/(slug+'.glb'); digest=sha256(asset)
    atomic_bytes(out/'source'/'geometry-config.json',json.dumps(cfg,indent=2).encode())
    for name in ('asset_io.py','geometry.py','validate.py','render_glb.py'):
        shutil.copyfile(root/'tools'/name,out/'source'/name)
    doc,_=glb_json(asset); ni={n['name']:i for i,n in enumerate(doc['nodes'])};holds=[]
    for c in cfg.get('surfaceContacts',[])+cfg.get('pockets',[]):
        hi=c.get('id',c.get('holdId'));on='hold-'+hi
        holds.append(dict(holdId=hi,objectName=on,nodeIndex=ni[on],
            kind=c.get('kind',c.get('label')),evidenceRefs=list(dict.fromkeys(c.get('evidenceRefs',[])+c.get('profileEvidenceRefs',[]))),
            publishedDepthMm=c.get('publishedDepthMm'),publishedAngleDegrees=c.get('publishedAngleDegrees'),
            publishedGripLengthMm=c.get('publishedGripLengthMm'),
            geometryClassification='source contact identity; manually authored approximate local curvature; see sourceSelector',
            sourceSelector=c))
    hm=dict(schemaVersion=2,asset=asset.name,assetSha256=digest,sourceCoordinates='metres; X right, Y rear, Z up',nonselectableObjects=['body'],holds=holds)
    atomic_bytes(out/'hold-map.json',json.dumps(hm,indent=2).encode())
    res=validate(asset,cfg,hm)
    atomic_bytes(out/'validation'/'structural-results.json',json.dumps(res,indent=2).encode())
    print(slug,digest,'structural',res['structuralPass'],'checks',len(res['checks']))
    for c in res['checks']:
        if not c['pass']:print('FAIL',c)
    assert res['structuralPass']
    return res
if __name__=='__main__': refresh(sys.argv[1])
