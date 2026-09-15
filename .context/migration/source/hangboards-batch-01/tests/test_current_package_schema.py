"""Regression checks for current export packaging and permitted extra review views."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

def test_all_current_status_records_locate_actual_glb():
    for p in (ROOT/'models').glob('*/model-status.json'):
        st=json.loads(p.read_text())
        if st['usableExport']:
            assert st.get('glb')==p.parent.name+'.glb',p.parent.name
            assert (p.parent/st['glb']).is_file()

def test_review_sheet_records_name_existing_output():
    for p in (ROOT/'models').glob('*/renders/review-sheet-provenance.json'):
        data=json.loads(p.read_text())
        assert data.get('output'),str(p)
        assert (p.parent/data['output']).is_file()

def test_extra_moon_review_views_are_permitted():
    import audit_archive
    d=ROOT/'models/moon-armstrong-ash'
    actual=json.loads((d/'renders/render-provenance.json').read_text())
    assert len(actual['renders'])==8
    result=audit_archive.verify_model(d)
    render_count_checks=[x for x in result['checks'] if 'render_records' in x['check']]
    assert render_count_checks and all(x['pass'] for x in render_count_checks)
