from __future__ import annotations

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
    write_cad_source,
    write_multi_presentation_board_package,
    write_primary_only_draft,
)
from _board_package_helpers import board_contact_geometry, board_positions_document

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_real_canonical_package_and_forge_category_only_contact_decode() -> None:
    module = load_board_catalog_module()
    root = Path(__file__).resolve().parents[3] / "Hangboards"

    inventory = module.discover_board_packages(root, require_complete_inventory=True)
    forge = next(package.board for package in inventory.packages if package.board.id == "trango.rock-prodigy-forge")
    left = next(contact for contact in forge.contacts if contact.id == "large-flat-edge-left")

    assert left.shape == "flat"
    assert left.depth == module.HoldDepth(category="large")
    assert left.depth.range is None


def test_board_schema_decodes_category_and_range_depths_without_legacy_members() -> None:
    module = load_board_catalog_module()
    document = board_document()
    contact = document["contacts"][0]
    contact["shape"] = "flat"
    contact["depth"] = {"category": "large"}

    board = module._load_board(document)

    assert board.contacts[0].shape == "flat"
    assert board.contacts[0].depth == module.HoldDepth(category="large")
    contact["depth"] = {"range": {"minimum": 7.5, "maximum": 12.5}}
    assert module._load_board(document).contacts[0].depth == module.HoldDepth(
        range=module.MillimeterRange(7.5, 12.5)
    )


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
    assert board.contact_ids_for_position("flipped") == board.contact_ids_for_position("front")
    assert board.transition_kind("front", "front") == "same"
    assert board.transition_kind("front", "flipped") == "seamless"
    assert board.transition_kind("flipped", "front") == "setupRequired"


def test_board_schema_loads_optional_unilateral_hand_resolution() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["unilateralHandResolution"] = "athleteRelative"

    board = module._load_board(document)

    assert board.unilateral_hand_resolution == module.UnilateralHandResolution.ATHLETE_RELATIVE


def test_board_schema_loads_board_hand_capacity_default_and_rejects_invalid() -> None:
    module = load_board_catalog_module()
    omitted = module._load_board(board_document())
    assert omitted.hand_capacity == 2

    one_handed = board_document()
    one_handed["handCapacity"] = 1
    assert module._load_board(one_handed).hand_capacity == 1

    zero = board_document()
    zero["handCapacity"] = 0
    with pytest.raises(ValueError, match="handCapacity must be a positive integer"):
        module._load_board(zero)

    out_of_range = board_document()
    out_of_range["handCapacity"] = 3
    with pytest.raises(ValueError, match="handCapacity must be in 1...2"):
        module._load_board(out_of_range)

    conflict = board_document()
    conflict["handCapacity"] = 1
    conflict["contacts"][0]["handCapacity"] = 2
    with pytest.raises(ValueError, match="one-handed board cannot include contact"):
        module._load_board(conflict)


def test_board_revision_preserves_positional_model_contact_frames_argument() -> None:
    module = load_board_catalog_module()
    model_contact_frames = {("primary", "hold-a"): object()}

    board = module.BoardRevision(
        "board",
        "revision",
        {},
        (),
        (),
        (),
        (),
        (),
        model_contact_frames,
    )

    assert board.model_contact_frames is model_contact_frames
    assert board.unilateral_hand_resolution is None


@pytest.mark.parametrize("value", [None, "boardRelative", 1])
def test_board_schema_rejects_invalid_unilateral_hand_resolution(value: object) -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["unilateralHandResolution"] = value

    with pytest.raises(ValueError, match="unilateralHandResolution"):
        module._load_board(document)


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


def test_board_schema_rejects_position_without_canonical_presentation_contacts() -> None:
    module = load_board_catalog_module()
    document = board_positions_document(board_document())
    document["presentations"].append(
        {
            "id": "unused",
            "name": "Unused",
            "aspectRatio": 2,
            "isDefault": False,
            "derivation": {"type": "original"},
            "media": {
                "type": "raster",
                "assetPath": "assets/unused.png",
                "contactGeometry": {},
            },
        }
    )
    document["positions"].append({"id": "unused", "presentationID": "unused"})

    with pytest.raises(ValueError, match="must own at least one physical contact"):
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


