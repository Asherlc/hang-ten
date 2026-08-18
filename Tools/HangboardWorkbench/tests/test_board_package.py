from __future__ import annotations

import base64
import copy
import errno
import importlib.util
import json
import os
import shutil
import struct
import sys
import zlib
from pathlib import Path
from types import ModuleType

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_MODULE_ROOT = (
    REPOSITORY_ROOT / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer"
)
VALIDATION_FIXTURES = json.loads(
    (
        REPOSITORY_ROOT
        / "HangTenTests"
        / "Fixtures"
        / "BoardPackageValidationFixtures.json"
    ).read_text(encoding="utf-8")
)
assert VALIDATION_FIXTURES["outOfBoundsFrames"], (
    "outOfBoundsFrames must contain at least one fixture"
)
SUPPORTED_HOLD_KINDS = ("jug", "edge", "pocket", "pinch", "sloper")
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_package import BoardPackageError  # noqa: E402
from workbench_fixtures import (  # noqa: E402
    CANONICAL_PACKAGE,
    PRIMARY_IMAGE,
    board_document,
)


def _load_stage_module(module_name: str) -> ModuleType:
    stage_path = REPOSITORY_ROOT / "scripts" / "stage-board-packages.py"
    spec = importlib.util.spec_from_file_location(module_name, stage_path)
    assert spec is not None
    assert spec.loader is not None
    stage_module = importlib.util.module_from_spec(spec)
    previous_bytecode_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(stage_module)
    finally:
        sys.dont_write_bytecode = previous_bytecode_setting
    return stage_module


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def _indexed_png_with_palette_after_idat() -> bytes:
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 3, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(b"\x00\x00")),
            _png_chunk(b"PLTE", b"\x00\x00\x00"),
            _png_chunk(b"IEND", b""),
        )
    )


def _png_with_corrupt_post_ihdr_data() -> bytes:
    data = bytearray(PRIMARY_IMAGE.read_bytes())
    data[-1] ^= 0xFF
    return bytes(data)


def _write_finished_package(
    library: Path,
    slug: str,
    board_id: str,
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    package = library / slug
    assets = package / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PRIMARY_IMAGE, assets / "primary.png")
    _write_json(
        package / "board.json",
        board_document(board_id, manufacturer=manufacturer, name=name),
    )
    return package


def _write_draft(library: Path, slug: str) -> Path:
    assets = library / slug / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PRIMARY_IMAGE, assets / "primary.png")
    return assets.parent


def _library(tmp_path: Path) -> Path:
    library = tmp_path / "Hangboards"
    library.mkdir()
    return library


def _read_board(package: Path) -> dict[str, object]:
    return json.loads((package / "board.json").read_text(encoding="utf-8"))


def _mutate_board(package: Path, mutation) -> None:
    board = _read_board(package)
    mutation(board)
    _write_json(package / "board.json", board)


def _replace_holds_with_supported_kinds(board: dict[str, object]) -> None:
    holds = board["holds"]
    assert isinstance(holds, list) and holds and isinstance(holds[0], dict)
    template = holds[0]
    board["holds"] = [
        {
            **template,
            "id": f"hold-{kind}",
            "name": f"Fixture {kind}",
            "kind": kind,
        }
        for kind in SUPPORTED_HOLD_KINDS
    ]


def _package_snapshot(package: Path) -> dict[str, bytes]:
    return {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }


def test_canonical_package_has_the_exact_single_file_inventory() -> None:
    assert {path.name for path in CANONICAL_PACKAGE.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (CANONICAL_PACKAGE / "assets").iterdir()} == {
        "primary.png"
    }

    package = board_package.load_board_package(CANONICAL_PACKAGE)

    assert package.board_id == "metolius.wood-grips-compact-ii"
    assert len(package.hold_ids) == 19
    assert all(hold["geometry"] for hold in package.board["holds"])
    assert all("cueStyle" not in hold for hold in package.board["holds"])
    for hold in package.board["holds"]:
        for piece in hold["geometry"]:
            if piece["shape"]["type"] != "path":
                continue
            points = [
                coordinates
                for command in piece["shape"]["commands"]
                for key, coordinates in command.items()
                if key != "command"
            ]
            assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
            assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
            assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
            assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)


