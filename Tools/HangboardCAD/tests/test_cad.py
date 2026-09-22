"""Tests for the one-document CAD boundary, including actual native roundtrips."""
from pathlib import Path
import importlib
import sys
import zipfile
import json
import hashlib

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def api(name):
    assert (ROOT / (name + '.py')).is_file(), f'{name} is not implemented'
    return importlib.import_module(name)


def archive(tmp_path, xml, extra=None):
    p = tmp_path / 'test.FCStd'
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('Document.xml', xml)
        for name, value in (extra or {}).items():
            z.writestr(name, value)
    return p


def xml_for(kind='Part::Feature', prop=''):
    return f'<Document><Objects><Object type="{kind}" name="Body"/></Objects><ObjectData><Object name="Body"><Properties>{prop}</Properties></Object></ObjectData></Document>'


def test_builtin_source_archive(tmp_path):
    assert api('contract').inspect_archive(archive(tmp_path, xml_for()))['objects'] == {'Body': 'Part::Feature'}


@pytest.mark.parametrize('kind', ['Part::FeaturePython','App::FeaturePython','Mesh::Feature','Addon::Object','App::Link'])
def test_rejects_nonportable_types(tmp_path, kind):
    with pytest.raises(ValueError, match='object type'):
        api('contract').inspect_archive(archive(tmp_path, xml_for(kind)))


@pytest.mark.parametrize('name', ['../escape','/escape','x/../y','x\\y','./Document.xml'])
def test_archive_traversal(tmp_path, name):
    with pytest.raises(ValueError, match='member'):
        api('contract').inspect_archive(archive(tmp_path, xml_for(), {name:b'x'}))


def test_duplicate_zip_member(tmp_path):
    p=archive(tmp_path, xml_for())
    with zipfile.ZipFile(p, 'a') as z:
        with pytest.warns(UserWarning):
            z.writestr('Document.xml', xml_for())
    with pytest.raises(ValueError, match='duplicate'):
        api('contract').inspect_archive(p)


def test_symlink_source(tmp_path):
    p=archive(tmp_path, xml_for()); link=tmp_path/'linked.FCStd'; link.symlink_to(p)
    with pytest.raises(ValueError, match='regular'):
        api('contract').inspect_archive(link)


def test_lfs_pointer(tmp_path):
    p=tmp_path/'pointer.FCStd'
    p.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:'+'0'*64+'\nsize 123\n')
    with pytest.raises(ValueError, match='LFS'):
        api('contract').inspect_archive(p)


@pytest.mark.parametrize('kind', ['App::PropertyPythonObject','App::PropertyXLink','App::PropertyFile'])
def test_external_properties(tmp_path, kind):
    prop=f'<Property name="Bad" type="{kind}"/>'
    with pytest.raises(ValueError, match='property'):
        api('contract').inspect_archive(archive(tmp_path, xml_for(prop=prop)))


def test_xml_entity_rejected(tmp_path):
    with pytest.raises(ValueError, match='XML'):
        api('contract').inspect_archive(archive(tmp_path, '<!DOCTYPE Document>'+xml_for()))


def test_missing_included_resource(tmp_path):
    prop='<Property name="Image" type="App::PropertyFileIncluded"><FileIncluded file="missing.png"/></Property>'
    with pytest.raises(ValueError, match='included'):
        api('contract').inspect_archive(archive(tmp_path, xml_for(prop=prop)))


def board():
    return {'schemaVersion':3, 'id':'test.board','contacts':[{'id':'edge'}],
            'presentations':[{'id':'primary','media':{'type':'model','assetPath':'assets/primary.usdz','descriptorPath':'assets/primary.model.json'}}]}


def test_contact_inventory():
    api('contract').validate_bindings([{'id':'Body','role':'body'},{'id':'Lip','role':'contact','contact':'edge'}],board(),1,[])


@pytest.mark.parametrize('nodes', [
    [{'id':'Body','role':'body'}],
    [{'id':'Body','role':'body'},{'id':'Lip','role':'contact','contact':'wrong'}],
    [{'id':'Body','role':'body','contact':'edge'},{'id':'Lip','role':'contact','contact':'edge'}],
    [{'id':'Same','role':'body'},{'id':'Same','role':'contact','contact':'edge'}],
    [{'id':'Lip','role':'contact','contact':'edge'}],
    [{'id':'../bad','role':'body'},{'id':'Lip','role':'contact','contact':'edge'}],
]):
    def unused():
        pass