def test_board_schema_accepts_equal_bound_fractional_depth_range() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["contacts"][0]
    hold["depth"] = {"range": {"minimum": 7.5, "maximum": 7.5}}

    board = module._load_board(document)

    assert board.contacts[0].depth == module.HoldDepth(
        range=module.MillimeterRange(7.5, 7.5)
    )


def test_board_schema_rejects_hold_with_unknown_equipment_object_id() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["equipmentObjects"] = [{"id": "primary"}]
    document["contacts"][0]["equipmentObjectID"] = "missing"

    with pytest.raises(ValueError, match="unknown equipment object"):
        module._load_board(document)


@pytest.mark.parametrize("policy", ["unavailable", "invented"])
def test_board_schema_rejects_legacy_missing_hand_capacity_policy(policy: str) -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["equipmentObjects"] = [
        {"id": "primary", "missingHandCapacityPolicy": policy}
    ]

    with pytest.raises(ValueError, match="missingHandCapacityPolicy"):
        module._load_board(document)


def test_board_schema_accepts_fractional_continuous_depth_range() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["contacts"][0]
    hold["depth"] = {"range": {"minimum": 7.5, "maximum": 12.5}}

    board = module._load_board(document)

    assert board.contacts[0].depth == module.HoldDepth(
        range=module.MillimeterRange(7.5, 12.5)
    )


def test_board_schema_accepts_category_only_depth_without_inventing_a_measurement() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["contacts"][0]
    hold["depth"] = {"category": "large"}

    board = module._load_board(document)

    assert board.contacts[0].depth == module.HoldDepth(category="large")


def test_board_schema_rejects_legacy_depth_range_member() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["contacts"][0]["depthRangeMillimeters"] = {
        "lowerBound": 7.5,
        "upperBound": 12.5,
    }

    with pytest.raises(ValueError, match=r"board\.json\.contacts\[0\] has unknown keys"):
        module._load_board(document)