def test_png_byte_helpers_decode_the_same_primary_image_dimensions() -> None:
    image = PRIMARY_IMAGE.read_bytes()

    assert board_package._png_header_dimensions_from_bytes(image[:33]) == (1774, 457)
    assert board_package._png_dimensions_from_bytes(image) == (1774, 457)


def test_apply_editor_document_returns_updated_board_without_mutating_its_input() -> None:
    package = board_package.load_board_package(CANONICAL_PACKAGE)
    document = board_package.editor_document(package)
    parsed = board_package._validate_editor_document(
        document, package.image_width, package.image_height
    )
    pieces_by_hold: dict[str, list[tuple[int, str, object]]] = {}
    for hold_id, piece_index, kind, path in parsed.values():
        pieces_by_hold.setdefault(hold_id, []).append((piece_index, kind, path))
    for pieces in pieces_by_hold.values():
        pieces.sort(key=lambda item: item[0])
    first_hold_id = next(iter(pieces_by_hold))
    first_piece = pieces_by_hold[first_hold_id][0]
    pieces_by_hold[first_hold_id][0] = (first_piece[0], "sloper", first_piece[2])
    original = copy.deepcopy(package.board)

    updated = board_package._apply_editor_document(
        package.board, pieces_by_hold, package.image_width, package.image_height
    )

    assert package.board == original
    updated_hold = next(hold for hold in updated["holds"] if hold["id"] == first_hold_id)
    assert updated_hold["name"] == next(
        hold["name"] for hold in original["holds"] if hold["id"] == first_hold_id
    )
    assert updated_hold["kind"] == "sloper"


def test_discovers_direct_children_without_a_catalog_and_sorts_physical_boards(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "zeta-model", "zeta.board", manufacturer="Zeta")
    _write_finished_package(
        library,
        "alpha-zulu",
        "alpha.zulu",
        manufacturer="Alpha",
        name="Zulu",
    )
    _write_finished_package(
        library,
        "alpha-alpha-b",
        "alpha.b",
        manufacturer="Alpha",
        name="Alpha",
    )
    _write_finished_package(
        library,
        "alpha-alpha-a",
        "alpha.a",
        manufacturer="Alpha",
        name="Alpha",
    )
    _write_draft(library, "draft-model")

    packages = board_package.discover_packages(library)

    assert [package.board_id for package in packages] == [
        "alpha.a",
        "alpha.b",
        "alpha.zulu",
        "zeta.board",
    ]
    assert not (library / "catalog.json").exists()


def test_opening_a_missing_valid_board_raises_not_available_error(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "fixture-board", "fixture.board")

    with pytest.raises(board_package.BoardNotAvailableError):
        board_package.open_package(library, "missing.board")


def test_discovery_uses_the_shared_non_ascii_ordering_contract(tmp_path: Path) -> None:
    library = _library(tmp_path)
    ordering = VALIDATION_FIXTURES["ordering"]
    for package in ordering["packages"]:
        _write_finished_package(
            library,
            package["slug"],
            package["id"],
            manufacturer=package["manufacturer"],
            name=package["name"],
        )

    packages = board_package.discover_packages(library)

    assert [package.board_id for package in packages] == ordering["expectedBoardIDs"]


def test_discovery_excludes_the_exact_internal_recovery_directory(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "current-board", "current.board")
    recovery = library / ".workbench-recovery"
    recovery.mkdir()
    _write_finished_package(
        recovery,
        "current-board-previous-0123456789abcdef0123456789abcdef",
        "previous.board",
    )

    packages = board_package.discover_packages(library)

    assert [package.board_id for package in packages] == ["current.board"]


def test_discovery_does_not_broaden_the_recovery_directory_exclusion(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "current-board", "current.board")
    (library / ".workbench-recovery-old").mkdir()

    with pytest.raises(BoardPackageError):
        board_package.discover_packages(library)


def test_discovery_open_and_noop_save_ignore_abandoned_staging_directories(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "fixture-board", "fixture.board")
    staging_directories = [
        library / ".workbench-edit-abandoned",
        library / ".workbench-save-abandoned",
    ]
    for staging in staging_directories:
        (staging / "partial-package").mkdir(parents=True)
        (staging / "partial-package" / "board.json").write_text(
            "{ incomplete", encoding="utf-8"
        )

    packages = board_package.discover_packages(library)
    package = board_package.open_package(library, "fixture.board")
    saved = board_package.save_editor_document(
        library,
        "fixture-board",
        board_package.editor_document(package),
    )

    assert [candidate.board_id for candidate in packages] == ["fixture.board"]
    assert saved.board_id == "fixture.board"
    assert all(staging.is_dir() for staging in staging_directories)


