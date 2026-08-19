from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from conftest import board_document
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hangboard_vectorizer.board_catalog_cli import main


def _derivation_module():
    specification = importlib.util.find_spec(
        "hangboard_vectorizer.board_geometry_derivation"
    )
    assert specification is not None, "geometry derivation API is absent"
    return importlib.import_module("hangboard_vectorizer.board_geometry_derivation")


def _piece(x: float) -> dict[str, object]:
    return {
        "frame": {"x": x, "y": 0.1, "width": 0.1, "height": 0.2},
        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
    }


def _write_package(
    root: Path,
    image: Image.Image,
    *,
    piece_counts: tuple[int, ...] = (1,),
    board_id: str = "fixture.geometry",
) -> Path:
    assets = root / "assets"
    assets.mkdir(parents=True)
    image.save(assets / "primary.png", format="PNG")
    document = board_document(board_id)
    document["aspectRatio"] = image.width / image.height
    document["holds"] = [
        {
            "id": f"hold-{hold_index + 1}",
            "name": f"Hold {hold_index + 1}",
            "kind": "edge" if hold_index % 2 else "jug",
            "geometry": [
                _piece(0.05 + 0.15 * (hold_index + piece_index))
                for piece_index in range(piece_count)
            ],
        }
        for hold_index, piece_count in enumerate(piece_counts)
    ]
    (root / "board.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    return root


def _transparent_rectangles(
    size: tuple[int, int] = (128, 80),
) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((14, 18, 42, 52), radius=5, fill=(142, 91, 49, 255))
    draw.rounded_rectangle((82, 22, 113, 55), radius=5, fill=(142, 91, 49, 255))
    return image


def _textured_board(*, unstable_bridge: bool = False) -> Image.Image:
    width, height = 128, 80
    pixels = np.full((height, width, 4), (246, 244, 241, 255), dtype=np.uint8)
    for y in range(10, 71):
        for x in range(8, 120):
            illumination = (x - 64) // 12
            grain = ((x * 17 + y * 11) % 9) - 4
            pixels[y, x] = (
                166 + illumination + grain,
                122 + illumination + grain,
                77 + illumination + grain,
                255,
            )
    image = Image.fromarray(pixels, mode="RGBA")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 29, 49, 47), radius=4, fill=(69, 49, 35, 255))
    draw.rounded_rectangle((78, 28, 105, 47), radius=4, fill=(224, 193, 151, 255))
    if unstable_bridge:
        for x in range(50, 78):
            shade = 70 + (x - 50) * 3
            draw.line((x, 36, x, 40), fill=(shade, shade - 12, shade - 24, 255))
    return image


def _candidate_near_x(report, x: float):
    return min(
        report.candidates,
        key=lambda candidate: abs((candidate.bounds[0] + candidate.bounds[2]) / 2 - x),
    )


