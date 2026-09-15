"""Source-backed regression tests: failures reproduce the old delivered defects.
These test geometry, not a status flag. Source photos remain independently reviewed.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from configs import moon,metolius
from geometry import evaluate

def inside(cfg,x,y,z):
    return float(evaluate(np.array(x,float),np.array(y,float),np.array(z,float),cfg))<0

def test_metolius_has_six_mounts_in_three_pairs():
    mounts=metolius()['mounts']
    assert len(mounts)==6, 'Readable Deluxe diagram shows six bores, not four'
    assert len(set(h['z'] for h in mounts))==3

def test_metolius_retains_numbered_nonuniform_depths():
    p={p['holdId']:p for p in metolius()['pockets']}
    assert p['03-edge-left']['displayDepthMm']==31
    assert p['04-three-finger-left']['displayDepthMm']==32
    assert p['05-two-finger-left']['displayDepthMm']==38
    assert p['08-two-finger-left']['displayDepthMm']==28

def test_moon_central_jug_not_a_capsule_pocket():
    c=moon()
    assert 'jug-centre' not in [p['holdId'] for p in c['pockets']]
    assert 'jug-centre' in [p['id'] for p in c['surfaceContacts']]

def test_moon_jug_has_central_arch_but_lateral_lip_material():
    c=moon()
    assert not inside(c,0,-51,142), 'Centre underside notch must be open'
    assert inside(c,35,-51,142), 'Lateral rolled lip must exist, not a broad capsule hollow'
    assert inside(c,0,-51,156), 'Top lip remains joined above arch'

def test_moon_mono_openings_are_not_blind_caps():
    c=moon()
    for p in c['pockets']:
        if p['holdId'].startswith('one-finger-'):
            for y in np.linspace(-56,1,90):
                assert not inside(c,p['x'],y,p['z']), 'Visible mono opening must remain open through the board'

def test_moon_central_edges_are_open_shelves_not_closed_pills():
    c=moon()
    for hold in ('edge-22mm-centre','edge-18mm-centre'):
        assert hold not in [p['holdId'] for p in c['pockets']]
        assert hold in [s['id'] for s in c['surfaceContacts']]
    assert not inside(c,0,-25,55), 'Air above the lower open shelf cannot be capped'
    assert not inside(c,0,-28,110), 'Air above the middle open shelf cannot be capped'
    assert inside(c,0,-10,110), 'The backing of the board remains joined'
