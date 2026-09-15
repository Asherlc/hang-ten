"""Acceptance tests for the new Evolv Long export, independent of its authoring functions."""
import os, json, unittest
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(os.environ.get('EVOLV_MODEL_DIR', str(Path(__file__).resolve().parents[1])))
SLUG='evolv-basic-training-board-long'

def ray(tris, origin, direction):
    d=np.asarray(direction); e1=tris[:,1]-tris[:,0]; e2=tris[:,2]-tris[:,0]
    h=np.cross(d,e2); a=(e1*h).sum(1); valid=np.abs(a)>1e-14
    inv=np.divide(1.,a,out=np.zeros_like(a),where=valid); s=np.asarray(origin)-tris[:,0]
    u=inv*(s*h).sum(1); q=np.cross(s,e1); v=inv*(q*d).sum(1); t=inv*(e2*q).sum(1)
    ok=valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)
    return None if not ok.any() else np.asarray(origin)+d*t[ok].min()

class EvolvLongAcceptance(unittest.TestCase):
    def setUp(self):
        p=ROOT/(SLUG+'.glb')
        self.assertTrue(p.is_file(), 'Missing usable Evolv Long export: original evidence blocker remains')
        self.scene=trimesh.load(p,force='scene',process=False)
        self.tris=np.concatenate([m.triangles for m in self.scene.geometry.values()])
        # glTF (x,z,-y) -> source (x,y,z), in millimetres.
        self.tris=self.tris[:,:,[0,2,1]]*np.array([1,-1,1])*1000
    def test_four_physical_contacts_not_four_pairs(self):
        self.assertEqual(set(self.scene.geometry),{'body','hold-jug','hold-edge-upper','hold-edge-middle','hold-edge-lower'})
    def test_every_contact_is_a_single_continuous_surface(self):
        for name,m in self.scene.geometry.items():
            if name=='body': continue
            v,inv=np.unique(m.vertices,axis=0,return_inverse=True)
            p=trimesh.Trimesh(vertices=v,faces=inv[m.faces],process=False)
            self.assertEqual(len(p.split(only_watertight=False)),1,name)
            self.assertGreater(p.extents[0],.76,name+' must span essentially the whole board')
    def test_assembled_shell_is_closed_and_connected(self):
        v,inv=np.unique(self.tris.reshape(-1,3),axis=0,return_inverse=True)
        m=trimesh.Trimesh(vertices=v,faces=inv.reshape(-1,3),process=False)
        self.assertTrue(m.is_watertight); self.assertTrue(m.is_winding_consistent)
        self.assertGreater(m.volume,0); self.assertEqual(len(m.split()),1)
    def test_rear_has_two_recessed_bays_and_central_spine(self):
        for x in [-110,110]:
            hit=ray(self.tris,[x,8,60],[0,-1,0]); self.assertIsNotNone(hit)
            self.assertLess(hit[1],-15); self.assertGreater(hit[1],-30)
        hit=ray(self.tris,[0,8,95],[0,-1,0]); self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit[1],0,delta=1.5)
    def test_rear_bays_are_not_through_holes(self):
        for x in [-110,110]:
            hits=[ray(self.tris,[x,-70,60],[0,1,0]),ray(self.tris,[x,8,60],[0,-1,0])]
            self.assertTrue(all(h is not None for h in hits))
            self.assertGreater(hits[1][1]-hits[0][1],5)
    def test_eleven_visible_mounting_apertures_are_open(self):
        cfg=json.loads((ROOT/'source/geometry-config.json').read_text())
        self.assertEqual(len(cfg['mounts']),11)
        for h in cfg['mounts']:
            self.assertIsNone(ray(self.tris,[h['x'],-70,h['z']],[0,1,0]),str(h))
    def test_front_steps_get_shallower_in_total_projection_downwards(self):
        y=[]
        for z in [118,78,47,14]:
            p=ray(self.tris,[110,-70,z],[0,1,0]); self.assertIsNotNone(p); y.append(p[1])
        self.assertTrue(all(a<b for a,b in zip(y,y[1:])),y)
    def test_authored_edge_depths_match_declared_tip_to_back_planes(self):
        # The assignment is photo-inferred, not a manufacturer-labelled position map.
        for z,front_y in [(77,-53),(48,-47),(15,-40)]:
            hit=ray(self.tris,[110,-70,z],[0,1,0])
            self.assertIsNotNone(hit);self.assertAlmostEqual(hit[1],front_y,delta=.4)
    def test_metric_envelope_and_mobile_triangle_budget(self):
        xyz=self.tris.reshape(-1,3); self.assertTrue(np.all(np.abs(np.ptp(xyz,axis=0)-[790,60,160])<1.5))
        self.assertLess(len(self.tris),70000); self.assertTrue(np.isfinite(xyz).all())
    def test_source_photos_are_retained_byte_for_byte(self):
        import hashlib
        record=json.loads((ROOT/'evidence/upload-provenance.json').read_text())
        self.assertEqual(len(record['images']),4)
        for r in record['images']:
            p=ROOT/r['localPath']; self.assertTrue(p.is_file())
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),r['sha256'])
if __name__=='__main__': unittest.main(verbosity=2)
