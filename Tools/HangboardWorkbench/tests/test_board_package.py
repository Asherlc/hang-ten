from __future__ import annotations

import base64
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

TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_ROOT))
import conftest as shared_fixtures  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PACKAGE = (
    REPOSITORY_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii"
)
PRIMARY_IMAGE = CANONICAL_PACKAGE / "assets" / "primary.png"
VALIDATION_FIXTURES = json.loads(
    (
        REPOSITORY_ROOT
        / "HangTenTests"
        / "Fixtures"
        / "BoardPackageValidationFixtures.json"
    ).read_text(encoding="utf-8")
)
SUPPORTED_HOLD_KINDS = ("jug", "edge", "pocket", "pinch", "sloper")
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_package import BoardPackageError  # noqa: E402


def _board_document(
    board_id: str,
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "id": board_id,
        "manufacturer": manufacturer,
        "name": name,
        "subtitle": "A physical fixture board.",
        "productURL": f"https://example.com/{board_id}",
        "dimensions": "20 × 10 cm",
        "aspectRatio": 1774 / 457,
        "presentation": {"assetPath": "assets/primary.png"},
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "geometry": [
                    {
                        "frame": {"x": 0.05, "y": 0.2, "width": 0.1, "height": 0.3},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
                    },
                    {
                        "frame": {"x": 0.35, "y": 0.1, "width": 0.1, "height": 0.2},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
                        "treatment": {"type": "surface"},
                    },
                ],
            }
        ],
    }


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
        _board_document(board_id, manufacturer=manufacturer, name=name),
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


def test_rejects_shared_out_of_bounds_normalized_frames(tmp_path: Path) -> None:
    for fixture in VALIDATION_FIXTURES["outOfBoundsFrames"]:
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
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    package = board_package.load_board_package(
        _write_finished_package(library, "fixture-board", "fixture.board")
    )

    document = board_package.editor_document(package)

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
    assert not (library / "catalog.json").exists()


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
        if destination_path == live and (
            source_path.name.startswith(".workbench-previous-")
            or source_path.name.startswith(".Hangboards.workbench-previous-")
        ):
            failures.append("restore")
            raise OSError("injected package restoration failure")
        return real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", fail_install_and_restore)

    with pytest.raises(BoardPackageError, match="could not restore"):
        board_package.replace_package(library, "fixture-board", candidate)

    backups = sorted(library.parent.glob(".Hangboards.workbench-previous-*"))
    assert failures == ["install", "restore"]
    assert not live.exists()
    assert len(backups) == 1
    assert _package_snapshot(backups[0]) == before
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

    def fail_backup_cleanup(path, *args, **kwargs):
        cleanup_path = Path(path)
        if (
            cleanup_path.name.startswith(".workbench-previous-")
            or cleanup_path.name.startswith(".Hangboards.workbench-previous-")
        ):
            cleanup_failures.append(cleanup_path)
            raise OSError("injected backup cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(board_package.shutil, "rmtree", fail_backup_cleanup)

    board_package.replace_package(library, "fixture-board", candidate)

    backups = sorted(library.parent.glob(".Hangboards.workbench-previous-*"))
    assert cleanup_failures == backups
    assert board_package.open_package(library, "fixture.board").board["name"] == (
        "Edited Fixture Board"
    )
    assert len(backups) == 1
    assert _package_snapshot(backups[0]) == before
    assert not any(
        path.name.startswith(".workbench-previous-") for path in library.iterdir()
    )


def test_staging_copies_only_complete_direct_children_without_a_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    library = repository / "Hangboards"
    library.mkdir(parents=True)
    finished = _write_finished_package(library, "finished-board", "finished.board")
    _mutate_board(finished, _replace_holds_with_supported_kinds)
    _write_draft(library, "draft-board")
    workbench = repository / "Tools" / "HangboardWorkbench"
    workbench.mkdir(parents=True)
    for filename in ["board_package.py", "board_geometry.py"]:
        shutil.copyfile(WORKBENCH_ROOT / filename, workbench / filename)

    stage_path = REPOSITORY_ROOT / "scripts" / "stage-board-packages.py"
    spec = importlib.util.spec_from_file_location("stage_board_packages_test", stage_path)
    assert spec is not None and spec.loader is not None
    stage_module = importlib.util.module_from_spec(spec)
    previous_bytecode_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(stage_module)
    finally:
        sys.dont_write_bytecode = previous_bytecode_setting

    build_root = tmp_path / "build"
    destination = build_root / "Resources" / "Hangboards"
    monkeypatch.setenv("TARGET_BUILD_DIR", str(build_root))
    monkeypatch.setenv("UNLOCALIZED_RESOURCES_FOLDER_PATH", "Resources")

    staged = stage_module.stage_board_packages(repository, destination)

    assert staged == (destination / "finished-board",)
    assert sorted(
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
    ) == [
        "finished-board",
        "finished-board/assets",
        "finished-board/assets/primary.png",
        "finished-board/board.json",
    ]
    assert not (destination / "catalog.json").exists()
    staged_board = json.loads(
        (destination / "finished-board" / "board.json").read_text(encoding="utf-8")
    )
    assert [hold["kind"] for hold in staged_board["holds"]] == list(
        SUPPORTED_HOLD_KINDS
    )


def test_staging_commits_new_destination_when_backup_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    library = repository / "Hangboards"
    library.mkdir(parents=True)
    _write_finished_package(library, "finished-board", "finished.board")
    workbench = repository / "Tools" / "HangboardWorkbench"
    workbench.mkdir(parents=True)
    for filename in ["board_package.py", "board_geometry.py"]:
        shutil.copyfile(WORKBENCH_ROOT / filename, workbench / filename)

    stage_path = REPOSITORY_ROOT / "scripts" / "stage-board-packages.py"
    spec = importlib.util.spec_from_file_location(
        "stage_board_packages_cleanup_test",
        stage_path,
    )
    assert spec is not None and spec.loader is not None
    stage_module = importlib.util.module_from_spec(spec)
    previous_bytecode_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(stage_module)
    finally:
        sys.dont_write_bytecode = previous_bytecode_setting

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
