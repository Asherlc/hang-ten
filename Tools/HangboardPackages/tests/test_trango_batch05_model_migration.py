"""Catch lost stable lobes, invented pinch contacts, disputed depths and ODR drift."""
import hashlib,json
from pathlib import Path
import pytest
from hangboard_packages.board_catalog import load_board_package
from test_board_package_staging import load_staging_module,configure_xcode_destination,odr_staging_root
ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'docs/source-audits/2026-09-20-hangboards-batch-05-migration/native'
IDS={
'forge':['sloper-30','sloper-40','large-flat-edge','slopey-crimper','variable-edge-rail','closed-crimp','mr-deep','mr-shallow','im-deep','im-shallow'],
'natural':['top-jug','top-variable-rail','bottom-variable-rail','closed-crimp','upper-pocket','center-lower-pocket','outer-supported-pocket']}
@pytest.mark.parametrize('product',IDS)
def test_trango_stable_contacts_bind_exact_native_surfaces(product):
    slug='trango-rock-prodigy-'+product;package=ROOT/'Hangboards'/slug
    b=json.loads((package/'board.json').read_text());media=b['presentations'][0]['media']
    assert media['type']=='model'
    assert not list(package.rglob('*.png')) and 'contactGeometry' not in json.dumps(b)
    expected={name+'-'+side for name in IDS[product] for side in ['left','right']}
    assert {c['id'] for c in b['contacts']}==expected
    d=json.loads((package/'assets/primary.model.json').read_text())
    assert set(d['contacts'])==expected
    assert d['modelSHA256']==hashlib.sha256((package/'assets/primary.usdz').read_bytes()).hexdigest()
    assert all(c['kind']!='pinch' for c in b['contacts'])
    for name in IDS[product]:
        l=d['contacts'][name+'-left'];r=d['contacts'][name+'-right']
        assert l['center'][0]<.5<r['center'][0]
        assert set(l['nodeIDs']).isdisjoint(r['nodeIDs'])
        for a,z in [('min','max'),('max','min')]:
            assert r['facePlaneAABB'][a][0]==pytest.approx(1-l['facePlaneAABB'][z][0],abs=1e-6)
            assert r['facePlaneAABB'][a][1]==pytest.approx(l['facePlaneAABB'][a][1],abs=1e-6)
    disputed=['im-deep','im-shallow'] if product=='forge' else ['closed-crimp','center-lower-pocket','outer-supported-pocket']
    assert all('depth' not in c for c in b['contacts'] if c['id'].rsplit('-',1)[0] in disputed)
    report=json.loads((AUDIT/slug/'geometry-verification.json').read_text())
    assert report['cleanEmptySceneImport']
    assert report['preparedTrianglesUnchanged']
    assert report['preparedCustomNormalsUnchangedWithinTolerance']
    assert report['authoredCrimpSection']['hookHasDistinctRelief']
    if product=='natural':assert report['authoredCrimpSection']['supportedFloorStepMetres']>.0025
    else:assert report['authoredCrimpSection']['imLobeDepthTransitionMetres']>.010
    mapping=json.loads((AUDIT/slug/'contact-mapping.json').read_text())
    extra=['pinch-medium','pinch-narrow'] if product=='forge' else ['pinch-thumb']
    roles={o['sourceNodeID']:o['role'] for o in mapping['objects']}
    assert all(roles['hold--'+side+'-'+name]=='body' for side in ['left','right'] for name in extra)

    assert len(report['nativeContactRays'])==len(expected)
    assert all(x['nearestContactID']==x['expectedContactID'] for x in report['nativeContactRays'])
    assert len(report['mountingClosureRays'])==(8 if product=='forge' else 6)
    assert all(x['frontHit'] and x['backHit'] for x in report['mountingClosureRays'])
    assert len(report['preservedPassageRays'])==2
    assert all(not x['hit'] for x in report['preservedPassageRays'])
    load_board_package(package)

def test_trango_models_ship_only_in_odr(tmp_path,monkeypatch):
    destination=tmp_path/'build/HangTen.app/Hangboards';configure_xcode_destination(monkeypatch,destination)
    load_staging_module().stage_board_packages(ROOT,destination)
    for product in IDS:
        slug='trango-rock-prodigy-'+product;source=ROOT/'Hangboards'/slug
        assert (destination/slug/'assets/primary.model.json').exists()
        assert not (destination/slug/'assets/primary.usdz').exists()
        assert (odr_staging_root(destination)/slug/'Hangboards'/slug/'assets/primary.usdz').read_bytes()==(source/'assets/primary.usdz').read_bytes()
        assert (destination/slug/'board.json').read_bytes()==(source/'board.json').read_bytes()