@pytest.mark.parametrize(
    "lookalike", [".workbench-edit", ".workbench-editor-abandoned", ".workbench-saved"]
)
def test_discovery_does_not_broaden_the_staging_directory_exclusion(
    lookalike: str, tmp_path: Path
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "fixture-board", "fixture.board")
    (library / lookalike).mkdir()

    with pytest.raises(BoardPackageError):
        board_package.discover_packages(library)


@pytest.mark.parametrize("prefix", [".workbench-edit-", ".workbench-save-"])
@pytest.mark.parametrize("unsafe_kind", ["file", "symlink"])
def test_discovery_rejects_unsafe_reserved_staging_paths(
    prefix: str, unsafe_kind: str, tmp_path: Path
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "fixture-board", "fixture.board")
    staging = library / f"{prefix}abandoned"
    if unsafe_kind == "file":
        staging.write_text("unsafe", encoding="utf-8")
    else:
        outside = tmp_path / f"outside-{prefix.removeprefix('.')}"
        outside.mkdir()
        staging.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BoardPackageError):
        board_package.discover_packages(library)


@pytest.mark.parametrize("unsafe_kind", ["file", "symlink"])
def test_discovery_rejects_an_unsafe_reserved_recovery_path(
    unsafe_kind: str, tmp_path: Path
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "current-board", "current.board")
    recovery = library / ".workbench-recovery"
    if unsafe_kind == "file":
        recovery.write_text("unsafe", encoding="utf-8")
    else:
        outside = tmp_path / "outside-recovery"
        outside.mkdir()
        recovery.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BoardPackageError):
        board_package.discover_packages(library)


