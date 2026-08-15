from __future__ import annotations

import json
import shutil
import sys
import threading
import time
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WORKBENCH_ROOT.parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_geometry import (  # noqa: E402
    NormalizedFrame,
    display_path_for_shape,
    normalized_frame_for_path,
)
from board_package import (  # noqa: E402
    BoardPackageError,
    discover_packages,
    editor_document,
    load_board_package,
    primary_image_path,
    replace_package,
    save_editor_document,
)


SLUG = "metolius-wood-grips-compact-ii"
_THREAD_SYNC_TIMEOUT_SECONDS = 30


def _wait_for_thread_event(
    event: threading.Event,
    description: str,
    worker_errors: list[BaseException] | None = None,
) -> None:
    """Wait for a coordinated thread hand-off and surface worker failures."""
    deadline = time.monotonic() + _THREAD_SYNC_TIMEOUT_SECONDS
    remaining = deadline - time.monotonic()
    if event.wait(timeout=max(remaining, 0)):
        return

    errors = ""
    if worker_errors:
        errors = f" Worker errors: {worker_errors!r}"
    pytest.fail(f"Timed out waiting for {description}.{errors}")


def _join_thread(thread: threading.Thread, description: str) -> None:
    thread.join(timeout=_THREAD_SYNC_TIMEOUT_SECONDS)
    assert not thread.is_alive(), f"Timed out waiting for {description} to finish"


def _copy_library(tmp_path: Path) -> Path:
    library = tmp_path / "Hangboards"
    shutil.copytree(
        REPOSITORY_ROOT / "Hangboards",
        library,
        ignore=shutil.ignore_patterns(".workbench.lock"),
    )
    return library


def _candidate_with_id(tmp_path: Path, library: Path, slug: str, board_id: str) -> Path:
    candidate = tmp_path / slug
    shutil.copytree(library / SLUG, candidate)
    for name in ("board.json", "artwork.json", "evidence.json", "semantics.json"):
        path = candidate / name
        document = json.loads(path.read_text(encoding="utf-8"))
        if name == "board.json":
            document["id"] = board_id
        else:
            document["boardID"] = board_id
        path.write_text(json.dumps(document), encoding="utf-8")
    return candidate


def test_canonical_fixture_uses_frames_derived_from_each_artwork_outline() -> None:
    package = load_board_package(REPOSITORY_ROOT / "Hangboards" / SLUG)

    assert primary_image_path(package).name == "primary.png"
    document = editor_document(package)
    assert document["canvas"]["width"] > 0
    assert {region["key"] for region in document["regions"]} == {
        hold["id"] for hold in package.board["holds"]
    }
    assert all(region["displayPath"].endswith(" Z") for region in document["regions"])
    pieces = {piece["holdID"]: piece for piece in package.artwork["holdPieces"]}
    width, height = document["canvas"]["width"], document["canvas"]["height"]
    for hold in package.board["holds"]:
        outline = display_path_for_shape(
            pieces[hold["id"]]["frame"],
            pieces[hold["id"]]["shape"],
            width,
            height,
            label=hold["id"],
        )
        expected = normalized_frame_for_path(outline, width, height)
        actual = NormalizedFrame.from_json(hold["frame"])
        assert (actual.x, actual.y, actual.width, actual.height) == pytest.approx(
            (expected.x, expected.y, expected.width, expected.height),
            abs=0.0000005,
        )


def test_discovers_registered_canonical_packages() -> None:
    assert discover_packages(REPOSITORY_ROOT / "Hangboards") == (
        board_package.CatalogEntry("metolius.wood-grips-compact-ii", SLUG),
    )