def test_board_schema_accepts_reciprocal_gaston_pairs() -> None:
    module = load_board_catalog_module()
    document = board_document()
    template = document["contacts"][0]
    left = {**template, "id": "gaston-left", "name": "Left gaston", "kind": "gaston", "pairedContactID": "gaston-right"}
    right = {**template, "id": "gaston-right", "name": "Right gaston", "kind": "gaston", "pairedContactID": "gaston-left"}
    document["contacts"] = [left, right]
    geometry = document["presentations"][0]["media"]["contactGeometry"].pop(
        "hold-left"
    )
    document["presentations"][0]["media"]["contactGeometry"] = {
        "gaston-left": geometry,
        "gaston-right": geometry,
    }

    board = module._load_board(document)

    assert [hold.kind for hold in board.contacts] == ["gaston", "gaston"]
    assert [hold.paired_contact_id for hold in board.contacts] == ["gaston-right", "gaston-left"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda holds: holds[0].__setitem__("kind", "gaston"),
        lambda holds: holds[0].update(kind="gaston", pairedContactID="not a valid identifier"),
        lambda holds: holds[0].__setitem__("pairedContactID", "gaston-right"),
        lambda holds: holds[0].update(kind="gaston", pairedContactID="gaston-left"),
        lambda holds: holds[0].update(kind="gaston", pairedContactID="missing"),
        lambda holds: holds[0].update(kind="gaston", pairedContactID="gaston-right"),
        lambda holds: (
            holds[0].update(kind="gaston", pairedContactID="gaston-right"),
            holds[1].update(kind="gaston", pairedContactID="another-gaston"),
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
    template = document["contacts"][0]
    document["contacts"] = [
        {**template, "id": "gaston-left", "name": "Left gaston"},
        {**template, "id": "gaston-right", "name": "Right gaston"},
    ]
    mutate(document["contacts"])

    with pytest.raises(ValueError):
        module._load_board(document)


@pytest.mark.parametrize("shape", ["flat", "round"])
def test_board_schema_exposes_sloper_shape_as_a_contact_shape(shape: str) -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["contacts"][0]
    hold["kind"] = "sloper"
    hold["shape"] = shape

    board = module._load_board(document)

    assert board.contacts[0].shape == shape


def test_board_schema_allows_sloper_without_shape() -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["contacts"][0]["kind"] = "sloper"

    board = module._load_board(document)

    assert board.contacts[0].shape is None


def test_board_schema_rejects_legacy_sloper_metadata() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["contacts"][0]
    hold["kind"] = "sloper"
    hold["sloper"] = {"type": "round"}

    with pytest.raises(ValueError, match=r"board\.json\.contacts\[0\] has unknown keys"):
        module._load_board(document)


def test_board_schema_rejects_unsupported_depth_category() -> None:
    module = load_board_catalog_module()
    document = board_document()
    hold = document["contacts"][0]
    hold["depth"] = {"category": "huge"}

    with pytest.raises(ValueError, match=r"depth\.category is unsupported"):
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
    document["presentations"][0]["media"]["contactGeometry"]["hold-left"].append(
        {
            "frame": {"x": 0.4, "y": 0.1, "width": 0.1, "height": 0.2},
            "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
        }
    )
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)
    geometry = board_contact_geometry(package.board)["hold-left"]

    assert len(geometry) == 2
    frame = package.board.contact_frame("hold-left", "primary")
    assert (frame.x, frame.y, frame.width, frame.height) == pytest.approx(
        (0.1, 0.1, 0.4, 0.4)
    )
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_v3_board_loads_its_declared_primary_presentation(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    package = module.load_board_package(package_root)

    assert len(package.board.presentations) == 1
    presentation = package.board.presentations[0]
    assert (
        presentation.id,
        presentation.name,
        presentation.asset_path,
        presentation.aspect_ratio,
        presentation.is_default,
        presentation.source_presentation_id,
    ) == ("primary", "Primary", "assets/primary.png", 2, True, None)
    assert set(presentation.media.contact_geometry) == {"hold-left"}


def test_v3_board_loads_declared_presentations_and_scoped_contacts(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(
        write_multi_presentation_board_package(tmp_path / "fixture-model")
    )

    assert [presentation.id for presentation in package.board.presentations] == [
        "front",
        "back",
    ]
    assert package.board.contact_ids_for_position("front") == ("hold-left",)
    assert package.board.contact_ids_for_position("back") == ("hold-right",)
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_v3_board_rejects_a_declared_image_with_a_mismatched_aspect_ratio(
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
                presentation.__setitem__("isDefault", False)
                for presentation in document["presentations"]
            ],
            "exactly one default presentation",
        ),
        (
            lambda document: document["presentations"].__setitem__(
                1,
                {
                    **document["presentations"][1],
                    "isDefault": True,
                },
            ),
            "exactly one default presentation",
        ),
    ],
)
def test_v3_board_rejects_invalid_presentation_identifiers_and_defaults(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    mutation(document)
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


def test_v3_board_rejects_geometry_with_an_unknown_contact_id(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    geometry = document["presentations"][0]["media"]["contactGeometry"].pop(
        "hold-left"
    )
    document["presentations"][0]["media"]["contactGeometry"]["missing"] = geometry
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="only own physical contacts"):
        module.load_board_package(package_root)


def test_v3_board_rejects_derived_presentation_chains(
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
            "aspectRatio": 2,
            "isDefault": False,
            "derivation": {
                "type": "derived",
                "sourcePresentationID": "front",
                "isInverted": True,
            },
            "media": {
                "type": "raster",
                "assetPath": "assets/front-inverted.png",
                "contactGeometry": document["presentations"][0]["media"][
                    "contactGeometry"
                ],
            },
        }
    )
    document["presentations"].append(
        {
            "id": "front-inverted-twice",
            "name": "Front twice inverted",
            "aspectRatio": 2,
            "isDefault": False,
            "derivation": {
                "type": "derived",
                "sourcePresentationID": "front-inverted",
                "isInverted": False,
            },
            "media": {
                "type": "raster",
                "assetPath": "assets/front-inverted.png",
                "contactGeometry": document["presentations"][0]["media"][
                    "contactGeometry"
                ],
            },
        }
    )
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="must reference a canonical presentation"):
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
                "media",
                {
                    **document["presentations"][1]["media"],
                    "assetPath": "assets/../outside.png",
                },
            ),
            "assetPath must name a PNG beneath assets/",
        ),
    ],
)
def test_v3_board_rejects_undeclared_missing_and_escaping_assets(
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
    document["presentations"][0]["media"]["contactGeometry"]["hold-left"][0][
        "shapeConstraint"
    ] = {
        "shape": "roundedRectangle",
        "rotationDegrees": -17.5,
    }
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    constraint = board_contact_geometry(package.board)["hold-left"][0].shape_constraint
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
    document["contacts"][0]["handCapacity"] = 2
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)
    assert package.board.contacts[0].hand_capacity == 2

    document["contacts"][0]["handCapacity"] = 3
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
    document["presentations"][0]["media"]["contactGeometry"]["hold-left"][0][
        "shape"
    ] = {
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
    document["presentations"][0]["media"]["contactGeometry"]["hold-left"][0][
        "shapeConstraint"
    ] = constraint
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
            document["contacts"][0]["unexpected"] = True
        else:
            document["presentations"][0]["media"]["contactGeometry"]["hold-left"][0][
                "unexpected"
            ] = True
        board_path.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(ValueError, match="unknown keys"):
            module.load_board_package(package)


def test_a_cad_backed_package_validates_its_generated_board_json(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "cad-model")
    authored = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    source = write_cad_source(package_root)

    inventory = module.discover_board_packages(tmp_path, require_complete_inventory=True)

    (package,) = inventory.packages
    assert package.board.id == authored["id"]
    assert package.generated_board_json == module.cad_source.generate_board_json(source)
    assert json.loads(package.generated_board_json) == authored
    assert module.read_board_json(package_root) == package.generated_board_json
    assert not (package_root / "board.json").exists()


def test_a_hand_authored_package_has_no_generated_board_json(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "plain-model")
    package = module.load_board_package(package_root)
    assert package.generated_board_json is None
    assert module.read_board_json(package_root) == (package_root / "board.json").read_bytes()


def test_a_cad_backed_package_rejects_an_on_disk_board_json(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "cad-model")
    write_cad_source(package_root, remove_board_json=False)

    with pytest.raises(ValueError, match=r"cad-model/board.json must not exist.*generated from cad-model\.FCStd"):
        module.discover_board_packages(tmp_path)


def test_a_cad_backed_package_needs_a_generatable_source(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "cad-model")
    source = write_cad_source(package_root)
    source.write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:" + "0" * 64 + "\nsize 1\n"
    )
    with pytest.raises(ValueError, match="cannot generate board.json.*LFS pointer"):
        module.load_board_package(package_root)


def test_the_generated_document_is_validated_with_its_exact_number_spelling() -> None:
    """Rock Rings' nine-decimal instance translations survive generation."""
    module = load_board_catalog_module()
    root = Path(__file__).resolve().parents[3] / "Hangboards" / "metolius-rock-rings-3d"
    source = module.cad_source.package_source_path(root)
    if module.cad_source._is_lfs_pointer(source):
        pytest.skip("FCStd sources are Git LFS pointers; run `git lfs pull` first")
    package = module.load_board_package(root)
    assert package.generated_board_json is not None
    assert b"                0.000000000,\n" in package.generated_board_json
    module._validate_instance_translation_lexemes(package.generated_board_json.decode())


def test_every_cad_backed_package_board_json_is_gitignored() -> None:
    module = load_board_catalog_module()
    repository = Path(__file__).resolve().parents[3]
    ignored = {
        line.strip()
        for line in (repository / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    cad_packages = sorted(
        path.name
        for path in (repository / "Hangboards").iterdir()
        if path.is_dir() and module.cad_source.is_cad_package(path)
    )
    assert cad_packages
    listed = {line for line in ignored if line.startswith("/Hangboards/")}
    assert listed == {f"/Hangboards/{slug}/board.json" for slug in cad_packages}
