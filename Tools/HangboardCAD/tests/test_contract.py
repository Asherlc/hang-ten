"""Tests for the fail-closed source archive preflight and the role bindings."""

from __future__ import annotations

from collections import Counter
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import use_hangboard_packages  # noqa: E402,F401
from hangboard_packages import cad_source  # noqa: E402

import contract  # noqa: E402

DOCUMENT = """<?xml version="1.0" encoding="utf-8"?>
<Document SchemaVersion="4">
  <Objects Count="1">
    <Object type="PartDesign::Body" name="Body"/>
  </Objects>
  <ObjectData Count="1">
    <Object name="Body"/>
  </ObjectData>
</Document>
"""


def build_archive(path: Path, members, document: str = DOCUMENT) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Document.xml", document)
        for name, data in members:
            archive.writestr(name, data)
    return path


def test_accepts_a_minimal_builtin_document(tmp_path):
    archive = build_archive(tmp_path / "ok.FCStd", [])
    result = cad_source.inspect_archive(archive)
    assert result["objects"] == {"Body": "PartDesign::Body"}


def test_rejects_a_missing_document(tmp_path):
    path = tmp_path / "bad.FCStd"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Other.xml", "<x/>")
    with pytest.raises(ValueError, match="missing Document.xml"):
        cad_source.inspect_archive(path)


def test_rejects_directory_traversal_members(tmp_path):
    archive = build_archive(tmp_path / "trav.FCStd", [("../escape.txt", b"x")])
    with pytest.raises(ValueError, match="unsafe member path"):
        cad_source.inspect_archive(archive)


def test_rejects_duplicate_case_colliding_members(tmp_path):
    archive = build_archive(
        tmp_path / "dup.FCStd", [("Part.brp", b"a"), ("part.brp", b"b")]
    )
    with pytest.raises(ValueError, match="duplicate or case-colliding"):
        cad_source.inspect_archive(archive)


def test_rejects_an_unsupported_object_type(tmp_path):
    document = DOCUMENT.replace("PartDesign::Body", "App::FeaturePython")
    archive = build_archive(tmp_path / "py.FCStd", [], document)
    with pytest.raises(ValueError, match="unsupported document object type"):
        cad_source.inspect_archive(archive)


def test_rejects_an_external_xlink(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="Support" type="App::PropertyXLinkSubList">'
        '<XLinkSubList count="1"><XLink file="/tmp/other.FCStd" name="B"/></XLinkSubList>'
        "</Property></ObjectData>",
    )
    archive = build_archive(tmp_path / "xlink.FCStd", [], document)
    with pytest.raises(ValueError, match="external document reference"):
        cad_source.inspect_archive(archive)


def test_accepts_a_document_local_xlink(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="Support" type="App::PropertyXLinkSubList">'
        '<XLinkSubList count="1"><XLink file="" name="Profile"/></XLinkSubList>'
        "</Property></ObjectData>",
    )
    archive = build_archive(tmp_path / "local.FCStd", [], document)
    assert cad_source.inspect_archive(archive)["objects"] == {"Body": "PartDesign::Body"}


NEW_XLINK_TYPES = [
    "App::PropertyXLinkList",
    "App::PropertyXLinkSubHidden",
    "App::PropertyXLinkContainer",
]


@pytest.mark.parametrize("xlink_type", NEW_XLINK_TYPES)
def test_rejects_external_reference_for_each_xlink_type(tmp_path, xlink_type):
    document = DOCUMENT.replace(
        "</ObjectData>",
        f'<Property name="Support" type="{xlink_type}">'
        '<XLink file="/tmp/other.FCStd" name="B"/></Property></ObjectData>',
    )
    archive = build_archive(tmp_path / "xlink_variant.FCStd", [], document)
    with pytest.raises(ValueError, match="external document reference"):
        cad_source.inspect_archive(archive)


@pytest.mark.parametrize("xlink_type", NEW_XLINK_TYPES)
def test_accepts_document_local_reference_for_each_xlink_type(tmp_path, xlink_type):
    document = DOCUMENT.replace(
        "</ObjectData>",
        f'<Property name="Support" type="{xlink_type}">'
        '<XLink file="" name="Profile"/></Property></ObjectData>',
    )
    archive = build_archive(tmp_path / "xlink_local.FCStd", [], document)
    assert cad_source.inspect_archive(archive)["objects"] == {"Body": "PartDesign::Body"}