@pytest.mark.parametrize("reader", ("discovery", "registered-open"))
def test_public_readers_wait_for_package_replacement_to_finish(
    reader: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _copy_library(tmp_path)
    candidate = _candidate_with_id(tmp_path, library, SLUG, "metolius.wood-grips-compact-ii")
    board_path = candidate / "board.json"
    candidate_board = json.loads(board_path.read_text(encoding="utf-8"))
    candidate_board["name"] = "Replacement board"
    board_path.write_text(json.dumps(candidate_board), encoding="utf-8")
    package_moved = threading.Event()
    release_replacement = threading.Event()
    reader_finished = threading.Event()
    reader_errors: list[BaseException] = []
    writer_errors: list[BaseException] = []
    real_replace = board_package.os.replace

    def pause_after_package_move(source: str | Path, destination: str | Path) -> None:
        real_replace(source, destination)
        if Path(destination) == library / f".{SLUG}.workbench-backup":
            package_moved.set()
            _wait_for_thread_event(release_replacement, "replacement release")

    monkeypatch.setattr(board_package.os, "replace", pause_after_package_move)

    def replace() -> None:
        try:
            replace_package(library, SLUG, candidate)
        except BaseException as error:  # pragma: no cover - surfaced below
            writer_errors.append(error)

    writer = threading.Thread(target=replace, name="package-replacement")

    def discover() -> None:
        try:
            if reader == "discovery":
                discover_packages(library)
            else:
                board_package.open_registered_package(
                    library, "metolius.wood-grips-compact-ii"
                )
        except BaseException as error:  # pragma: no cover - surfaced below
            reader_errors.append(error)
        finally:
            reader_finished.set()

    reader_thread = threading.Thread(target=discover)
    writer.start()
    _wait_for_thread_event(package_moved, "package replacement to begin", writer_errors)
    reader_thread.start()
    assert not reader_finished.wait(timeout=0.1)
    release_replacement.set()
    _join_thread(writer, "package replacement")
    _join_thread(reader_thread, "package reader")

    assert not writer_errors
    assert not reader_errors
    assert reader_finished.is_set()


def test_rejects_a_library_lock_symlink_without_following_its_target(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    outside_lock = tmp_path / "outside.lock"
    outside_lock.write_text("outside lock content", encoding="utf-8")
    (library / ".workbench.lock").symlink_to(outside_lock)

    with pytest.raises(BoardPackageError, match="workbench lock must be a regular file"):
        discover_packages(library)

    assert outside_lock.read_text(encoding="utf-8") == "outside lock content"


@pytest.mark.parametrize(
    ("evidence_map", "key"),
    (
        ("fieldEvidence", "manufacturer"),
        ("holdEvidence", "jug-left.kind"),
        ("semanticEvidence", "outer-jugs"),
        ("artworkEvidence", "holdPieces.jug-left-top-cap"),
    ),
)
def test_rejects_external_generation_as_canonical_evidence(
    evidence_map: str, key: str, tmp_path: Path
) -> None:
    library = _copy_library(tmp_path)
    evidence_path = library / SLUG / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence[evidence_map][key]["method"] = "external-generative-adaptation"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="external-generative-adaptation is not permitted"):
        load_board_package(library / SLUG)


def test_rejects_external_generation_for_an_original_source_asset(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    package = library / SLUG
    evidence_path = package / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["assetEvidence"]["assets/WoodGripsCompactII.jpg"] = {
        "sourceIDs": ["product-page"],
        "method": "external-generative-adaptation",
    }
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="external-generative-adaptation is not permitted"):
        load_board_package(package)


def test_rejects_duplicate_board_hold_ids_and_mismatched_artwork_ids(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    package_root = library / SLUG
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["holds"][1]["id"] = board["holds"][0]["id"]
    board_path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="duplicate hold ID"):
        load_board_package(package_root)

    board["holds"][1]["id"] = "restored-hold"
    board_path.write_text(json.dumps(board), encoding="utf-8")
    semantics_path = package_root / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    for semantic in semantics["semanticHolds"].values():
        semantic["holdIDs"] = [
            "restored-hold" if hold_id == "sloper-flat-left" else hold_id
            for hold_id in semantic["holdIDs"]
        ]
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")
    with pytest.raises(BoardPackageError, match="hold IDs must exactly match"):
        load_board_package(package_root)


def test_rejects_an_artwork_layer_with_an_unparseable_shape(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    artwork_path = library / SLUG / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    artwork["layers"][0]["shape"] = {"not": "a-shape"}
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="layer top-plane has invalid geometry"):
        load_board_package(library / SLUG)


def test_rejects_a_board_hold_frame_that_disagrees_with_its_artwork_outline(
    tmp_path: Path,
) -> None:
    library = _copy_library(tmp_path)
    board_path = library / SLUG / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["holds"][0]["frame"]["x"] = 0.001
    board_path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(
        BoardPackageError,
        match="board.json.holds\\[0\\].frame must match its derived artwork outline",
    ):
        load_board_package(library / SLUG)


@pytest.mark.parametrize("sidecar", ("board.json", "artwork.json", "evidence.json", "semantics.json"))
def test_rejects_a_boolean_schema_version(sidecar: str, tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    sidecar_path = library / SLUG / sidecar
    document = json.loads(sidecar_path.read_text(encoding="utf-8"))
    document["schemaVersion"] = True
    sidecar_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="schemaVersion must be 1"):
        load_board_package(library / SLUG)


def test_rejects_a_boolean_catalog_schema_version(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    catalog_path = library / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["schemaVersion"] = True
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="catalog.json.schemaVersion must be 1"):
        discover_packages(library)


def test_rejects_an_unknown_catalog_field(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    catalog_path = library / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["unexpected"] = "ignored configuration must not be accepted"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="catalog.json has unknown keys: \\['unexpected'\\]"):
        discover_packages(library)


def test_rejects_a_boolean_editor_document_schema_version(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    document = editor_document(load_board_package(library / SLUG))
    document["schemaVersion"] = True

    with pytest.raises(BoardPackageError, match="editor document.schemaVersion must be 1"):
        save_editor_document(library, SLUG, document)


def test_rejects_evidence_source_ids_without_a_method(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    evidence_path = library / SLUG / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["fieldEvidence"]["manufacturer"] = ["product-page"]
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="evidence.json.fieldEvidence.manufacturer must be an object"):
        load_board_package(library / SLUG)


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda value: value.__setitem__("palette", "inventedPalette"),
            "artwork.json.palette must be one of",
        ),
        (
            lambda value: value["layers"][0].__setitem__("role", "inventedRole"),
            "artwork.json.layers\\[0\\].role must be one of",
        ),
    ),
)
def test_rejects_noncanonical_artwork_metadata(
    mutate: object, message: str, tmp_path: Path
) -> None:
    library = _copy_library(tmp_path)
    artwork_path = library / SLUG / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    mutate(artwork)
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")

    with pytest.raises(BoardPackageError, match=message):
        load_board_package(library / SLUG)


