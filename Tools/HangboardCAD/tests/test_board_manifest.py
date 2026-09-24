"""The FCStd board manifest is the source of truth for a CAD board's board.json.

Pure host Python: no FreeCAD, so CI runs this on Linux.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
REPOSITORY = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))

import board_manifest  # noqa: E402
import set_board_manifest  # noqa: E402

# Shaped like a FreeCAD 1.1 document: transient ``_Property`` entries first,
# then the persistent properties sorted by name, then one object.
DOCUMENT = """<?xml version='1.0' encoding='utf-8'?>
<Document SchemaVersion="4" ProgramVersion="1.1R20260725 (Git shallow)" FileVersion="1" StringHasher="1">
    <Properties Count="6" TransientCount="2">
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


def members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info.filename) for info in archive.infolist()}


def test_round_trip_regenerates_board_json_and_leaves_geometry_untouched(tmp_path):
    source = make_package(tmp_path)
    before = members(source)

    assert set_board_manifest.embed(source, board_manifest.board_to_manifest(V1_BOARD))
    after = members(source)

    assert list(after) == list(before)
    assert after["Body.Shape.brp"] == before["Body.Shape.brp"]
    board = board_manifest.load_board(source)
    assert board == V1_BOARD
    assert list(board) == list(V1_BOARD), "id is re-inserted right after schemaVersion"
    rendered = board_manifest.generate_board_json(source)
    assert rendered == (json.dumps(V1_BOARD, indent=2, ensure_ascii=False) + "\n").encode()
    assert "×".encode() in rendered, "non-ASCII stays literal UTF-8"

    # FreeCAD's own layout: inserted between HangTenBoardID and
    # HangTenCoordinateFrame, and the document-level count grows by one only.
    document = after["Document.xml"].decode()
    assert '<Properties Count="7" TransientCount="2">' in document
    assert '<Properties Count="1" TransientCount="0">' in document
    order = [document.index(name) for name in (
        'name="HangTenBoardID"', 'name="HangTenBoardManifest"', 'name="HangTenCoordinateFrame"'
    )]
    assert order == sorted(order)


def test_embedding_is_idempotent_and_replaces_in_place(tmp_path):
    source = make_package(tmp_path)
    manifest = board_manifest.board_to_manifest(V1_BOARD)
    assert set_board_manifest.embed(source, manifest)
    first = source.read_bytes()
    assert not set_board_manifest.embed(source, manifest)
    assert source.read_bytes() == first

    changed = dict(manifest, subtitle="A different subtitle.")
    assert set_board_manifest.embed(source, changed)
    document = members(source)["Document.xml"].decode()
    assert document.count('name="HangTenBoardManifest"') == 1
    assert '<Properties Count="7" TransientCount="2">' in document
    assert board_manifest.load_board(source)["subtitle"] == "A different subtitle."


def test_v2_reusable_slot_board_round_trips():
    """The committed Metolius Rock Rings board is schema v2: slots and instances."""
    committed = REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "board.json"
    board = json.loads(committed.read_text(encoding="utf-8"))
    instances = board["presentations"][0]["media"]["instances"]
    assert all("contactIDsBySlotID" in instance for instance in instances)

    manifest = board_manifest.board_to_manifest(board)
    assert "id" not in manifest
    stored = board_manifest.render_manifest(manifest)
    assert "\n" not in stored
    rebuilt = board_manifest.manifest_to_board(board_manifest.parse_manifest(stored), board["id"])
    assert board_manifest.render_board(rebuilt) == board_manifest.render_board(board)
    assert list(rebuilt) == list(board), "contacts-before-presentations order is kept"


def test_v2_board_embeds_into_a_source(tmp_path):
    committed = REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "board.json"
    board = json.loads(committed.read_text(encoding="utf-8"))
    source = make_package(tmp_path, board_id=board["id"])
    set_board_manifest.embed(source, board_manifest.board_to_manifest(board))
    assert board_manifest.generate_board_json(source) == board_manifest.render_board(board)


