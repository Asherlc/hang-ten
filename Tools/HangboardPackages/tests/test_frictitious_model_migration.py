"""Catch swapped opaque DoorMount IDs, conflated Megalith pockets, and shipping drift."""
import hashlib
import json
import zipfile
from pathlib import Path
import pytest
from hangboard_packages.board_catalog import load_board_package
from test_board_package_staging import load_staging_module, configure_xcode_destination, odr_staging_root

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'docs/source-audits/2026-09-20-hangboards-batch-05-migration'
DOOR = {'jug':'top-jug', 'left-edge-35':'edge-35-left', 'right-edge-35':'edge-35-right',
        'left-edge-25':'mixed-25-pocket-left','right-edge-25':'mixed-25-pocket-right',
        'left-pocket-2finger':'hold-7','right-pocket-2finger':'hold-6',
        'left-edge-20':'hold-12','right-edge-20':'hold-13',
        'left-edge-15':'hold-11','right-edge-15':'hold-8',
        'left-edge-10':'hold-10','right-edge-10':'hold-9'}
MEGA = {'jug':'top-jug','center-edge-25':'center-edge-25',
        'left-mono':'mono-left','right-mono':'mono-right',
        'left-pocket-2finger':'pocket-2finger-left','right-pocket-2finger':'pocket-2finger-right',
        **{f'{s}-edge-{d}':f'edge-{d}-{s}' for s in ('left','right') for d in (8,10,12,15,20,30)},
        'left-edge-40':'edge-40-pocket-left','right-edge-40':'edge-40-pocket-right'}

@pytest.mark.parametrize('slug,mapping,width,height,holes',[
    ('frictitious-doormount-pro-7', DOOR,.6477,.1143,1),
    ('frictitious-megalith', MEGA,.67945,.1651,6)])
def test_physical_identities_survive_native_export(slug,mapping,width,height,holes):
    package=ROOT/'Hangboards'/slug
    board=json.loads((package/'board.json').read_text())
    assert board['presentations'][0]['media']['type']=='model'
    assert not list(package.rglob('*.png'))
    assert 'contactGeometry' not in json.dumps(board)
    descriptor=json.loads((package/'assets/primary.model.json').read_text())
    assert descriptor['modelSHA256']==hashlib.sha256((package/'assets/primary.usdz').read_bytes()).hexdigest()
    assert set(descriptor['contacts'])==set(mapping.values())=={c['id'] for c in board['contacts']}
    actual=json.loads((AUDIT/'native'/slug/'contact-mapping.json').read_text())
    assert {o['sourceNodeID']:o['contactID'] for o in actual['objects'] if o['role']=='contact'}=={'hold--'+n:c for n,c in mapping.items()}
    contacts=descriptor['contacts'];bounds=descriptor['modelBounds']
    assert bounds['max'][0]-bounds['min'][0]==pytest.approx(width,abs=.001)
    assert bounds['max'][1]-bounds['min'][1]==pytest.approx(height,abs=.001)
    assert bounds['max'][2]-bounds['min'][2]<.065
    for source,identity in mapping.items():
        if source.startswith('left-'):
            left=contacts[identity];right=contacts[mapping[source.replace('left-','right-',1)]]
            assert left['center'][0]<.5<right['center'][0]
            assert not set(left['nodeIDs'])&set(right['nodeIDs'])
            for side,other in [('min','max'),('max','min')]:
                assert right['facePlaneAABB'][side][0]==pytest.approx(1-left['facePlaneAABB'][other][0],abs=1e-6)
                assert right['facePlaneAABB'][side][1]==pytest.approx(left['facePlaneAABB'][side][1],abs=1e-6)
    prep=json.loads((AUDIT/'native'/slug/'preparation-report.json').read_text())
    assert prep['mountingOpeningsRemoved']==holes
    assert prep['maximumContactVertexDeltaMetres']<1e-7
    verify=json.loads((AUDIT/'native'/slug/'geometry-verification.json').read_text())
    assert len(verify['mountingClosureRays'])==holes
    assert all(v['frontHit'] and v['backHit'] for v in verify['mountingClosureRays'])
    assert verify['contactCount']==len(mapping)
    assert verify['unionOfAllContactTrianglesUnchanged']
    assert verify['ownershipTransferTriangles']==(18 if slug.endswith('megalith') else 0)
    load_board_package(package)


def test_nested_megalith_pockets_have_independent_unspecified_depth():
    board=json.loads((ROOT/'Hangboards/frictitious-megalith/board.json').read_text())
    contacts={c['id']:c for c in board['contacts']}
    assert {'pocket-2finger-left','pocket-2finger-right'}<=contacts.keys()
    for side in ('left','right'):
        pocket=contacts['pocket-2finger-'+side]
        assert pocket['kind']=='pocket' and pocket['fingerCapacity']==2
        assert 'depth' not in pocket and pocket['gripTypes']==[]
        assert contacts['edge-40-pocket-'+side]['depth']['range']=={'minimum':40,'maximum':40}
        assert 'depth' not in contacts['mono-'+side]


def test_frictitious_stages_exact_models_only_in_odr(tmp_path,monkeypatch):
    destination=tmp_path/'build/HangTen.app/Hangboards'
    configure_xcode_destination(monkeypatch,destination)
    load_staging_module().stage_board_packages(ROOT,destination)
    for slug in ('frictitious-doormount-pro-7','frictitious-megalith'):
        source=ROOT/'Hangboards'/slug
        assert (destination/slug/'assets/primary.model.json').exists()
        assert not (destination/slug/'assets/primary.usdz').exists()
        assert (odr_staging_root(destination)/slug/'Hangboards'/slug/'assets/primary.usdz').read_bytes()==(source/'assets/primary.usdz').read_bytes()
        assert (destination/slug/'board.json').read_bytes()==(source/'board.json').read_bytes()
