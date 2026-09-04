from __future__ import annotations

import hashlib
import json
import re
import struct
import zlib
from pathlib import Path

import pytest

from conftest import (
    ALTERNATE_PRIMARY_PNG_BYTES,
    OPAQUE_PRIMARY_PNG_BYTES,
    PRIMARY_PNG_BYTES,
    TRANSPARENT_PRIMARY_PNG_BYTES,
    board_document,
    load_board_catalog_module,
    multi_presentation_board_document,
    write_board_package,
    write_multi_presentation_board_package,
    write_primary_only_draft,
)
from _board_package_helpers import board_positions_document

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_port_has_only_approved_front_and_back_physical_faces() -> None:
    module = load_board_catalog_module()
    repository_root = Path(__file__).resolve().parents[3]
    package_root = repository_root / "Hangboards" / "frictitious-port-a-board"
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    presentations = {item["id"]: item for item in document["presentations"]}

    assert [(item["id"], item["assetPath"]) for item in document["presentations"]] == [
        ("primary", "assets/primary.png"),
        ("front-inverted", "assets/primary.png"),
        ("back", "assets/back.png"),
    ]
    assert presentations["back"]["assetPath"] == "assets/back.png"
    assert "back-inverted" not in presentations
    assert "side" not in presentations
    assert not (package_root / "assets" / "back-inverted.png").exists()
    assert not (package_root / "assets" / "side.png").exists()
    assert {hold["id"] for hold in document["holds"]} == {
        "edge-30",
        "pocket-30-two-finger-mono",
        "edge-25",
        "edge-20",
        "edge-15",
        "edge-12",
        "edge-10",
        "edge-8",
        "jug-outer-rim",
    }
    assert hashlib.sha256((package_root / "assets" / "back.png").read_bytes()).hexdigest() == (
        "39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e"
    )
    canonical_holds = json.dumps(
        document["holds"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    assert hashlib.sha256(canonical_holds).hexdigest() == (
        "f8ca1ab25f3b1fd70f4cf756bd6b4a4ac8b5478e6da4048e1ed005ba835074d8"
    )

    package = module.load_board_package(package_root)
    parsed_presentations = {item.id: item for item in package.board.presentations}
    assert parsed_presentations["front-inverted"].rotation_degrees == 180
    assert parsed_presentations["front-inverted"].is_inverted is False
    assert parsed_presentations["back"].source_presentation_id is None
    assert "back-inverted" not in parsed_presentations


def _png_chunk(chunk_type: bytes, body: bytes = b"") -> bytes:
    return (
        struct.pack(">I", len(body))
        + chunk_type
        + body
        + struct.pack(">I", zlib.crc32(chunk_type + body) & 0xFFFFFFFF)
    )


def _png_without_idat() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return _PNG_SIGNATURE + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND")


def test_board_schema_loads_positions_and_directed_transitions() -> None:
    module = load_board_catalog_module()
    document = board_positions_document(board_document())

    board = module._load_board(document)

    assert board.positions == (
        module.BoardPosition("front", "primary"),
        module.BoardPosition("flipped", "front-inverted"),
    )
    assert board.position_transitions == (
        module.BoardPositionTransition(
            "front", "flipped", module.BoardPositionTransitionKind.SEAMLESS
        ),
    )
    assert [position.id for position in board.positions] == ["front", "flipped"]
    assert board.hold_ids_for_position("flipped") == board.hold_ids_for_position("front")
    assert board.transition_kind("front", "front") == "same"
    assert board.transition_kind("front", "flipped") == "seamless"
    assert board.transition_kind("flipped", "front") == "setupRequired"


@pytest.mark.parametrize("field", ["positions", "positionTransitions"])
def test_board_schema_rejects_explicit_null_position_fields(field: str) -> None:
    module = load_board_catalog_module()
    document = (
        board_document()
        if field == "positions"
        else board_positions_document(board_document())
    )
    document[field] = None

    with pytest.raises(ValueError, match=rf"board\.json\.{field} must be"):
        module._load_board(document)


@pytest.mark.parametrize(
    ("from_id", "to_id"),
    [
        ("missing", "front"),
        ("front", "missing"),
        ("missing", "missing"),
    ],
)
def test_board_transition_kind_rejects_unknown_position_endpoints(
    from_id: str, to_id: str
) -> None:
    module = load_board_catalog_module()
    board = module._load_board(board_positions_document(board_document()))

    with pytest.raises(ValueError, match="unknown position id: missing"):
        board.transition_kind(from_id, to_id)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("setupRequired", "setupRequired"),
        ("unsupported", "unsupported"),
    ],
)
def test_board_schema_loads_all_explicit_transition_kinds(
    kind: str, expected: str
) -> None:
    module = load_board_catalog_module()
    document = board_positions_document(board_document())
    document["positionTransitions"][0]["kind"] = kind

    board = module._load_board(document)

    assert board.transition_kind("front", "flipped") == expected


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["positions"].append(
                {"id": "front", "presentationID": "primary"}
            ),
            "duplicate position id",
        ),
        (
            lambda document: document["positions"][0].__setitem__(
                "presentationID", "missing"
            ),
            "unknown presentationID",
        ),
        (
            lambda document: document["positionTransitions"].append(
                {
                    "fromPositionID": "front",
                    "toPositionID": "flipped",
                    "kind": "seamless",
                }
            ),
            "duplicate position transition",
        ),
        (
            lambda document: document["positionTransitions"][0].__setitem__(
                "fromPositionID", "missing"
            ),
            "unknown fromPositionID",
        ),
        (
            lambda document: document["positionTransitions"][0].__setitem__(
                "toPositionID", "missing"
            ),
            "unknown toPositionID",
        ),
        (
            lambda document: document["positionTransitions"][0].__setitem__(
                "toPositionID", "front"
            ),
            "must not be self-edge",
        ),
        (
            lambda document: document["positionTransitions"][0].__setitem__(
                "kind", "invented"
            ),
            "kind is unsupported",
        ),
        (
            lambda document: document["positions"][0].__setitem__(
                "unexpected", True
            ),
            r"board\.json\.positions\[0\] has unknown keys",
        ),
        (
            lambda document: document["positionTransitions"][0].__setitem__(
                "unexpected", True
            ),
            r"board\.json\.positionTransitions\[0\] has unknown keys",
        ),
    ],
)
def test_board_schema_rejects_invalid_positions_and_transitions(mutation, message: str) -> None:
    module = load_board_catalog_module()
    document = board_positions_document(board_document())
    mutation(document)

    with pytest.raises(ValueError, match=message):
        module._load_board(document)


