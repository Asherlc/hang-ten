"""Independent metadata regressions. Tests target actual files, never stale claims."""
import json
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]

def active_models():
    return sorted(p.parent for p in (ROOT/'models').glob('*/model-status.json') if json.loads(p.read_text()).get('usableExport'))

def test_all_hold_evidence_references_resolve():
    for d in active_models():
        ids={x['id'] for x in json.loads((d/'evidence/source-register.json').read_text())}
        for h in json.loads((d/'hold-map.json').read_text())['holds']:
            assert set(h['evidenceRefs'])<=ids, (d.name,h['holdId'],set(h['evidenceRefs'])-ids)

def test_render_hashes_bind_current_actual_export():
    for d in active_models():
        h=hashlib.sha256((d/(d.name+'.glb')).read_bytes()).hexdigest()
        for rel in ['build-result.json','hold-map.json','validation/structural-results.json','validation/visual-review.json','renders/render-provenance.json']:
            data=json.loads((d/rel).read_text())
            assert h in [data.get('sha256'),data.get('assetSha256')],(d.name,rel)
        prov=json.loads((d/'renders/render-provenance.json').read_text())
        assert len(prov['renders'])>=5
        for r in prov['renders']:
            assert hashlib.sha256((d/'renders'/r['path']).read_bytes()).hexdigest()==r['sha256']

def test_source_face_label_inventory_matches_export_mapping():
    import numpy as np
    for d in active_models():
        ids=json.loads((d/'build-result.json').read_text())['geometry']['contactIds']
        hm=json.loads((d/'hold-map.json').read_text())['holds']
        assert ids==[h['holdId'] for h in hm]
        m=np.load(d/'source/editable-assembled-mesh.npz')
        assert set(np.unique(m['face_labels']))==set(range(len(ids)+1))
        assert len(m['faces'])==len(m['face_labels'])
        assert np.isfinite(m['vertices']).all()

def test_every_hold_is_one_connected_surface_patch():
    import numpy as np,trimesh
    for d in active_models():
        scene=trimesh.load(d/(d.name+'.glb'),force='scene',process=False)
        for name,g in scene.geometry.items():
            if name=='body':continue
            v,inv=np.unique(np.asarray(g.vertices),axis=0,return_inverse=True)
            m=trimesh.Trimesh(vertices=v,faces=inv[np.asarray(g.faces)],process=False)
            groups=trimesh.graph.connected_components(m.face_adjacency,nodes=np.arange(len(m.faces)),min_len=1)
            assert len(groups)==1,(d.name,name,[len(x) for x in groups])