def _complete_mapping(report, holds: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(report.candidates, key=lambda candidate: candidate.bounds)
    cursor = 0
    mapped_holds = []
    for hold in holds:
        piece_count = len(hold["geometry"])
        mapped_holds.append(
            {
                "holdID": hold["id"],
                "candidateIDs": [
                    candidate.candidate_id
                    for candidate in ordered[cursor : cursor + piece_count]
                ],
            }
        )
        cursor += piece_count
    mapped_ids = {
        candidate_id for hold in mapped_holds for candidate_id in hold["candidateIDs"]
    }
    return {
        "schemaVersion": 1,
        "manifestHash": report.manifest_hash,
        "holds": mapped_holds,
        "rejectedCandidateIDs": [
            candidate.candidate_id
            for candidate in ordered
            if candidate.candidate_id not in mapped_ids
        ],
        "symmetry": [],
    }


def test_derives_disconnected_silhouettes_from_transparent_background(
    tmp_path: Path,
) -> None:
    module = _derivation_module()
    package = _write_package(tmp_path / "board", _transparent_rectangles())

    report = module.derive_geometry_candidates(package)

    silhouettes = [
        candidate
        for candidate in report.candidates
        if candidate.source == "foregroundSilhouette"
    ]
    assert len(silhouettes) == 2
    assert all(candidate.topology_stable for candidate in silhouettes)
    assert all(candidate.display_path.endswith(" Z") for candidate in silhouettes)


def test_finds_dark_and_light_recesses_despite_texture_and_illumination(
    tmp_path: Path,
) -> None:
    module = _derivation_module()
    package = _write_package(tmp_path / "board", _textured_board())

    report = module.derive_geometry_candidates(package)

    polarities = {candidate.polarity for candidate in report.candidates}
    assert {"dark", "light"} <= polarities
    assert _candidate_near_x(report, 36).polarity == "dark"
    assert _candidate_near_x(report, 92).polarity == "light"


def test_rejects_nested_holes_instead_of_flattening_them(
    tmp_path: Path,
) -> None:
    module = _derivation_module()
    image = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((15, 10, 85, 70), fill=(130, 90, 55, 255))
    draw.ellipse((35, 25, 65, 55), fill=(0, 0, 0, 0))
    package = _write_package(tmp_path / "board", image)

    report = module.derive_geometry_candidates(package)

    assert not [
        candidate
        for candidate in report.candidates
        if candidate.source == "foregroundSilhouette"
    ]
    assert any(rejection.reason == "nestedHole" for rejection in report.rejections)


def test_touching_regions_remain_one_unlabeled_candidate(tmp_path: Path) -> None:
    module = _derivation_module()
    image = _textured_board()
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 29, 49, 47), fill=(65, 45, 30, 255))
    draw.rectangle((50, 29, 73, 47), fill=(65, 45, 30, 255))
    package = _write_package(tmp_path / "board", image)

    report = module.derive_geometry_candidates(package)

    touching = [
        candidate
        for candidate in report.candidates
        if candidate.polarity == "dark"
        and candidate.bounds[0] < 40
        and candidate.bounds[2] > 60
    ]
    assert len(touching) == 1