def test_board_schema_rejects_position_without_canonical_presentation_holds() -> None:
    module = load_board_catalog_module()
    document = board_positions_document(board_document())
    document["presentations"].append(
        {
            "id": "unused",
            "name": "Unused",
            "assetPath": "assets/unused.png",
            "aspectRatio": 2,
            "default": False,
        }
    )
    document["positions"].append({"id": "unused", "presentationID": "unused"})

    with pytest.raises(ValueError, match="must own at least one hold"):
        module._load_board(document)


def test_board_schema_synthesizes_legacy_positions_in_presentation_order() -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()

    board = module._load_board(document)

    assert [(position.id, position.presentation_id) for position in board.positions] == [
        ("front", "front"),
        ("back", "back"),
    ]
    assert board.position_transitions == ()


def test_discovery_reads_direct_child_packages_without_a_catalog_and_sorts_them(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    write_board_package(
        tmp_path / "zeta-model",
        board_id="zeta.board",
        manufacturer="Zeta",
        name="Model",
    )
    write_board_package(
        tmp_path / "alpha-zulu",
        board_id="alpha.zulu",
        manufacturer="Alpha",
        name="Zulu",
    )
    write_board_package(
        tmp_path / "alpha-alpha-b",
        board_id="alpha.b",
        manufacturer="Alpha",
        name="Alpha",
    )
    write_board_package(
        tmp_path / "alpha-alpha-a",
        board_id="alpha.a",
        manufacturer="Alpha",
        name="Alpha",
    )
    draft = write_primary_only_draft(tmp_path / "draft-model")

    inventory = module.discover_board_packages(tmp_path)

    assert [package.board.id for package in inventory.packages] == [
        "alpha.a",
        "alpha.b",
        "alpha.zulu",
        "zeta.board",
    ]
    assert [package.root.name for package in inventory.packages] == [
        "alpha-alpha-a",
        "alpha-alpha-b",
        "alpha-zulu",
        "zeta-model",
    ]
    assert inventory.drafts == (draft.resolve(),)
    assert not (tmp_path / "catalog.json").exists()


def test_board_schema_accepts_fractional_fixed_millimeter_measurement() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["holds"][0]
    hold["sizeMillimeters"] = 7.5

    board = module._load_board(document)

    assert board.holds[0].size_millimeters == 7.5
    assert board.holds[0].depth_range_millimeters is None


def test_board_schema_rejects_hold_with_unknown_equipment_object_id() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["equipmentObjects"] = [{"id": "primary"}]
    document["holds"][0]["equipmentObjectID"] = "missing"

    with pytest.raises(ValueError, match="unknown equipment object"):
        module._load_board(document)


def test_board_schema_accepts_missing_hand_capacity_policy() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["equipmentObjects"] = [
        {"id": "primary", "missingHandCapacityPolicy": "unavailable"}
    ]

    board = module._load_board(document)

    assert board.equipment_objects == ("primary",)


def test_board_schema_rejects_unknown_missing_hand_capacity_policy() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["equipmentObjects"] = [
        {"id": "primary", "missingHandCapacityPolicy": "invented"}
    ]

    with pytest.raises(ValueError, match="missingHandCapacityPolicy"):
        module._load_board(document)


def test_board_schema_accepts_fractional_continuous_depth_range() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["holds"][0]
    hold["depthRangeMillimeters"] = {"lowerBound": 7.5, "upperBound": 12.5}

    board = module._load_board(document)

    assert board.holds[0].size_millimeters is None
    assert board.holds[0].depth_range_millimeters == module.MillimeterRange(7.5, 12.5)


def test_board_schema_accepts_reciprocal_gaston_pairs() -> None:
    module = load_board_catalog_module()
    document = board_document()
    template = document["holds"][0]
    left = {**template, "id": "gaston-left", "name": "Left gaston", "kind": "gaston", "pairedHoldID": "gaston-right"}
    right = {**template, "id": "gaston-right", "name": "Right gaston", "kind": "gaston", "pairedHoldID": "gaston-left"}
    document["holds"] = [left, right]

    board = module._load_board(document)

    assert [hold.kind for hold in board.holds] == ["gaston", "gaston"]
    assert [hold.paired_hold_id for hold in board.holds] == ["gaston-right", "gaston-left"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda holds: holds[0].__setitem__("kind", "gaston"),
        lambda holds: holds[0].update(kind="gaston", pairedHoldID="not a valid identifier"),
        lambda holds: holds[0].__setitem__("pairedHoldID", "gaston-right"),
        lambda holds: holds[0].update(kind="gaston", pairedHoldID="gaston-left"),
        lambda holds: holds[0].update(kind="gaston", pairedHoldID="missing"),
        lambda holds: holds[0].update(kind="gaston", pairedHoldID="gaston-right"),
        lambda holds: (
            holds[0].update(kind="gaston", pairedHoldID="gaston-right"),
            holds[1].update(kind="gaston", pairedHoldID="another-gaston"),
        ),
    ],
    ids=[
        "missing-pair",
        "invalid-pair-identifier",
        "pair-on-non-gaston",
        "self-pair",
        "unknown-target",
        "non-gaston-target",
        "non-reciprocal-target",
    ],
)
def test_board_schema_rejects_invalid_gaston_pair_metadata(mutate) -> None:
    module = load_board_catalog_module()
    document = board_document()
    template = document["holds"][0]
    document["holds"] = [
        {**template, "id": "gaston-left", "name": "Left gaston"},
        {**template, "id": "gaston-right", "name": "Right gaston"},
    ]
    mutate(document["holds"])

    with pytest.raises(ValueError):
        module._load_board(document)


