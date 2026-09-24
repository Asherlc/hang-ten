"""The FCStd board manifest is the source of truth for a CAD board's board.json.

board.json is generated from it at build time and is never committed. Pure host
Python: no FreeCAD, so CI runs this on Linux.
"""

from __future__ import annotations

import json
import re
import stat
import sys
import zipfile
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
REPOSITORY = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))

import use_hangboard_packages  # noqa: E402,F401
from hangboard_packages import cad_source  # noqa: E402

import board_manifest  # noqa: E402
import set_board_manifest  # noqa: E402

# Shaped like a FreeCAD 1.1 document: transient ``_Property`` entries first,
# then the persistent properties sorted by name, then one object.
DOCUMENT = """<?xml version='1.0' encoding='utf-8'?>
<Document SchemaVersion="4" ProgramVersion="1.1R20260725 (Git shallow)" FileVersion="1" StringHasher="1">
    <Properties Count="4" TransientCount="2">
        <_Property name="FileName" type="App::PropertyString" status="50331649"/>
        <_Property name="Tip" type="App::PropertyLink" status="33554433"/>
        <Property name="Comment" type="App::PropertyString">
            <String value=""/>
        </Property>
        <Property name="HangTenBoardID" type="App::PropertyString" group="HangTen" doc="" attr="0" ro="0" hide="0" status="2097153">
            <String value="{board_id}"/>
        </Property>
        <Property name="HangTenCoordinateFrame" type="App::PropertyString" group="HangTen" doc="" attr="0" ro="0" hide="0" status="2097153">
            <String value="freecad-mm-z-up-front-negative-y"/>
        </Property>
        <Property name="Label" type="App::PropertyString" status="16777217">
            <String value="example"/>
        </Property>
    </Properties>
    <Objects Count="1">
        <Object type="PartDesign::Body" name="Body"/>
    </Objects>
    <ObjectData Count="1">
        <Object name="Body">
            <Properties Count="1" TransientCount="0">
                <Property name="Label" type="App::PropertyString">
                    <String value="Body"/>
                </Property>
            </Properties>
        </Object>
    </ObjectData>
</Document>
"""

V1_BOARD = {
    "schemaVersion": 3,
    "id": "example",
    "manufacturer": "Example",
    "name": "Example × Board",
    "subtitle": "Quotes \" & <angle> 'apostrophes' and a \\ backslash.",
    "productURL": "https://example.com/board",
    "dimensions": "55 × 13 × 5 cm",
    "aspectRatio": 4.2307694857988265,
    "presentations": [{"id": "primary", "aspectRatio": 4.2307694857988265}],
    "revisionID": "r1",
    "contacts": [
        {"id": "edge-20", "depth": {"range": {"minimum": 20, "maximum": 20}}},
        {"id": "edge-10", "depth": {"range": {"minimum": 10.5, "maximum": 10.5}}},
    ],
}


def make_package(root: Path, package: str = "example", board_id: str = "example") -> Path:
    directory = root / "Hangboards" / package
    directory.mkdir(parents=True)
    source = directory / f"{package}.FCStd"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Document.xml", DOCUMENT.replace("{board_id}", board_id))
        archive.writestr("Body.Shape.brp", b"geometry bytes that must never change")
    return source


def document_level_counts(document: str) -> tuple[int, int, int, int]:
    """(declared Count, declared TransientCount, <Property> children,
    <_Property> children) of the document-level Properties block."""
    header = re.search(r'<Properties Count="(\d+)" TransientCount="(\d+)">', document)
    block = document[header.end(): document.index("</Properties>", header.end())]
    return (
        int(header.group(1)),
        int(header.group(2)),
        block.count("<Property "),
        block.count("<_Property "),
    )


def committed_source(package: str) -> Path:
    source = board_manifest.package_source(REPOSITORY, package)
    if cad_source._is_lfs_pointer(source):
        pytest.skip("FCStd sources are Git LFS pointers; run `git lfs pull` first")
    return source


def members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info.filename) for info in archive.infolist()}