def test_records_only_native_gate_passing_mirror_pairs(tmp_path: Path) -> None:
    module = _derivation_module()
    image = Image.new("RGBA", (120, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((14, 20, 36, 48), radius=4, fill=(140, 90, 50, 255))
    draw.rounded_rectangle((84, 20, 106, 48), radius=4, fill=(140, 90, 50, 255))
    draw.polygon(((48, 55), (64, 52), (70, 69), (46, 70)), fill=(140, 90, 50, 255))
    package = _write_package(tmp_path / "board", image)

    report = module.derive_geometry_candidates(package)

    left = _candidate_near_x(report, 25)
    right = _candidate_near_x(report, 95)
    asymmetric = _candidate_near_x(report, 57)
    paired_ids = {
        candidate_id for pair in report.symmetry_pairs for candidate_id in pair
    }
    assert {left.candidate_id, right.candidate_id} <= paired_ids
    assert asymmetric.candidate_id not in paired_ids


def test_rejects_image_border_clipping(tmp_path: Path) -> None:
    module = _derivation_module()
    image = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((0, 15, 35, 45), fill=(140, 90, 50, 255))
    package = _write_package(tmp_path / "board", image)

    report = module.derive_geometry_candidates(package)

    assert not report.candidates
    assert any(
        rejection.reason == "imageBorderClipped" for rejection in report.rejections
    )


def test_rejects_threshold_unstable_residual_topology(tmp_path: Path) -> None:
    module = _derivation_module()
    package = _write_package(tmp_path / "board", _textured_board(unstable_bridge=True))

    report = module.derive_geometry_candidates(package)

    assert any(
        rejection.reason == "thresholdUnstable" for rejection in report.rejections
    )


def test_selects_rounded_rect_only_when_native_mask_gates_pass(tmp_path: Path) -> None:
    module = _derivation_module()
    image = Image.new("RGBA", (128, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 15, 48, 52), radius=8, fill=(140, 90, 50, 255))
    draw.polygon(
        ((74, 13), (113, 20), (105, 56), (84, 48), (70, 31)), fill=(140, 90, 50, 255)
    )
    package = _write_package(tmp_path / "board", image, piece_counts=(1, 1))

    report = module.derive_geometry_candidates(package)

    rounded = _candidate_near_x(report, 30)
    irregular = _candidate_near_x(report, 92)
    assert rounded.representation == "roundedRect"
    assert rounded.maximum_boundary_deviation_pixels <= 1.0
    assert rounded.symmetric_difference_ratio <= 0.0025
    assert irregular.representation == "path"


def test_report_is_byte_deterministic_and_ignores_package_semantics(
    tmp_path: Path,
) -> None:
    module = _derivation_module()
    image = _transparent_rectangles()
    first_root = _write_package(
        tmp_path / "first", image, piece_counts=(1, 1), board_id="fixture.first"
    )
    second_root = _write_package(
        tmp_path / "second", image, piece_counts=(2,), board_id="fixture.second"
    )

    first = module.derive_geometry_candidates(first_root)
    repeated = module.derive_geometry_candidates(first_root)
    semantic_variant = module.derive_geometry_candidates(second_root)

    assert first.manifest_bytes() == repeated.manifest_bytes()
    assert first.manifest_bytes() == semantic_variant.manifest_bytes()
    assert first.manifest_hash == repeated.manifest_hash


def test_materializes_complete_multi_piece_mapping_in_source_hold_order(
    tmp_path: Path,
) -> None:
    module = _derivation_module()
    package = _write_package(
        tmp_path / "board", _transparent_rectangles(), piece_counts=(2,)
    )
    source = json.loads((package / "board.json").read_text(encoding="utf-8"))
    report = module.derive_geometry_candidates(package)
    mapping = _complete_mapping(report, source["holds"])

    editor = module.materialize_editor_document(package, mapping)

    assert editor["canvas"] == {"width": 128, "height": 80}
    assert [region["key"] for region in editor["regions"]] == [
        "hold-1-piece-0",
        "hold-1-piece-1",
    ]
    assert [region["metadata"] for region in editor["regions"]] == [
        {"holdID": "hold-1", "pieceIndex": 0},
        {"holdID": "hold-1", "pieceIndex": 1},
    ]
    assert all(region["type"] == "jug" for region in editor["regions"])


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda mapping: mapping["holds"].pop(),
            "every audited hold",
        ),
        (
            lambda mapping: mapping["holds"][1].update(
                {"candidateIDs": mapping["holds"][0]["candidateIDs"]}
            ),
            "candidate ID is assigned more than once",
        ),
        (
            lambda mapping: mapping.update({"threshold": 17}),
            "unknown keys",
        ),
        (
            lambda mapping: mapping.update({"manifestHash": "0" * 64}),
            "manifest hash",
        ),
    ],
)
def test_materialization_fails_closed_for_incomplete_duplicate_or_unsafe_mapping(
    tmp_path: Path, mutate, message: str
) -> None:
    module = _derivation_module()
    package = _write_package(
        tmp_path / "board", _transparent_rectangles(), piece_counts=(1, 1)
    )
    source = json.loads((package / "board.json").read_text(encoding="utf-8"))
    report = module.derive_geometry_candidates(package)
    mapping = _complete_mapping(report, source["holds"])
    mutate(mapping)

    with pytest.raises(ValueError, match=message):
        module.materialize_editor_document(package, mapping)


def test_dry_run_cli_emits_deterministic_hash_bound_catalog_manifest(
    tmp_path: Path, capsys
) -> None:
    root = tmp_path / "catalog"
    _write_package(root / "board", _transparent_rectangles())

    assert main(["derive-hold-geometry", "--root", str(root)]) == 0
    first = capsys.readouterr().out.encode()
    assert main(["derive-hold-geometry", "--root", str(root)]) == 0
    second = capsys.readouterr().out.encode()

    assert first == second
    payload = json.loads(first)
    assert payload["write"] is False
    assert payload["boards"][0]["manifest"]["manifestHash"]
    assert "id" not in payload["boards"][0]["manifest"]