def test_rejects_an_absent_included_file(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="TextureFile" type="App::PropertyFileIncluded">'
        '<FileIncluded file="missing.png"/></Property></ObjectData>',
    )
    archive = build_archive(tmp_path / "inc.FCStd", [], document)
    with pytest.raises(ValueError, match="missing included file"):
        cad_source.inspect_archive(archive)


def test_accepts_a_present_included_file(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="TextureFile" type="App::PropertyFileIncluded">'
        '<FileIncluded file="wood.png"/></Property></ObjectData>',
    )
    archive = build_archive(tmp_path / "inc2.FCStd", [("wood.png", b"\x89PNG")], document)
    assert "wood.png" in cad_source.inspect_archive(archive)["members"]


def test_rejects_a_git_lfs_pointer(tmp_path):
    path = tmp_path / "pointer.FCStd"
    path.write_bytes(
        b"version https://git-lfs.github.com/spec/v1\n"
        b"oid sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
        b"size 10\n"
    )
    with pytest.raises(ValueError, match="Git LFS pointer"):
        cad_source.inspect_archive(path)


def test_rejects_duplicate_board_contact_ids():
    board = {"schemaVersion": 3, "id": "x", "contacts": [{"id": "a"}, {"id": "a"}]}
    with pytest.raises(ValueError, match="duplicate board contact IDs"):
        contract.validate_bindings([{"id": "b", "role": "body"}], board, 1, [])


def test_requires_every_contact_to_be_bound():
    board = {
        "schemaVersion": 3,
        "id": "x",
        "contacts": [{"id": "a"}, {"id": "b"}],
    }
    nodes = [{"id": "body", "role": "body"}, {"id": "c", "role": "contact", "contact": "a"}]
    with pytest.raises(ValueError, match="does not match"):
        contract.validate_bindings(nodes, board, 1, [])


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REAL_SOURCE = REPOSITORY_ROOT / "Hangboards" / "lattice-triple-rung" / "lattice-triple-rung.FCStd"
REAL_OBJECT_INVENTORY = {
    "Body": "PartDesign::Body",
    "Origin": "App::Origin",
    "X_Axis": "App::Line",
    "Y_Axis": "App::Line",
    "Z_Axis": "App::Line",
    "XY_Plane": "App::Plane",
    "XZ_Plane": "App::Plane",
    "YZ_Plane": "App::Plane",
    "Origin001": "App::Point",
    "Profile": "Sketcher::SketchObject",
    "Pad": "PartDesign::Pad",
    "Region_edge_10": "PartDesign::SubShapeBinder",
    "Surface_edge_10": "Part::Extrusion",
    "Region_edge_20": "PartDesign::SubShapeBinder",
    "Surface_edge_20": "Part::Extrusion",
    "Region_edge_45": "PartDesign::SubShapeBinder",
    "Surface_edge_45": "Part::Extrusion",
}


def test_real_committed_source_document_matches_inventory():
    with REAL_SOURCE.open("rb") as stream:
        if stream.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
            pytest.skip("Git LFS object not fetched in this checkout")
    try:
        result = cad_source.inspect_archive(REAL_SOURCE)
    except ValueError as error:
        if "Git LFS pointer" in str(error):
            pytest.skip("Git LFS object not fetched in this checkout")
        raise
    assert set(result["objects"].values()) <= cad_source.BUILTIN_TYPES
    assert result["objects"] == REAL_OBJECT_INVENTORY
    assert Counter(result["objects"].values()) == {
        "PartDesign::Body": 1,
        "Sketcher::SketchObject": 1,
        "PartDesign::Pad": 1,
        "Part::Extrusion": 3,
        "PartDesign::SubShapeBinder": 3,
        "App::Origin": 1,
        "App::Line": 3,
        "App::Plane": 3,
        "App::Point": 1,
    }
    assert len(result["objects"]) == 17
    assert any("neutral-tulipwood" in member for member in result["members"])