def test_round_trip_regenerates_board_json_and_leaves_geometry_untouched(tmp_path):
    source = make_package(tmp_path)
    before = members(source)

    assert set_board_manifest.embed(source, cad_source.board_to_manifest(V1_BOARD))
    after = members(source)

    assert list(after) == list(before)
    assert after["Body.Shape.brp"] == before["Body.Shape.brp"]
    board = cad_source.load_board(source)
    assert board == V1_BOARD
    assert list(board) == list(V1_BOARD), "id is re-inserted right after schemaVersion"
    rendered = cad_source.generate_board_json(source)
    assert rendered == (json.dumps(V1_BOARD, indent=2, ensure_ascii=False) + "\n").encode()
    assert "×".encode() in rendered, "non-ASCII stays literal UTF-8"

    # FreeCAD's own layout: inserted between HangTenBoardID and
    # HangTenCoordinateFrame, and the document-level count grows by one only.
    document = after["Document.xml"].decode()
    assert document_level_counts(before["Document.xml"].decode()) == (4, 2, 4, 2)
    assert document_level_counts(document) == (5, 2, 5, 2)
    assert '<Properties Count="1" TransientCount="0">' in document
    order = [document.index(name) for name in (
        'name="HangTenBoardID"', 'name="HangTenBoardManifest"', 'name="HangTenCoordinateFrame"'
    )]
    assert order == sorted(order)


def test_embedding_is_idempotent_and_replaces_in_place(tmp_path):
    source = make_package(tmp_path)
    manifest = cad_source.board_to_manifest(V1_BOARD)
    assert set_board_manifest.embed(source, manifest)
    first = source.read_bytes()
    assert not set_board_manifest.embed(source, manifest)
    assert source.read_bytes() == first

    changed = dict(manifest, subtitle="A different subtitle.")
    assert set_board_manifest.embed(source, changed)
    document = members(source)["Document.xml"].decode()
    assert document.count('name="HangTenBoardManifest"') == 1
    assert document_level_counts(document) == (5, 2, 5, 2)
    assert cad_source.load_board(source)["subtitle"] == "A different subtitle."


def test_embedding_keeps_the_source_file_mode(tmp_path):
    source = make_package(tmp_path)
    source.chmod(0o644)
    assert set_board_manifest.embed(source, cad_source.board_to_manifest(V1_BOARD))
    assert stat.S_IMODE(source.stat().st_mode) == 0o644


def test_v2_reusable_slot_board_round_trips():
    """The Metolius Rock Rings board is schema v2: slots and instances."""
    board = cad_source.loads(
        cad_source.generate_board_json(committed_source("metolius-rock-rings-3d")).decode()
    )
    instances = board["presentations"][0]["media"]["instances"]
    assert all("contactIDsBySlotID" in instance for instance in instances)

    manifest = cad_source.board_to_manifest(board)
    assert "id" not in manifest
    stored = cad_source.render_manifest(manifest)
    assert "\n" not in stored
    rebuilt = cad_source.manifest_to_board(cad_source.parse_manifest(stored), board["id"])
    assert cad_source.render_board(rebuilt) == cad_source.render_board(board)
    assert list(rebuilt) == list(board), "contacts-before-presentations order is kept"


def test_v2_board_embeds_into_a_source(tmp_path):
    board = cad_source.load_board(committed_source("metolius-rock-rings-3d"))
    source = make_package(tmp_path, board_id=board["id"])
    set_board_manifest.embed(source, cad_source.board_to_manifest(board))
    assert cad_source.generate_board_json(source) == cad_source.render_board(board)


def test_generated_board_json_is_written_only_outside_the_package(tmp_path):
    source = make_package(tmp_path)
    set_board_manifest.embed(source, cad_source.board_to_manifest(V1_BOARD))
    expected = cad_source.render_board(V1_BOARD)

    with pytest.raises(cad_source.ManifestError, match="must not exist in the package"):
        board_manifest.write_board_json(source, source.parent / "board.json")
    assert not (source.parent / "board.json").exists()

    output = tmp_path / "out" / "board.json"
    assert board_manifest.write_board_json(source, output)
    assert not board_manifest.write_board_json(source, output)
    assert output.read_bytes() == expected

    root = ["--root", str(tmp_path)]
    other = tmp_path / "cli.json"
    assert board_manifest.main(["--package", "example", "--output", str(other), *root]) == 0
    assert other.read_bytes() == expected
    assert board_manifest.main(["--all", "--output-dir", str(tmp_path / "all"), *root]) == 0
    assert (tmp_path / "all" / "example" / "board.json").read_bytes() == expected
    assert board_manifest.main(["--all", *root]) == 0


def test_all_with_no_cad_packages_is_a_no_op(tmp_path, capsys):
    (tmp_path / "Hangboards").mkdir()
    assert board_manifest.main(["--all", "--root", str(tmp_path)]) == 0
    assert "0 CAD-backed package(s)" in capsys.readouterr().out


def test_a_source_without_a_manifest_does_not_generate(tmp_path):
    source = make_package(tmp_path)
    with pytest.raises(cad_source.ManifestError, match="carries no HangTenBoardManifest"):
        cad_source.generate_board_json(source)