@pytest.mark.parametrize(
    ("sloper", "expected"),
    [
        ({"type": "flat", "angleDegrees": 20}, ("flat", 20.0)),
        ({"type": "flat"}, ("flat", None)),
        ({"type": "round"}, ("round", None)),
    ],
)
def test_board_schema_exposes_strict_sloper_metadata(
    sloper: dict[str, object], expected: tuple[str, float | None]
) -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["holds"][0]
    hold["kind"] = "sloper"
    hold["sloper"] = sloper

    board = module._load_board(document)

    assert board.holds[0].sloper == module.SloperMetadata(*expected)


def test_board_schema_allows_sloper_without_subtype_metadata() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["holds"][0]["kind"] = "sloper"

    board = module._load_board(document)

    assert board.holds[0].sloper is None


@pytest.mark.parametrize(
    ("kind", "sloper", "path"),
    [
        ("jug", {"type": "round"}, "board.json.holds[0].sloper"),
        (
            "sloper",
            {"type": "round", "angleDegrees": 20},
            "board.json.holds[0].sloper",
        ),
        (
            "sloper",
            {"type": "flat", "angleDegrees": -1},
            "board.json.holds[0].sloper.angleDegrees",
        ),
        (
            "sloper",
            {"type": "flat", "angleDegrees": 91},
            "board.json.holds[0].sloper.angleDegrees",
        ),
        (
            "sloper",
            {"type": "flat", "angleDegrees": float("inf")},
            "board.json.holds[0].sloper.angleDegrees",
        ),
        ("sloper", {"type": "angled"}, "board.json.holds[0].sloper.type"),
    ],
)
def test_board_schema_rejects_invalid_strict_sloper_metadata(
    kind: str, sloper: dict[str, object] | None, path: str
) -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["holds"][0]
    hold["kind"] = kind
    if sloper is not None:
        hold["sloper"] = sloper

    with pytest.raises(ValueError, match=re.escape(path)):
        module._load_board(document)


