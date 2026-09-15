from pathlib import Path
import hashlib, importlib.util, sys, zipfile
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

def audit_module():
    p=ROOT/'tools/audit_archive.py'
    assert p.is_file(), 'The documented archive audit command must exist and be executable'
    spec=importlib.util.spec_from_file_location('audit_archive',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def test_checksums_detect_changed_content(tmp_path):
    a=audit_module();f=tmp_path/'example.txt';f.write_text('original')
    (tmp_path/'SHA256SUMS.txt').write_text(hashlib.sha256(f.read_bytes()).hexdigest()+'  example.txt\n')
    assert a.check_checksums(tmp_path)['passed']
    f.write_text('changed')
    result=a.check_checksums(tmp_path)
    assert not result['passed'] and result['failures'][0]['path']=='example.txt'

def test_checksum_missing_file_is_not_a_pass(tmp_path):
    a=audit_module();(tmp_path/'SHA256SUMS.txt').write_text('0'*64+'  missing.glb\n')
    assert not a.check_checksums(tmp_path)['passed']

def test_zip_path_traversal_is_rejected(tmp_path):
    a=audit_module();z=tmp_path/'bad.zip'
    with zipfile.ZipFile(z,'w') as out:out.writestr('../outside.txt','bad')
    with pytest.raises(ValueError):a.safe_extract(z,tmp_path/'extracted')
    assert not (tmp_path/'outside.txt').exists()