def test_stale_and_hand_edited_board_json_is_detected(tmp_path):
    source = make_package(tmp_path)
    set_board_manifest.embed(source, board_manifest.board_to_manifest(V1_BOARD))
    target = source.parent / "board.json"

    assert board_manifest.check_package(tmp_path, "example") is not None  # missing
    assert board_manifest.write_package(tmp_path, "example")
    assert not board_manifest.write_package(tmp_path, "example")
    assert board_manifest.check_package(tmp_path, "example") is None
    assert board_manifest.main(["--check", "--all", "--root", str(tmp_path)]) == 0

    edited = json.loads(target.read_text(encoding="utf-8"))
    edited["subtitle"] = "hand edit"
    target.write_text(json.dumps(edited, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert "stale or hand-edited" in board_manifest.check_package(tmp_path, "example")
    assert board_manifest.main(["--check", "--all", "--root", str(tmp_path)]) == 1

    # Formatting drift alone is also stale: the file is a generated output.
    target.write_text(json.dumps(V1_BOARD, indent=4) + "\n", encoding="utf-8")
    assert board_manifest.check_package(tmp_path, "example") is not None
    assert board_manifest.main(["--package", "example", "--root", str(tmp_path)]) == 0
    assert board_manifest.check_package(tmp_path, "example") is None


def test_a_source_without_a_manifest_fails_the_check(tmp_path):
    make_package(tmp_path)
    assert "carries no HangTenBoardManifest" in board_manifest.check_package(tmp_path, "example")


def test_the_manifest_may_not_carry_the_derived_id(tmp_path):
    with pytest.raises(board_manifest.ManifestError, match="derived key 'id'"):
        board_manifest.manifest_to_board(dict(V1_BOARD), "example")
    source = make_package(tmp_path)
    with pytest.raises(board_manifest.ManifestError):
        set_board_manifest.embed(source, dict(V1_BOARD))


def test_input_id_must_match_the_cad_board_id(tmp_path):
    board_path = tmp_path / "board.json"
    board_path.write_text(json.dumps(dict(V1_BOARD, id="other")), encoding="utf-8")
    with pytest.raises(board_manifest.ManifestError, match="HangTenBoardID"):
        set_board_manifest.read_input(board_path, "example")
    board_path.write_text(json.dumps(V1_BOARD), encoding="utf-8")
    assert "id" not in set_board_manifest.read_input(board_path, "example")


def test_an_lfs_pointer_is_rejected_with_a_fetch_hint(tmp_path):
    directory = tmp_path / "Hangboards" / "example"
    directory.mkdir(parents=True)
    (directory / "example.FCStd").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:" + "0" * 64 + "\nsize 1\n"
    )
    assert "LFS" in board_manifest.check_package(tmp_path, "example")
    rendering = board_manifest.describe_source(directory / "example.FCStd")
    assert rendering.startswith("Git LFS pointer")


def test_textconv_rendering_shows_the_manifest_and_member_digests(tmp_path):
    source = make_package(tmp_path)
    set_board_manifest.embed(source, board_manifest.board_to_manifest(V1_BOARD))
    rendering = board_manifest.describe_source(source)
    assert "HangTenBoardID = example" in rendering
    assert '  "subtitle": "Quotes' in rendering, "manifest is pretty-printed"
    assert "Body.Shape.brp" in rendering


def test_committed_cad_packages_have_fresh_generated_board_json():
    packages = board_manifest.source_backed_packages(REPOSITORY)
    assert packages
    sources = [board_manifest.package_source(REPOSITORY, p) for p in packages]
    if any(board_manifest._is_lfs_pointer(source) for source in sources):
        pytest.skip("FCStd sources are Git LFS pointers; run `git lfs pull` first")
    problems = [problem for p in packages if (problem := board_manifest.check_package(REPOSITORY, p))]
    assert not problems


def test_number_spelling_survives_the_manifest(tmp_path):
    """The package validator reads number lexemes (nine-decimal translations)."""
    text = (
        '{"schemaVersion":3,"id":"example","aspectRatio":1.6666667,'
        '"presentations":[{"translation":[0.000000000,-0.012500000,9E-9,4.3e-8,1.0,2]}]}'
    )
    board = board_manifest.loads(text)
    source = make_package(tmp_path)
    set_board_manifest.embed(source, board_manifest.board_to_manifest(board))
    rendered = board_manifest.generate_board_json(source).decode()
    assert '"aspectRatio": 1.6666667,' in rendered
    for lexeme in ("0.000000000", "-0.012500000", "9E-9", "4.3e-8", "1.0"):
        assert f"\n        {lexeme}" in rendered
    assert "\n        2\n" in rendered
    assert board_manifest.render_board(board_manifest.loads(rendered)).decode() == rendered


def test_generator_layout_matches_json_dumps_for_plain_values():
    assert board_manifest.render_board(V1_BOARD) == (
        json.dumps(V1_BOARD, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    empty = {"schemaVersion": 3, "a": [], "b": {}, "c": [[]], "d": None, "e": True}
    assert board_manifest.render_board(empty) == (json.dumps(empty, indent=2) + "\n").encode()