def test_board_schema_rejects_hold_with_fixed_and_variable_depths() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["holds"][0]
    hold["sizeMillimeters"] = 7.5
    hold["depthRangeMillimeters"] = {"lowerBound": 7.5, "upperBound": 12.5}

    with pytest.raises(ValueError, match="must not specify both"):
        module._load_board(document)


def test_final_inventory_rejects_a_primary_only_draft(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    write_primary_only_draft(tmp_path / "draft-model")

    with pytest.raises(ValueError, match="missing board.json"):
        module.discover_board_packages(tmp_path, require_complete_inventory=True)


def test_discovery_accepts_an_opaque_primary_only_draft(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    draft = write_primary_only_draft(tmp_path / "draft-model")
    (draft / "assets" / "primary.png").write_bytes(OPAQUE_PRIMARY_PNG_BYTES)

    inventory = module.discover_board_packages(tmp_path)

    assert inventory.packages == ()
    assert inventory.drafts == (draft.resolve(),)


def test_discovery_rejects_duplicate_board_ids(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    write_board_package(tmp_path / "first-model", board_id="duplicate.board")
    write_board_package(tmp_path / "second-model", board_id="duplicate.board")

    with pytest.raises(ValueError, match="duplicate board id: duplicate.board"):
        module.discover_board_packages(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda root: (root / "assets" / "primary.png").unlink(), "primary.png"),
        (lambda root: (root / "semantics.json").write_text("{}"), "unknown package entry"),
        (
            lambda root: (root / "assets" / "extra.png").write_bytes(b"extra"),
            "undeclared presentation asset",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(b"not a png"),
            "must be a PNG image",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(
                PRIMARY_PNG_BYTES[:-1] + bytes([PRIMARY_PNG_BYTES[-1] ^ 0xFF])
            ),
            "corrupt chunk checksum",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(_png_without_idat()),
            "must contain image data",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(
                PRIMARY_PNG_BYTES + b"trailing"
            ),
            "trailing data after IEND",
        ),
    ],
)
def test_completed_package_requires_the_exact_finished_shape(
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    mutation(package)

    with pytest.raises(ValueError, match=message):
        module.discover_board_packages(tmp_path)


def test_completed_package_accepts_a_fully_opaque_primary_png(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    (package / "assets" / "primary.png").write_bytes(OPAQUE_PRIMARY_PNG_BYTES)

    inventory = module.discover_board_packages(tmp_path)

    assert [item.root.name for item in inventory.packages] == ["fixture-model"]


def test_completed_package_accepts_a_primary_png_with_actual_alpha_zero(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    (package / "assets" / "primary.png").write_bytes(TRANSPARENT_PRIMARY_PNG_BYTES)

    inventory = module.discover_board_packages(tmp_path)

    assert [item.root.name for item in inventory.packages] == ["fixture-model"]


def test_primary_png_decoder_uses_the_streaming_zlib_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_board_catalog_module()
    write_board_package(tmp_path / "fixture-model")

    def prohibit_full_decompression(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the one-shot zlib API must not be used")

    monkeypatch.setattr(module.zlib, "decompress", prohibit_full_decompression)

    inventory = module.discover_board_packages(tmp_path)

    assert [item.root.name for item in inventory.packages] == ["fixture-model"]


def test_primary_png_decoder_rejects_an_invalid_filter_after_alpha_zero(
    tmp_path: Path,
) -> None:
    """Alpha discovery must not skip structural validation of later scanlines."""
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    raw_rows = b"\x00\xff\xff\xff\x00" + b"\x05\xff\xff\xff\xff"
    ihdr = struct.pack(">IIBBBBB", 1, 2, 8, 6, 0, 0, 0)
    malformed = (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw_rows))
        + _png_chunk(b"IEND")
    )
    (package / "assets" / "primary.png").write_bytes(malformed)

    with pytest.raises(ValueError, match="invalid PNG row filter"):
        module.discover_board_packages(tmp_path)


def test_primary_png_decoder_checks_later_filters_without_unfiltering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep full structural checks without Python pixel work after alpha-zero."""
    module = load_board_catalog_module()
    write_board_package(tmp_path / "fixture-model")
    original = module._unfilter_png_row
    calls = 0

    def count_rows(*args: object, **kwargs: object) -> bytes:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_unfilter_png_row", count_rows)

    module.discover_board_packages(tmp_path)

    assert calls == 1


def test_discovery_rejects_malformed_completed_package(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    (package / "board.json").write_text("{ malformed", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        module.discover_board_packages(tmp_path)


def test_discovery_rejects_symlinked_direct_children_and_members(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    outside = write_board_package(tmp_path / "outside")
    root = tmp_path / "Hangboards"
    root.mkdir()
    (root / "linked-model").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        module.discover_board_packages(root)

    (root / "linked-model").unlink()
    package = write_board_package(root / "fixture-model")
    primary = package / "assets" / "primary.png"
    primary.unlink()
    primary.symlink_to(outside / "assets" / "primary.png")

    with pytest.raises(ValueError, match="symlink"):
        module.discover_board_packages(root)


def test_package_loader_consumes_embedded_hold_geometry(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"].append(
        {
            "frame": {"x": 0.4, "y": 0.1, "width": 0.1, "height": 0.2},
            "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
        }
    )
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)
    hold = package.board.holds[0]

    assert len(hold.geometry) == 2
    assert (hold.frame.x, hold.frame.y, hold.frame.width, hold.frame.height) == pytest.approx(
        (0.1, 0.1, 0.4, 0.4)
    )
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_unversioned_board_loads_its_declared_primary_presentation(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    package = module.load_board_package(package_root)

    assert package.board.presentations == (
        module.BoardPresentation(
            id="primary",
            name="Primary",
            asset_path="assets/primary.png",
            aspect_ratio=2,
            is_default=True,
        ),
    )
    assert {hold.presentation_id for hold in package.board.holds} == {"primary"}


def test_unversioned_board_loads_declared_presentations_and_scoped_holds(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(
        write_multi_presentation_board_package(tmp_path / "fixture-model")
    )

    assert package.board.presentations == (
        module.BoardPresentation("front", "Front", "assets/primary.png", 2, True),
        module.BoardPresentation("back", "Back", "assets/back.png", 2, False),
    )
    assert [(hold.id, hold.presentation_id) for hold in package.board.holds] == [
        ("hold-left", "front"),
        ("hold-right", "back"),
    ]
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_unversioned_board_rejects_a_declared_image_with_a_mismatched_aspect_ratio(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    (package_root / "assets" / "back.png").write_bytes(ALTERNATE_PRIMARY_PNG_BYTES)

    with pytest.raises(ValueError, match="aspectRatio.*within 0.1%"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    "write_package",
    [write_board_package, write_multi_presentation_board_package],
    ids=["primary", "multi-presentation"],
)
def test_package_loader_reports_missing_required_top_level_fields_as_value_errors(
    tmp_path: Path, write_package
) -> None:
    module = load_board_catalog_module()
    package_root = write_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document.pop("manufacturer")
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=r"board\.json is missing keys: \['manufacturer'\]"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["presentations"].__setitem__(
                1,
                {
                    **document["presentations"][1],
                    "id": "front",
                },
            ),
            "duplicate presentation id",
        ),
        (
            lambda document: [
                presentation.__setitem__("default", False)
                for presentation in document["presentations"]
            ],
            "exactly one default presentation",
        ),
        (
            lambda document: document["presentations"].__setitem__(
                1,
                {
                    **document["presentations"][1],
                    "default": True,
                },
            ),
            "exactly one default presentation",
        ),
    ],
)
def test_unversioned_board_rejects_invalid_presentation_identifiers_and_defaults(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    mutation(document)
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


def test_unversioned_board_rejects_hold_with_an_unknown_presentation_id(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["holds"][0]["presentationID"] = "missing"
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown presentationID"):
        module.load_board_package(package_root)


def test_unversioned_board_rejects_alias_chains_and_alias_owned_holds(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    (package_root / "assets" / "front-inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    document["presentations"].append(
        {
            "id": "front-inverted",
            "name": "Front upside down",
            "assetPath": "assets/front-inverted.png",
            "aspectRatio": 2,
            "default": False,
            "sourcePresentationID": "front",
            "isInverted": True,
        }
    )
    document["presentations"].append(
        {
            "id": "front-inverted-twice",
            "name": "Front twice inverted",
            "assetPath": "assets/front-inverted.png",
            "aspectRatio": 2,
            "default": False,
            "sourcePresentationID": "front-inverted",
            "isInverted": False,
        }
    )
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="must reference a canonical presentation"):
        module.load_board_package(package_root)

    document["presentations"].pop()
    document["holds"][0]["presentationID"] = "front-inverted"
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="must be owned by a canonical presentation"):
        module.load_board_package(package_root)


def test_direct_two_anchor_cord_rig_matches_ios_schema(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    rig = {
        "type": "directTwoAnchor",
        "sceneSize": {"width": 1200, "height": 1464},
        "sourceFrame": {"x": 0, "y": 214, "width": 1200, "height": 1250},
        "innerFaceFrame": {"x": -100, "y": -10, "width": 1400, "height": 1400},
        "attachmentPoints": [
            {"x": 203, "y": 712},
            {"x": 997, "y": 712},
        ],
        "pullPoint": {"x": 600, "y": 71.5},
        "eyeletRadius": 34,
    }
    document["presentations"][0].update(id="primary", name="Primary")
    document["presentations"][1].update(
        aspectRatio=50 / 61,
        cordRig=rig,
    )
    document["presentations"].append(
        {
            "id": "rig-rotated",
            "name": "Rig rotated",
            "assetPath": "assets/rig-rotated.png",
            "aspectRatio": 50 / 61,
            "default": False,
            "sourcePresentationID": "back",
            "isInverted": True,
            "geometryRotationAnchor": {"x": 0.5, "y": 0.6174863387978142},
        }
    )
    document["holds"][0]["presentationID"] = "primary"
    document["holds"][1]["geometry"][0]["frame"] = {
        "x": 0.2,
        "y": 0.2,
        "width": 0.1,
        "height": 0.2,
    }
    square_png = (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + _png_chunk(b"IEND")
    )
    (package_root / "assets" / "back.png").write_bytes(square_png)
    (package_root / "assets" / "rig-rotated.png").write_bytes(square_png)
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)
    presentations = {item.id: item for item in package.board.presentations}
    back = presentations["back"]
    rig_rotated = presentations["rig-rotated"]
    primary = presentations["primary"]

    assert back.cord_rig == module.DirectTwoAnchorCordRig(
        scene_size=module.CordSize(1200, 1464),
        source_frame=module.CordRect(0, 214, 1200, 1250),
        inner_face_frame=module.CordRect(-100, -10, 1400, 1400),
        attachment_points=(module.CordPoint(203, 712), module.CordPoint(997, 712)),
        pull_point=module.CordPoint(600, 71.5),
        eyelet_radius=34,
    )
    assert back.source_presentation_id is None
    assert rig_rotated.cord_rig is None
    assert rig_rotated.source_presentation_id == "back"
    assert rig_rotated.aspect_ratio == 50 / 61
    assert rig_rotated.geometry_rotation_anchor == module.NormalizedPoint(
        0.5, 0.6174863387978142
    )
    assert primary.cord_rig is None

    wide_png = (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00\x00\x00"))
        + _png_chunk(b"IEND")
    )
    (package_root / "assets" / "back.png").write_bytes(wide_png)
    with pytest.raises(
        ValueError,
        match=re.escape(
            "board.json.presentations[back].cordRig.innerFaceFrame aspect ratio "
            "must match its image width/height within 0.1%"
        ),
    ):
        module.load_board_package(package_root)
    (package_root / "assets" / "back.png").write_bytes(square_png)

    document["presentations"][1]["cordRig"]["unexpected"] = True
    board_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match=r"cordRig has unknown keys: \['unexpected'\]"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("scene_width", "scene_height"),
    [(1e308, 1e-308), (1e-308, 1e308)],
    ids=("overflow", "underflow"),
)
def test_direct_two_anchor_cord_rig_rejects_unrepresentable_scene_ratio(
    tmp_path: Path,
    scene_width: float,
    scene_height: float,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["presentations"][1]["cordRig"] = {
        "type": "directTwoAnchor",
        "sceneSize": {"width": scene_width, "height": scene_height},
        "sourceFrame": {"x": 0, "y": 0, "width": 1, "height": 1},
        "innerFaceFrame": {"x": 0, "y": 0, "width": 1, "height": 1},
        "attachmentPoints": [{"x": 0, "y": 1}, {"x": 1, "y": 1}],
        "pullPoint": {"x": 0.5, "y": 0},
        "eyeletRadius": 0.1,
    }
    board_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "presentation back.aspectRatio must match cordRig.sceneSize within 0.1%"
        ),
    ):
        module.load_board_package(package_root)


def test_unversioned_board_keeps_omitted_alias_rotation_anchor_as_center_compatibility(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
    )
    document["holds"] = [
        _source_hold_with_frames(
            "center-source",
            [{"x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}],
        )
    ]
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    assert package.board.presentations[1].geometry_rotation_anchor is None


def test_unversioned_board_preserves_a_valid_non_center_alias_rotation_anchor(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
        geometryRotationAnchor={"x": 0.6, "y": 0.5},
    )
    document["holds"] = document["holds"][:1]
    document["holds"][0]["geometry"][0]["frame"] = {
        "x": 0.2,
        "y": 0.1,
        "width": 0.1,
        "height": 0.4,
    }
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    assert package.board.presentations[1].geometry_rotation_anchor == module.NormalizedPoint(
        0.6, 0.5
    )


def test_unversioned_board_loads_explicit_arbitrary_alias_rotation() -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()
    document["presentations"][1].update(
        sourcePresentationID="front",
        rotationDegrees=135,
        geometryRotationAnchor={"x": 0.5, "y": 0.5},
    )
    document["holds"] = [
        _source_hold_with_frames(
            "center-source",
            [{"x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}],
        )
    ]

    board = module._load_board(document)

    alias = board.presentations[1]
    assert alias.rotation_degrees == 135
    assert alias.resolved_rotation_degrees == 135
    assert alias.is_inverted is False


def test_unversioned_board_maps_legacy_inversion_to_180_degrees() -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
    )
    document["holds"] = document["holds"][:1]

    alias = module._load_board(document).presentations[1]

    assert alias.rotation_degrees is None
    assert alias.resolved_rotation_degrees == 180


@pytest.mark.parametrize("rotation", [-0.1, 360, float("inf"), float("nan"), True])
def test_unversioned_board_rejects_non_normalized_alias_rotation(
    rotation: object,
) -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()
    document["presentations"][1].update(
        sourcePresentationID="front",
        rotationDegrees=rotation,
    )
    document["holds"] = document["holds"][:1]

    with pytest.raises(ValueError, match="rotationDegrees"):
        module._load_board(document)


def test_unversioned_board_rejects_ambiguous_legacy_and_explicit_rotation() -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()
    document["presentations"][1].update(
        sourcePresentationID="front",
        rotationDegrees=180,
        isInverted=True,
    )
    document["holds"] = document["holds"][:1]

    with pytest.raises(ValueError, match="must not declare both"):
        module._load_board(document)


def test_unversioned_board_rejects_arbitrarily_rotated_frame_outside_canvas() -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()
    document["presentations"][1].update(
        sourcePresentationID="front",
        rotationDegrees=45,
        geometryRotationAnchor={"x": 0.5, "y": 0.5},
    )
    document["holds"] = [
        _source_hold_with_frames(
            "corner-source",
            [{"x": 0.8, "y": 0.8, "width": 0.2, "height": 0.2}],
        )
    ]

    with pytest.raises(ValueError, match="projects source hold geometry outside"):
        module._load_board(document)


def _source_hold_with_frames(
    hold_id: str, frames: list[dict[str, float]]
) -> dict[str, object]:
    return {
        "id": hold_id,
        "name": hold_id,
        "kind": "jug",
        "presentationID": "front",
        "geometry": [
            {
                "frame": frame,
                "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
            }
            for frame in frames
        ],
    }


def test_unversioned_board_accepts_alias_aspect_ratio_serialization_rounding(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
        aspectRatio=2.0000000005,
    )
    document["holds"] = document["holds"][:1]
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    assert package.board.presentations[1].aspect_ratio == 2.0000000005


def test_unversioned_board_accepts_a_projected_frame_on_the_exact_boundary(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
        geometryRotationAnchor={"x": 0.15, "y": 0.15},
    )
    document["holds"] = [
        _source_hold_with_frames(
            "boundary-source",
            [{"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}],
        )
    ]
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    assert package.board.presentations[1].geometry_rotation_anchor == module.NormalizedPoint(
        0.15, 0.15
    )


@pytest.mark.parametrize(
    ("anchor", "frame"),
    [
        ({"x": 0.1, "y": 0.5}, {"x": 0.2, "y": 0.4, "width": 0.2, "height": 0.1}),
        ({"x": 0.9, "y": 0.5}, {"x": 0.7, "y": 0.4, "width": 0.1, "height": 0.1}),
        ({"x": 0.5, "y": 0.1}, {"x": 0.4, "y": 0.2, "width": 0.1, "height": 0.2}),
        ({"x": 0.5, "y": 0.9}, {"x": 0.4, "y": 0.7, "width": 0.1, "height": 0.1}),
    ],
    ids=["left", "right", "top", "bottom"],
)
def test_unversioned_board_rejects_each_projected_frame_boundary(
    tmp_path: Path, anchor: dict[str, float], frame: dict[str, float]
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
        geometryRotationAnchor=anchor,
    )
    document["holds"] = [_source_hold_with_frames("boundary-source", [frame])]
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="projects source hold geometry outside the normalized canvas"):
        module.load_board_package(package_root)


def test_unversioned_board_rejects_an_off_canvas_later_piece_of_a_later_source_hold(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["presentations"][1].update(
        sourcePresentationID="front",
        isInverted=True,
        geometryRotationAnchor={"x": 0.1, "y": 0.5},
    )
    document["holds"] = [
        _source_hold_with_frames(
            "first-source",
            [{"x": 0.1, "y": 0.4, "width": 0.1, "height": 0.1}],
        ),
        _source_hold_with_frames(
            "second-source",
            [
                {"x": 0.1, "y": 0.4, "width": 0.1, "height": 0.1},
                {"x": 0.2, "y": 0.4, "width": 0.2, "height": 0.1},
            ],
        ),
    ]
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="projects source hold geometry outside the normalized canvas"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["presentations"][0].__setitem__(
                "geometryRotationAnchor", {"x": 0.5, "y": 0.5}
            ),
            "requires sourcePresentationID",
        ),
        (
            lambda document: document["presentations"][1].update(
                sourcePresentationID="front",
                isInverted=False,
                geometryRotationAnchor={"x": 0.5, "y": 0.5},
            ),
            "requires isInverted true",
        ),
        (
            lambda document: document["presentations"][1].update(
                sourcePresentationID="front",
                isInverted=True,
                aspectRatio=2.0001,
            ),
            "must match source presentation aspectRatio",
        ),
        (
            lambda document: document["presentations"][1].update(
                sourcePresentationID="front",
                isInverted=True,
                geometryRotationAnchor={"x": 0.04, "y": 0.5},
            ),
            "projects source hold geometry outside the normalized canvas",
        ),
    ],
    ids=["canonical", "non-inverted", "aspect-ratio", "off-canvas-projection"],
)
def test_unversioned_board_rejects_invalid_alias_rotation_anchor_contract(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    mutation(document)
    document["holds"] = document["holds"][:1]
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda package, document: (package / "assets" / "undeclared.png").write_bytes(
                PRIMARY_PNG_BYTES
            ),
            "undeclared presentation asset",
        ),
        (
            lambda package, document: (package / "assets" / "back.png").unlink(),
            "missing declared presentation asset",
        ),
        (
            lambda package, document: document["presentations"][1].__setitem__(
                "assetPath", "assets/../outside.png"
            ),
            "assetPath must name a PNG beneath assets/",
        ),
    ],
)
def test_unversioned_board_rejects_undeclared_missing_and_escaping_assets(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    mutation(package_root, document)
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


def test_package_loader_retains_shape_constraint(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["shapeConstraint"] = {
        "shape": "roundedRectangle",
        "rotationDegrees": -17.5,
    }
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    constraint = package.board.holds[0].geometry[0].shape_constraint
    assert constraint is not None
    assert constraint.shape == "roundedRectangle"
    assert constraint.rotation_degrees == -17.5


def test_package_loader_accepts_optional_hand_capacity_and_rejects_invalid_values(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["handCapacity"] = 2
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)
    assert package.board.holds[0].hand_capacity == 2

    document["holds"][0]["handCapacity"] = 3
    board_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="handCapacity must be in 1...2"):
        module.load_board_package(package_root)


def test_package_loader_rejects_path_that_does_not_fill_its_declared_frame(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["shape"] = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0.1, 0.1]},
            {"command": "line", "to": [0.9, 0.1]},
            {"command": "line", "to": [0.9, 0.9]},
            {"command": "line", "to": [0.1, 0.9]},
            {"command": "close"},
        ],
    }
    board_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="frame must match its derived shape bounds"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    "constraint",
    [
        {"rotationDegrees": 0},
        {"shape": "oval"},
        {"shape": "triangle", "rotationDegrees": 0},
        {"shape": "circle", "rotationDegrees": True},
        {"shape": "pill", "rotationDegrees": float("inf")},
        {"shape": "pill", "rotationDegrees": 10**1000},
        {"shape": "rectangle", "rotationDegrees": -180.01},
        {"shape": "oval", "rotationDegrees": 180},
        {"shape": "oval", "rotationDegrees": 0, "unexpected": True},
    ],
)
def test_package_loader_rejects_invalid_shape_constraints(
    tmp_path: Path, constraint: object
) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["shapeConstraint"] = constraint
    board_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="shapeConstraint"):
        module.load_board_package(package_root)


def test_package_loader_rejects_unknown_board_hold_and_geometry_keys(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    for location in ("board", "hold", "geometry"):
        package = write_board_package(tmp_path / location)
        board_path = package / "board.json"
        document = board_document()
        if location == "board":
            document["unexpected"] = True
        elif location == "hold":
            document["holds"][0]["unexpected"] = True
        else:
            document["holds"][0]["geometry"][0]["unexpected"] = True
        board_path.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(ValueError, match="unknown keys"):
            module.load_board_package(package)
