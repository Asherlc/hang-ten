"""Tests for the fail-closed source archive preflight."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    result = contract.inspect_archive(archive)
    assert result["objects"] == {"Body": "PartDesign::Body"}


def test_rejects_a_missing_document(tmp_path):
    path = tmp_path / "bad.FCStd"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Other.xml", "<x/>")
    with pytest.raises(ValueError, match="missing Document.xml"):
        contract.inspect_archive(path)


def test_rejects_directory_traversal_members(tmp_path):
    archive = build_archive(tmp_path / "trav.FCStd", [("../escape.txt", b"x")])
    with pytest.raises(ValueError, match="unsafe member path"):
        contract.inspect_archive(archive)


def test_rejects_duplicate_case_colliding_members(tmp_path):
    archive = build_archive(
        tmp_path / "dup.FCStd", [("Part.brp", b"a"), ("part.brp", b"b")]
    )
    with pytest.raises(ValueError, match="duplicate or case-colliding"):
        contract.inspect_archive(archive)


def test_rejects_an_unsupported_object_type(tmp_path):
    document = DOCUMENT.replace("PartDesign::Body", "App::FeaturePython")
    archive = build_archive(tmp_path / "py.FCStd", [], document)
    with pytest.raises(ValueError, match="unsupported document object type"):
        contract.inspect_archive(archive)


def test_rejects_an_external_xlink(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="Support" type="App::PropertyXLinkSubList">'
        '<XLinkSubList count="1"><XLink file="/tmp/other.FCStd" name="B"/></XLinkSubList>'
        "</Property></ObjectData>",
    )
    archive = build_archive(tmp_path / "xlink.FCStd", [], document)
    with pytest.raises(ValueError, match="external document reference"):
        contract.inspect_archive(archive)


def test_accepts_a_document_local_xlink(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="Support" type="App::PropertyXLinkSubList">'
        '<XLinkSubList count="1"><XLink file="" name="Profile"/></XLinkSubList>'
        "</Property></ObjectData>",
    )
    archive = build_archive(tmp_path / "local.FCStd", [], document)
    assert contract.inspect_archive(archive)["objects"] == {"Body": "PartDesign::Body"}


def test_rejects_an_absent_included_file(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="TextureFile" type="App::PropertyFileIncluded">'
        '<FileIncluded file="missing.png"/></Property></ObjectData>',
    )
    archive = build_archive(tmp_path / "inc.FCStd", [], document)
    with pytest.raises(ValueError, match="missing included file"):
        contract.inspect_archive(archive)


def test_accepts_a_present_included_file(tmp_path):
    document = DOCUMENT.replace(
        "</ObjectData>",
        '<Property name="TextureFile" type="App::PropertyFileIncluded">'
        '<FileIncluded file="wood.png"/></Property></ObjectData>',
    )
    archive = build_archive(tmp_path / "inc2.FCStd", [("wood.png", b"\x89PNG")], document)
    assert "wood.png" in contract.inspect_archive(archive)["members"]


def test_rejects_a_git_lfs_pointer(tmp_path):
    path = tmp_path / "pointer.FCStd"
    path.write_bytes(
        b"version https://git-lfs.github.com/spec/v1\n"
        b"oid sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
        b"size 10\n"
    )
    with pytest.raises(ValueError, match="Git LFS pointer"):
        contract.inspect_archive(path)


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