def test_rejects_an_artwork_hold_piece_with_an_extra_field(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    artwork_path = library / SLUG / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    artwork["holdPieces"][0]["extra"] = "unexpected"
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="artwork.json.holdPieces\\[0\\] has unknown keys"):
        load_board_package(library / SLUG)


def test_rejects_an_artwork_hold_piece_without_a_treatment(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    artwork_path = library / SLUG / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    del artwork["holdPieces"][0]["treatment"]
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="artwork.json.holdPieces\\[0\\] has missing keys"):
        load_board_package(library / SLUG)


def test_rejects_an_artwork_hold_piece_with_an_invalid_treatment(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    artwork_path = library / SLUG / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    artwork["holdPieces"][0]["treatment"] = {
        "type": "shelf",
        "rimInsetFraction": 0.51,
    }
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")

    with pytest.raises(
        BoardPackageError,
        match="artwork.json.holdPieces\\[0\\].treatment.rimInsetFraction must be in 0...0.5",
    ):
        load_board_package(library / SLUG)


def test_replaces_a_valid_candidate_and_leaves_live_files_untouched_when_validation_fails(
    tmp_path: Path,
) -> None:
    library = _copy_library(tmp_path)
    live = library / SLUG
    candidate = tmp_path / "candidate"
    shutil.copytree(live, candidate)
    board_path = candidate / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["name"] = "Edited board name"
    board_path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")

    replace_package(library, SLUG, candidate)

    assert json.loads((live / "board.json").read_text(encoding="utf-8"))["name"] == "Edited board name"
    catalog_before = (library / "catalog.json").read_bytes()
    package_before = (live / "board.json").read_bytes()
    invalid = tmp_path / "invalid"
    shutil.copytree(live, invalid)
    invalid_artwork = json.loads((invalid / "artwork.json").read_text(encoding="utf-8"))
    duplicate_piece = dict(invalid_artwork["holdPieces"][0])
    duplicate_piece["id"] = "duplicate-piece"
    invalid_artwork["holdPieces"].append(duplicate_piece)
    (invalid / "artwork.json").write_text(json.dumps(invalid_artwork), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="duplicate hold ID"):
        replace_package(library, SLUG, invalid)

    assert (library / "catalog.json").read_bytes() == catalog_before
    assert (live / "board.json").read_bytes() == package_before


def test_saves_an_edited_contour_with_its_derived_board_frame(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    package = load_board_package(library / SLUG)
    document = editor_document(package)
    region = document["regions"][0]
    region["displayPath"] = "M 10 20 L 50 20 L 50 60 L 10 60 Z"

    saved = save_editor_document(library, SLUG, document)

    edited_hold = next(hold for hold in saved.board["holds"] if hold["id"] == region["key"])
    assert edited_hold["frame"] == {"x": 10 / document["canvas"]["width"], "y": 20 / document["canvas"]["height"], "width": 40 / document["canvas"]["width"], "height": 40 / document["canvas"]["height"]}
    reloaded = editor_document(saved)
    assert reloaded["regions"][0]["displayPath"] == region["displayPath"]


def test_restores_the_prior_package_and_catalog_when_replacement_io_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _copy_library(tmp_path)
    live = library / SLUG
    candidate = tmp_path / "candidate"
    shutil.copytree(live, candidate)
    package_before = (live / "board.json").read_bytes()
    catalog_before = (library / "catalog.json").read_bytes()
    real_replace = board_package.os.replace

    def fail_staged_package_replace(source: str | Path, destination: str | Path) -> None:
        if Path(source).parent.name.startswith(".workbench-save-") and Path(source).name == SLUG:
            raise OSError("injected replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", fail_staged_package_replace)

    with pytest.raises(BoardPackageError, match="could not save"):
        replace_package(library, SLUG, candidate)

    assert (live / "board.json").read_bytes() == package_before
    assert (library / "catalog.json").read_bytes() == catalog_before


def test_concurrent_new_packages_preserve_both_catalog_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _copy_library(tmp_path)
    first = _candidate_with_id(tmp_path, library, "first-board", "example.first-board")
    second = _candidate_with_id(tmp_path, library, "second-board", "example.second-board")
    first_ready = threading.Event()
    release_first = threading.Event()
    second_catalog_read = threading.Event()
    real_transaction = board_package._replace_transaction
    real_load_catalog = board_package._load_catalog

    def pause_first_transaction(*args: object) -> None:
        if not first_ready.is_set():
            first_ready.set()
            _wait_for_thread_event(release_first, "first package release")
        real_transaction(*args)

    monkeypatch.setattr(board_package, "_replace_transaction", pause_first_transaction)

    def record_catalog_read(path: Path) -> tuple[board_package.CatalogEntry, ...]:
        if threading.current_thread().name == "second-save":
            second_catalog_read.set()
        return real_load_catalog(path)

    monkeypatch.setattr(board_package, "_load_catalog", record_catalog_read)
    errors: list[BaseException] = []

    def save(slug: str, candidate: Path) -> None:
        try:
            replace_package(library, slug, candidate)
        except BaseException as error:  # pragma: no cover - surfaced below
            errors.append(error)

    first_thread = threading.Thread(target=save, args=("first-board", first), name="first-save")
    second_thread = threading.Thread(target=save, args=("second-board", second), name="second-save")
    first_thread.start()
    _wait_for_thread_event(first_ready, "first package replacement to begin", errors)
    second_thread.start()
    assert not second_catalog_read.wait(timeout=0.1)
    release_first.set()
    _join_thread(first_thread, "first package replacement")
    _join_thread(second_thread, "second package replacement")

    assert not errors
    assert {entry.board_id for entry in discover_packages(library)} == {
        "metolius.wood-grips-compact-ii",
        "example.first-board",
        "example.second-board",
    }


def test_removes_a_new_package_when_catalog_installation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _copy_library(tmp_path)
    candidate = _candidate_with_id(tmp_path, library, "new-board", "example.new-board")
    catalog_before = (library / "catalog.json").read_bytes()
    real_replace = board_package.os.replace

    def fail_catalog_install(source: str | Path, destination: str | Path) -> None:
        if Path(source).parent.name.startswith(".workbench-save-") and Path(source).name == "catalog.json":
            raise OSError("injected catalog install failure")
        real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", fail_catalog_install)

    with pytest.raises(BoardPackageError, match="could not save"):
        replace_package(library, "new-board", candidate)

    assert not (library / "new-board").exists()
    assert (library / "catalog.json").read_bytes() == catalog_before


@pytest.mark.parametrize(
    ("path", "mutate", "message"),
    [
        ("board.json", lambda value: value.pop("manufacturer"), "missing keys"),
        ("board.json", lambda value: value["holds"][0].__setitem__("kind", "rail"), "kind must be one of"),
        ("semantics.json", lambda value: value["semanticHolds"]["outer-jugs"].__setitem__("holdIDs", []), "must be non-empty"),
        ("evidence.json", lambda value: value["sources"][0].__setitem__("url", "http://example.com"), "absolute HTTPS URL"),
    ],
)
def test_rejects_malformed_canonical_metadata_and_sidecars(
    tmp_path: Path, path: str, mutate: object, message: str
) -> None:
    library = _copy_library(tmp_path)
    package = library / SLUG
    sidecar = package / path
    document = json.loads(sidecar.read_text(encoding="utf-8"))
    mutate(document)
    sidecar.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(BoardPackageError, match=message):
        load_board_package(package)