def test_rejects_a_plausible_png_header_without_complete_image_data(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    truncated = base64.b64decode(
        VALIDATION_FIXTURES["png"]["plausibleHeaderTruncatedBase64"],
        validate=True,
    )
    assert len(truncated) == 24
    assert truncated[:8] == b"\x89PNG\r\n\x1a\n"
    assert truncated[12:16] == b"IHDR"
    (package / "assets" / "primary.png").write_bytes(truncated)

    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.load_board_package(package)


def test_rejects_an_indexed_png_with_palette_after_image_data(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    invalid_png = _indexed_png_with_palette_after_idat()
    assert invalid_png.index(b"IDAT") < invalid_png.index(b"PLTE")
    (package / "assets" / "primary.png").write_bytes(invalid_png)
    _mutate_board(package, lambda board: board.update(aspectRatio=1))

    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.load_board_package(package)


def test_rejects_shared_indexed_png_with_duplicate_palette(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    invalid_png = base64.b64decode(
        VALIDATION_FIXTURES["png"]["duplicatePaletteBase64"],
        validate=True,
    )
    assert invalid_png.count(b"PLTE") == 2
    (package / "assets" / "primary.png").write_bytes(invalid_png)
    _mutate_board(package, lambda board: board.update(aspectRatio=1))

    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.load_board_package(package)


def test_open_ignores_corrupt_post_ihdr_data_in_an_unselected_sibling(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "selected-board", "selected.board")
    corrupt = _write_finished_package(library, "corrupt-board", "corrupt.board")
    (corrupt / "assets" / "primary.png").write_bytes(
        _png_with_corrupt_post_ihdr_data()
    )

    package = board_package.open_package(library, "selected.board")

    assert package.board_id == "selected.board"


def test_open_and_direct_load_reject_selected_corrupt_post_ihdr_data(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    corrupt = _write_finished_package(library, "corrupt-board", "corrupt.board")
    (corrupt / "assets" / "primary.png").write_bytes(
        _png_with_corrupt_post_ihdr_data()
    )

    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.open_package(library, "corrupt.board")
    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.load_board_package(corrupt)


def test_accepts_a_rounded_aspect_ratio_matching_the_primary_canvas(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    _mutate_board(package, lambda board: board.update(aspectRatio=3.88))

    loaded = board_package.load_board_package(package)

    assert loaded.board["aspectRatio"] == 3.88


def test_rejects_an_aspect_ratio_that_does_not_match_the_primary_canvas(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    _mutate_board(package, lambda board: board.update(aspectRatio=34 / 7))

    with pytest.raises(BoardPackageError, match="aspectRatio.*primary image"):
        board_package.load_board_package(package)


def test_final_inventory_rejects_an_exact_primary_only_draft(tmp_path: Path) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "finished-board", "finished.board")
    _write_draft(library, "draft-board")

    with pytest.raises(BoardPackageError, match="draft-board.*board.json"):
        board_package.discover_packages(library, final_inventory=True)


@pytest.mark.parametrize(
    "relative_path",
    [
        "semantics.json",
        "artwork.json",
        "evidence.json",
        "README.md",
        "assets/alternate.png",
    ],
)
def test_rejects_sidecars_and_extra_package_files(
    relative_path: str, tmp_path: Path
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    extra = package / relative_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"{}")

    with pytest.raises(BoardPackageError, match="only board.json and assets/primary.png"):
        board_package.load_board_package(package)


def test_rejects_root_catalog_malformed_drafts_and_invalid_pngs(tmp_path: Path) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "fixture-board", "fixture.board")
    (library / "catalog.json").write_text("{}", encoding="utf-8")

    with pytest.raises(BoardPackageError, match="direct child directories"):
        board_package.discover_packages(library)

    (library / "catalog.json").unlink()
    malformed = _write_draft(library, "malformed-draft")
    (malformed / "notes.txt").write_text("not an exact draft", encoding="utf-8")
    with pytest.raises(BoardPackageError, match="malformed-draft"):
        board_package.discover_packages(library)

    shutil.rmtree(malformed)
    package = library / "fixture-board"
    (package / "assets" / "primary.png").write_bytes(b"not a PNG")
    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.load_board_package(package)


def test_rejects_symlinked_packages_and_members(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    outside = tmp_path / "outside-board"
    shutil.move(package, outside)
    package.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BoardPackageError, match="symlink"):
        board_package.discover_packages(library)

    package.unlink()
    shutil.move(outside, package)
    image = package / "assets" / "primary.png"
    outside_image = tmp_path / "outside.png"
    shutil.move(image, outside_image)
    image.symlink_to(outside_image)
    with pytest.raises(BoardPackageError, match="symlink"):
        board_package.load_board_package(package)


def test_rejects_duplicate_discovered_board_and_hold_ids(tmp_path: Path) -> None:
    library = _library(tmp_path)
    _write_finished_package(library, "first-board", "duplicate.board")
    _write_finished_package(library, "second-board", "duplicate.board")
    with pytest.raises(BoardPackageError, match="duplicate board ID"):
        board_package.discover_packages(library)

    shutil.rmtree(library / "second-board")
    package = library / "first-board"
    _mutate_board(
        package,
        lambda board: board["holds"].append(dict(board["holds"][0])),
    )
    with pytest.raises(BoardPackageError, match="duplicate hold ID"):
        board_package.load_board_package(package)


def test_accepts_exact_physical_hold_kind_enum(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    assert board_package._HOLD_KINDS == frozenset(SUPPORTED_HOLD_KINDS)
    _mutate_board(package, _replace_holds_with_supported_kinds)

    loaded = board_package.load_board_package(package)

    assert [hold["kind"] for hold in loaded.board["holds"]] == list(
        SUPPORTED_HOLD_KINDS
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda hold: hold.pop("kind"), "kind"),
        (lambda hold: hold.__setitem__("kind", "crimp"), "kind must be one of"),
        (lambda hold: hold.__setitem__("geometry", []), "geometry must be non-empty"),
    ],
)
def test_requires_physical_kind_and_nonempty_geometry(
    mutation, message: str, tmp_path: Path
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    _mutate_board(package, lambda board: mutation(board["holds"][0]))

    with pytest.raises(BoardPackageError, match=message):
        board_package.load_board_package(package)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda piece: piece["frame"].__setitem__("x", -0.1),
            "normalized canvas",
        ),
        (
            lambda piece: piece.__setitem__(
                "shape",
                {
                    "type": "path",
                    "commands": [
                        {"command": "move", "to": [0.1, 0.1]},
                        {"command": "line", "to": [0.5, 0.1]},
                        {"command": "line", "to": [0.5, 0.5]},
                        {"command": "close"},
                    ],
                },
            ),
            "frame must match its derived shape bounds",
        ),
    ],
)
def test_rejects_malformed_normalized_geometry_and_mismatched_bounds(
    mutation, message: str, tmp_path: Path
) -> None:
    library = _library(tmp_path)
    package = _write_finished_package(library, "fixture-board", "fixture.board")
    _mutate_board(package, lambda board: mutation(board["holds"][0]["geometry"][0]))

    with pytest.raises(BoardPackageError, match=message):
        board_package.load_board_package(package)


@pytest.mark.parametrize(
    "fixture",
    VALIDATION_FIXTURES["outOfBoundsFrames"],
    ids=lambda fixture: fixture["name"],
)
def test_rejects_shared_out_of_bounds_normalized_frames(
    fixture: dict[str, object],
) -> None:
    with pytest.raises(board_package.GeometryError, match="normalized canvas"):
        board_package.NormalizedFrame.from_json(
            fixture["frame"],
            fixture["name"],
        )


def test_preserves_optional_metadata_and_derives_a_multipiece_union_frame(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(
        library, "fixture-board", "fixture.board"
    )

    package = board_package.load_board_package(package_root)
    hold = package.board["holds"][0]

    assert set(hold) == {"id", "name", "kind", "geometry"}
    assert package.hold_frame("hold-left").to_json() == {
        "x": 0.05,
        "y": 0.1,
        "width": 0.4,
        "height": 0.4,
    }


def test_editor_exposes_independently_keyed_pieces_for_one_physical_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path)
    package = board_package.load_board_package(
        _write_finished_package(library, "fixture-board", "fixture.board")
    )
    monkeypatch.setattr(
        board_package,
        "_png_dimensions",
        lambda _path: pytest.fail("editor_document repeated complete PNG validation"),
    )
    monkeypatch.setattr(
        board_package,
        "_png_header_dimensions",
        lambda _path: pytest.fail("editor_document repeated PNG header inspection"),
    )

    document = board_package.editor_document(package)

    assert document["canvas"] == {"width": 1774, "height": 457}
    assert [region["key"] for region in document["regions"]] == [
        "hold-left-piece-0",
        "hold-left-piece-1",
    ]
    assert [region["metadata"] for region in document["regions"]] == [
        {"holdID": "hold-left", "pieceIndex": 0},
        {"holdID": "hold-left", "pieceIndex": 1},
    ]


def test_open_save_round_trip_keeps_board_json_and_creates_no_sidecar(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(
        library, "fixture-board", "fixture.board"
    )
    before = (package_root / "board.json").read_bytes()
    package = board_package.open_package(library, "fixture.board")

    saved = board_package.save_editor_document(
        library,
        package.root.name,
        board_package.editor_document(package),
    )

    assert (package_root / "board.json").read_bytes() == before
    assert board_package.editor_document(saved)["regions"][0]["key"] == (
        "hold-left-piece-0"
    )
    assert {path.name for path in package_root.iterdir()} == {"board.json", "assets"}
    assert not (library / "catalog.json").exists()


def test_noop_save_rejects_selected_live_package_with_corrupt_post_ihdr_data(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(
        library, "fixture-board", "fixture.board"
    )
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    (package_root / "assets" / "primary.png").write_bytes(
        _png_with_corrupt_post_ihdr_data()
    )

    with pytest.raises(BoardPackageError, match="PNG"):
        board_package.save_editor_document(library, "fixture-board", document)


def test_save_updates_one_piece_inside_board_json_and_preserves_its_sibling(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(
        library, "fixture-board", "fixture.board"
    )
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    second_piece_before = _read_board(package_root)["holds"][0]["geometry"][1]
    document["regions"][0]["displayPath"] = (
        "M 177.4 45.7 L 354.8 45.7 L 354.8 137.1 L 177.4 137.1 Z"
    )

    saved = board_package.save_editor_document(library, "fixture-board", document)
    hold = _read_board(package_root)["holds"][0]

    assert hold["geometry"][0]["frame"] == {
        "x": 0.1,
        "y": 0.1,
        "width": 0.1,
        "height": 0.2,
    }
    assert hold["geometry"][1] == second_piece_before
    assert saved.hold_frame("hold-left").to_json() == {
        "x": 0.1,
        "y": 0.1,
        "width": 0.35,
        "height": 0.2,
    }
    assert not (library / "catalog.json").exists()


def test_changed_save_derives_current_display_paths_once_per_piece(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"][0]["displayPath"] = (
        "M 177.4 45.7 L 354.8 45.7 L 354.8 137.1 L 177.4 137.1 Z"
    )
    original_display_path_for_shape = board_package.display_path_for_shape
    calls = 0

    def counted_display_path_for_shape(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original_display_path_for_shape(*args, **kwargs)

    monkeypatch.setattr(
        board_package, "display_path_for_shape", counted_display_path_for_shape
    )

    board_package.save_editor_document(library, "fixture-board", document)

    assert calls == 6


def test_invalid_save_leaves_the_live_single_file_package_unchanged(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(
        library, "fixture-board", "fixture.board"
    )
    document = board_package.editor_document(
        board_package.load_board_package(package_root)
    )
    document["regions"][0]["displayPath"] = (
        "M 10 10 L 90 90 L 10 90 L 90 10 Z"
    )
    before = _package_snapshot(package_root)

    with pytest.raises(BoardPackageError, match="self-intersect"):
        board_package.save_editor_document(library, "fixture-board", document)

    assert _package_snapshot(package_root) == before
    assert not (library / "catalog.json").exists()


def test_save_recategorizes_a_hold_across_all_its_pieces(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    for region in document["regions"]:
        region["type"] = "edge"

    saved = board_package.save_editor_document(library, "fixture-board", document)

    assert _read_board(package_root)["holds"][0]["kind"] == "edge"
    assert saved.board["holds"][0]["kind"] == "edge"


def test_save_rejects_a_hold_with_pieces_of_mixed_kinds(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"][0]["type"] = "edge"

    with pytest.raises(BoardPackageError, match="share one kind"):
        board_package.save_editor_document(library, "fixture-board", document)


def test_save_rejects_an_unsupported_hold_kind(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"][0]["type"] = "crimp"
    document["regions"][1]["type"] = "crimp"

    with pytest.raises(BoardPackageError, match="must be one of"):
        board_package.save_editor_document(library, "fixture-board", document)


def test_save_adds_a_new_hold(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"].append(
        {
            "id": 99,
            "key": "hold-right-piece-0",
            "type": "pinch",
            "displayPath": "M 900 100 L 950 100 L 950 150 Z",
            "metadata": {"holdID": "hold-right", "pieceIndex": 0},
        }
    )

    saved = board_package.save_editor_document(library, "fixture-board", document)
    holds = _read_board(package_root)["holds"]

    assert [hold["id"] for hold in holds] == ["hold-left", "hold-right"]
    new_hold = holds[1]
    assert new_hold["kind"] == "pinch"
    assert new_hold["name"]
    assert len(new_hold["geometry"]) == 1
    assert saved.hold_ids == ("hold-left", "hold-right")


def test_save_rejects_deleting_the_only_hold(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"] = []

    with pytest.raises(BoardPackageError, match="non-empty"):
        board_package.save_editor_document(library, "fixture-board", document)


def test_save_deletes_one_of_several_holds(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    _mutate_board(package_root, _replace_holds_with_supported_kinds)
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"] = [
        region
        for region in document["regions"]
        if region["metadata"]["holdID"] != "hold-jug"
    ]

    saved = board_package.save_editor_document(library, "fixture-board", document)

    expected_ids = {f"hold-{kind}" for kind in SUPPORTED_HOLD_KINDS if kind != "jug"}
    assert set(saved.hold_ids) == expected_ids
    assert "hold-jug" not in {hold["id"] for hold in _read_board(package_root)["holds"]}


def test_save_rejects_non_contiguous_piece_indices(tmp_path: Path) -> None:
    library = _library(tmp_path)
    package_root = _write_finished_package(library, "fixture-board", "fixture.board")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"][1]["metadata"]["pieceIndex"] = 5

    with pytest.raises(BoardPackageError, match="indexed contiguously"):
        board_package.save_editor_document(library, "fixture-board", document)


def test_replace_rolls_back_the_live_package_when_installation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path)
    live = _write_finished_package(library, "fixture-board", "fixture.board")
    candidate_library = tmp_path / "candidates"
    candidate_library.mkdir()
    candidate = _write_finished_package(
        candidate_library,
        "fixture-board",
        "fixture.board",
        name="Edited Fixture Board",
    )
    before = _package_snapshot(live)
    real_replace = os.replace
    failed = False

    def fail_candidate_install(source, destination):
        nonlocal failed
        source_path = Path(source)
        destination_path = Path(destination)
        if (
            not failed
            and destination_path == live
            and source_path.parent.name.startswith(".workbench-save-")
        ):
            failed = True
            raise OSError("injected package installation failure")
        return real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", fail_candidate_install)

    with pytest.raises(BoardPackageError, match="could not save board package"):
        board_package.replace_package(library, "fixture-board", candidate)

    assert failed
    assert _package_snapshot(live) == before
    assert not (library / ".workbench-recovery").exists()
    assert not (library / "catalog.json").exists()


def test_replace_keeps_the_backup_inside_a_library_mount_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path)
    live = _write_finished_package(library, "fixture-board", "fixture.board")
    candidate_library = tmp_path / "candidates"
    candidate_library.mkdir()
    candidate = _write_finished_package(
        candidate_library,
        "fixture-board",
        "fixture.board",
        name="Edited Fixture Board",
    )
    real_replace = os.replace
    backup_destinations: list[Path] = []

    def reject_cross_mount_replace(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        source_is_below_library = source_path == library or library in source_path.parents
        destination_is_below_library = (
            destination_path == library or library in destination_path.parents
        )
        if source_path == live:
            backup_destinations.append(destination_path)
        if source_is_below_library != destination_is_below_library:
            raise OSError(errno.EXDEV, "injected cross-device package replacement")
        return real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", reject_cross_mount_replace)

    board_package.replace_package(library, "fixture-board", candidate)

    assert len(backup_destinations) == 1
    assert backup_destinations[0].parent == library / ".workbench-recovery"
    assert board_package.open_package(library, "fixture.board").board["name"] == (
        "Edited Fixture Board"
    )
    assert not (library / ".workbench-recovery").exists()


def test_replace_preserves_the_live_backup_when_install_and_restore_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path)
    live = _write_finished_package(library, "fixture-board", "fixture.board")
    candidate_library = tmp_path / "candidates"
    candidate_library.mkdir()
    candidate = _write_finished_package(
        candidate_library,
        "fixture-board",
        "fixture.board",
        name="Edited Fixture Board",
    )
    before = _package_snapshot(live)
    real_replace = os.replace
    failures: list[str] = []

    def fail_install_and_restore(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if (
            destination_path == live
            and source_path.name == "fixture-board"
            and source_path.parent.name.startswith(".workbench-save-")
        ):
            failures.append("install")
            raise OSError("injected package installation failure")
        if (
            destination_path == live
            and source_path.parent == library / ".workbench-recovery"
            and source_path.name.startswith("fixture-board-previous-")
        ):
            failures.append("restore")
            raise OSError("injected package restoration failure")
        return real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", fail_install_and_restore)

    with pytest.raises(BoardPackageError, match="could not restore"):
        board_package.replace_package(library, "fixture-board", candidate)

    recovery = library / ".workbench-recovery"
    backups = sorted(recovery.glob("fixture-board-previous-*"))
    assert failures == ["install", "restore"]
    assert not live.exists()
    assert len(backups) == 1
    assert _package_snapshot(backups[0]) == before
    assert board_package.discover_packages(library) == ()
    assert not any(path.name.startswith(".workbench-save-") for path in library.iterdir())


def test_replace_commits_new_package_when_backup_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path)
    live = _write_finished_package(library, "fixture-board", "fixture.board")
    candidate_library = tmp_path / "candidates"
    candidate_library.mkdir()
    candidate = _write_finished_package(
        candidate_library,
        "fixture-board",
        "fixture.board",
        name="Edited Fixture Board",
    )
    before = _package_snapshot(live)
    real_rmtree = shutil.rmtree
    cleanup_failures: list[Path] = []
    recovery = library / ".workbench-recovery"

    def fail_backup_cleanup(path, *args, **kwargs):
        cleanup_path = Path(path)
        if cleanup_path.parent == recovery and cleanup_path.name.startswith(
            "fixture-board-previous-"
        ):
            cleanup_failures.append(cleanup_path)
            raise OSError("injected backup cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(board_package.shutil, "rmtree", fail_backup_cleanup)

    board_package.replace_package(library, "fixture-board", candidate)
    first_commit = _package_snapshot(live)
    _mutate_board(
        candidate,
        lambda board: board.update(name="Edited Fixture Board Again"),
    )
    board_package.replace_package(library, "fixture-board", candidate)

    backups = sorted(recovery.glob("fixture-board-previous-*"))
    assert set(cleanup_failures) == set(backups)
    assert board_package.open_package(library, "fixture.board").board["name"] == (
        "Edited Fixture Board Again"
    )
    assert len(backups) == 2
    assert len({backup.name for backup in backups}) == 2
    assert {_package_snapshot(backup)["board.json"] for backup in backups} == {
        before["board.json"],
        first_commit["board.json"],
    }
    assert [package.board_id for package in board_package.discover_packages(library)] == [
        "fixture.board"
    ]
    assert not list(library.parent.glob(".Hangboards.workbench-previous-*"))


def test_staging_ignores_primary_only_drafts_when_staging_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    library = repository / "Hangboards"
    library.mkdir(parents=True)
    finished = _write_finished_package(library, "finished-board", "finished.board")
    _mutate_board(finished, _replace_holds_with_supported_kinds)
    _write_draft(library, "draft-board")
    pipeline_module = (
        repository / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer"
    )
    pipeline_module.mkdir(parents=True)
    for filename in ["board_catalog.py", "board_artwork.py"]:
        shutil.copyfile(PIPELINE_MODULE_ROOT / filename, pipeline_module / filename)

    stage_module = _load_stage_module("stage_board_packages_test")

    build_root = tmp_path / "build"
    destination = build_root / "Resources" / "Hangboards"
    monkeypatch.setenv("TARGET_BUILD_DIR", str(build_root))
    monkeypatch.setenv("UNLOCALIZED_RESOURCES_FOLDER_PATH", "Resources")

    staged = stage_module.stage_board_packages(repository, destination)

    assert staged == (destination / "finished-board",)
    assert (destination / "finished-board").is_dir()
    assert (destination / "draft-board").is_dir() is False


def test_staging_commits_new_destination_when_backup_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    library = repository / "Hangboards"
    library.mkdir(parents=True)
    _write_finished_package(library, "finished-board", "finished.board")
    pipeline_module = (
        repository / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer"
    )
    pipeline_module.mkdir(parents=True)
    for filename in ["board_catalog.py", "board_artwork.py"]:
        shutil.copyfile(PIPELINE_MODULE_ROOT / filename, pipeline_module / filename)

    stage_module = _load_stage_module("stage_board_packages_cleanup_test")

    build_root = tmp_path / "build"
    destination = build_root / "Resources" / "Hangboards"
    destination.mkdir(parents=True)
    (destination / "previous.txt").write_text("recoverable", encoding="utf-8")
    monkeypatch.setenv("TARGET_BUILD_DIR", str(build_root))
    monkeypatch.setenv("UNLOCALIZED_RESOURCES_FOLDER_PATH", "Resources")
    real_rmtree = shutil.rmtree
    cleanup_failures: list[Path] = []

    def fail_backup_cleanup(path, *args, **kwargs):
        cleanup_path = Path(path)
        if cleanup_path.name.startswith(".Hangboards.previous-"):
            cleanup_failures.append(cleanup_path)
            raise OSError("injected staged backup cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(stage_module.shutil, "rmtree", fail_backup_cleanup)

    staged = stage_module.stage_board_packages(repository, destination)

    backups = sorted(destination.parent.glob(".Hangboards.previous-*"))
    assert staged == (destination / "finished-board",)
    assert cleanup_failures == backups
    assert len(backups) == 1
    assert (backups[0] / "previous.txt").read_text(encoding="utf-8") == "recoverable"
    assert [package.board_id for package in board_package.discover_packages(destination)] == [
        "finished.board"
    ]
    assert not any(
        path.name.startswith(".Hangboards.previous-") for path in destination.iterdir()
    )