def test_a_corrupt_source_is_a_manifest_error(tmp_path):
    source = make_package(tmp_path)
    source.write_bytes(b"not a zip archive")
    with pytest.raises(cad_source.ManifestError):
        cad_source.has_manifest(source)
    with pytest.raises(cad_source.ManifestError):
        cad_source.load_board(source)
    # main raises; its __main__ wrapper reports MANIFEST ERROR and exits 1.
    with pytest.raises(cad_source.ManifestError):
        set_board_manifest.main(["--source", str(source), str(tmp_path / "missing.json")])


def test_duplicate_manifest_keys_are_rejected():
    with pytest.raises(cad_source.ManifestError, match="duplicate JSON key: 'name'"):
        cad_source.parse_manifest('{"schemaVersion":3,"name":"a","name":"b"}')
    with pytest.raises(cad_source.ManifestError, match="duplicate JSON key"):
        cad_source.loads('{"a":{"b":1,"b":2}}')
    assert list(cad_source.loads('{"b":1,"a":2}')) == ["b", "a"]


def test_the_manifest_may_not_carry_the_derived_id(tmp_path):
    with pytest.raises(cad_source.ManifestError, match="derived key 'id'"):
        cad_source.manifest_to_board(dict(V1_BOARD), "example")
    source = make_package(tmp_path)
    with pytest.raises(cad_source.ManifestError):
        set_board_manifest.embed(source, dict(V1_BOARD))


def test_input_id_must_match_the_cad_board_id(tmp_path):
    board_path = tmp_path / "board.json"
    board_path.write_text(json.dumps(dict(V1_BOARD, id="other")), encoding="utf-8")
    with pytest.raises(cad_source.ManifestError, match="HangTenBoardID"):
        set_board_manifest.read_input(board_path, "example")
    board_path.write_text(json.dumps(V1_BOARD), encoding="utf-8")
    assert "id" not in set_board_manifest.read_input(board_path, "example")


def test_an_lfs_pointer_is_rejected_with_a_fetch_hint(tmp_path):
    directory = tmp_path / "Hangboards" / "example"
    directory.mkdir(parents=True)
    (directory / "example.FCStd").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:" + "0" * 64 + "\nsize 1\n"
    )
    with pytest.raises(cad_source.ManifestError, match="LFS"):
        cad_source.generate_board_json(directory / "example.FCStd")
    rendering = board_manifest.describe_source(directory / "example.FCStd")
    assert rendering.startswith("Git LFS pointer")


def test_textconv_rendering_shows_the_manifest_and_member_digests(tmp_path):
    source = make_package(tmp_path)
    set_board_manifest.embed(source, cad_source.board_to_manifest(V1_BOARD))
    rendering = board_manifest.describe_source(source)
    assert "HangTenBoardID = example" in rendering
    assert '  "subtitle": "Quotes' in rendering, "manifest is pretty-printed"
    assert "Body.Shape.brp" in rendering


def test_committed_cad_packages_generate_board_json_and_commit_none():
    packages = board_manifest.source_backed_packages(REPOSITORY)
    assert packages
    for package in packages:
        board = cad_source.load_board(committed_source(package))
        assert board["id"] and board["schemaVersion"] == 3
        assert not (REPOSITORY / "Hangboards" / package / "board.json").exists(), (
            f"{package}: board.json is generated at build time and must not exist"
        )


def test_number_spelling_survives_the_manifest(tmp_path):
    """The package validator reads number lexemes (nine-decimal translations)."""
    text = (
        '{"schemaVersion":3,"id":"example","aspectRatio":1.6666667,'
        '"presentations":[{"translation":[0.000000000,-0.012500000,9E-9,4.3e-8,1.0,2]}]}'
    )
    board = cad_source.loads(text)
    source = make_package(tmp_path)
    set_board_manifest.embed(source, cad_source.board_to_manifest(board))
    rendered = cad_source.generate_board_json(source).decode()
    assert '"aspectRatio": 1.6666667,' in rendered
    for lexeme in ("0.000000000", "-0.012500000", "9E-9", "4.3e-8", "1.0"):
        assert f"\n        {lexeme}" in rendered
    assert "\n        2\n" in rendered
    assert cad_source.render_board(cad_source.loads(rendered)).decode() == rendered


def test_generator_layout_matches_json_dumps_for_plain_values():
    assert cad_source.render_board(V1_BOARD) == (
        json.dumps(V1_BOARD, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    empty = {"schemaVersion": 3, "a": [], "b": {}, "c": [[]], "d": None, "e": True}
    assert cad_source.render_board(empty) == (json.dumps(empty, indent=2) + "\n").encode()
