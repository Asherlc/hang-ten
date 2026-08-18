from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from conftest import board_document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hangboard_vectorizer import board_presentation  # noqa: E402
from hangboard_vectorizer.board_catalog_cli import main  # noqa: E402
from hangboard_vectorizer.board_presentation import normalize_package_presentation  # noqa: E402


def _rounded_piece(x: float, y: float, width: float, height: float) -> dict[str, object]:
    return {
        "frame": {"x": x, "y": y, "width": width, "height": height},
        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
    }


def _hold(identifier: str, *pieces: dict[str, object]) -> dict[str, object]:
    return {
        "id": identifier,
        "name": identifier,
        "kind": "jug",
        "geometry": list(pieces),
    }


def _path_piece(x: float, y: float, width: float, height: float) -> dict[str, object]:
    return {
        "frame": {"x": x, "y": y, "width": width, "height": height},
        "shape": {
            "type": "path",
            "commands": [
                {"command": "move", "to": [0, 0]},
                {"command": "line", "to": [1, 0]},
                {"command": "line", "to": [1, 1]},
                {"command": "line", "to": [0, 1]},
                {"command": "close"},
            ],
        },
    }


def _write_package(
    root: Path,
    *,
    size: tuple[int, int],
    background: tuple[int, int, int, int],
    visible_rectangles: list[tuple[int, int, int, int]],
    holds: list[dict[str, object]],
) -> Path:
    assets = root / "assets"
    assets.mkdir(parents=True)
    image = Image.new("RGBA", size, background)
    draw = ImageDraw.Draw(image)
    for rectangle in visible_rectangles:
        draw.rectangle(rectangle, fill=(88, 55, 32, 255))
    image.save(assets / "primary.png", format="PNG")
    document = board_document()
    document["aspectRatio"] = size[0] / size[1]
    document["holds"] = holds
    (root / "board.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return root


def _frame(x: float, y: float, width: float, height: float) -> dict[str, float]:
    return {"x": x, "y": y, "width": width, "height": height}


def test_normalizes_opaque_near_white_canvas_from_visible_and_geometry_bounds(tmp_path: Path) -> None:
    # A geometry frame left of the visible board must expand the crop; the global one-pixel pad is exact.
    package = _write_package(
        tmp_path / "board",
        size=(100, 50),
        background=(250, 248, 245, 255),
        visible_rectangles=[(20, 10, 79, 39)],
        holds=[
            {
                **_hold(
                    "outside-visual",
                    _rounded_piece(0.10, 0.20, 0.05, 0.10),
                    _rounded_piece(0.70, 0.20, 0.05, 0.10),
                ),
                "features": ["incutEdge"],
            },
            _hold("inside-visual", _rounded_piece(0.30, 0.30, 0.10, 0.20)),
        ],
    )
    before = (package / "board.json").read_bytes()

    result = normalize_package_presentation(package, write=False)

    assert result.crop == (9, 9, 81, 41)
    assert (result.original_width, result.original_height) == (100, 50)
    assert (result.width, result.height, result.hold_count, result.changed) == (72, 32, 2, True)
    assert (package / "board.json").read_bytes() == before

    written = normalize_package_presentation(package, write=True)
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert written == result
    assert Image.open(package / "assets" / "primary.png").size == (72, 32)
    assert document["aspectRatio"] == 72 / 32
    assert document["holds"][0]["geometry"][0]["frame"] == _frame(1 / 72, 1 / 32, 5 / 72, 5 / 32)
    assert document["holds"][1]["geometry"][0]["frame"] == _frame(21 / 72, 6 / 32, 10 / 72, 10 / 32)


def test_normalizes_transparent_canvas_and_preserves_non_presentation_fields(tmp_path: Path) -> None:
    package = _write_package(
        tmp_path / "board",
        size=(100, 100),
        background=(0, 0, 0, 0),
        visible_rectangles=[(30, 20, 69, 79)],
        holds=[_hold("board", _path_piece(0.3, 0.2, 0.4, 0.6))],
    )
    before = json.loads((package / "board.json").read_text(encoding="utf-8"))

    result = normalize_package_presentation(package, write=True)
    after = json.loads((package / "board.json").read_text(encoding="utf-8"))

    assert result.crop == (29, 19, 71, 81)
    assert Image.open(package / "assets" / "primary.png").size == (42, 62)
    assert after["id"] == before["id"]
    assert after["holds"][0]["geometry"][0]["shape"] == before["holds"][0]["geometry"][0]["shape"]
    assert after["holds"][0]["geometry"][0]["frame"] == _frame(1 / 42, 1 / 62, 40 / 42, 60 / 62)


def test_leaves_an_already_tight_canvas_unchanged(tmp_path: Path) -> None:
    package = _write_package(
        tmp_path / "board",
        size=(40, 20),
        background=(250, 248, 245, 255),
        visible_rectangles=[(0, 0, 39, 19)],
        holds=[_hold("board", _rounded_piece(0, 0, 1, 1))],
    )
    before_json = (package / "board.json").read_bytes()
    before_png = (package / "assets" / "primary.png").read_bytes()

    result = normalize_package_presentation(package, write=True)

    assert result.crop == (0, 0, 40, 20)
    assert result.changed is False
    assert (package / "board.json").read_bytes() == before_json
    assert (package / "assets" / "primary.png").read_bytes() == before_png


def test_rejects_malformed_primary_image_without_writing_either_package_file(tmp_path: Path) -> None:
    package = _write_package(
        tmp_path / "board",
        size=(40, 20),
        background=(250, 248, 245, 255),
        visible_rectangles=[(5, 5, 34, 14)],
        holds=[_hold("board", _rounded_piece(0.1, 0.1, 0.8, 0.8))],
    )
    board_before = (package / "board.json").read_bytes()
    (package / "assets" / "primary.png").write_bytes(b"not a PNG")

    with pytest.raises(ValueError, match="must be a PNG image"):
        normalize_package_presentation(package, write=True)

    assert (package / "board.json").read_bytes() == board_before


def test_repeat_normalization_is_idempotent_and_cli_reports_drafts(tmp_path: Path, capsys) -> None:
    root = tmp_path / "catalog"
    package = _write_package(
        root / "board",
        size=(100, 50),
        background=(250, 248, 245, 255),
        visible_rectangles=[(20, 10, 79, 39)],
        holds=[_hold("board", _rounded_piece(0.2, 0.2, 0.6, 0.6))],
    )
    draft_assets = root / "draft" / "assets"
    draft_assets.mkdir(parents=True)
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(draft_assets / "primary.png")
    draft_before = (draft_assets / "primary.png").read_bytes()

    assert normalize_package_presentation(package, write=True).changed is True
    normalized_json = (package / "board.json").read_bytes()
    normalized_png = (package / "assets" / "primary.png").read_bytes()
    assert normalize_package_presentation(package, write=True).changed is False
    assert (package / "board.json").read_bytes() == normalized_json
    assert (package / "assets" / "primary.png").read_bytes() == normalized_png

    assert main(["normalize-presentations", "--root", str(root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert (draft_assets / "primary.png").read_bytes() == draft_before
    assert payload == {
        "boards": [{
            "changed": False,
            "crop": [0, 0, 62, 32],
            "holdCount": 1,
            "id": "fixture.board",
            "newDimensions": [62, 32],
            "originalDimensions": [62, 32],
            "path": "board",
        }],
        "draftCount": 1,
        "drafts": ["draft"],
        "write": False,
    }


def test_uses_fixed_point_padding_after_a_large_canvas_shrinks(tmp_path: Path) -> None:
    # The first crop must leave the same 1%-of-output margin that a second run observes.
    package = _write_package(
        tmp_path / "board",
        size=(1000, 500),
        background=(250, 248, 245, 255),
        visible_rectangles=[(400, 200, 599, 299)],
        holds=[_hold("board", _rounded_piece(0.4, 0.4, 0.2, 0.2))],
    )

    first = normalize_package_presentation(package, write=True)
    second = normalize_package_presentation(package, write=False)

    assert first.crop == (397, 197, 603, 303)
    assert (first.width, first.height) == (206, 106)
    assert second.crop == (0, 0, 206, 106)
    assert second.changed is False


@pytest.mark.parametrize(
    ("size", "visible_rectangle"),
    [
        ((207, 64), (4, 3, 203, 60)),
        ((123, 45), (2, 2, 119, 42)),
    ],
)
def test_keeps_a_canvas_with_one_pixel_fixed_point_margin_rounding(
    tmp_path: Path,
    size: tuple[int, int],
    visible_rectangle: tuple[int, int, int, int],
) -> None:
    # Raster bounds can move by one pixel after a crop; a canvas already at the global margin is stable.
    package = _write_package(
        tmp_path / "board",
        size=size,
        background=(250, 248, 245, 255),
        visible_rectangles=[visible_rectangle],
        holds=[_hold("board", _rounded_piece(0.2, 0.2, 0.6, 0.6))],
    )

    result = normalize_package_presentation(package, write=False)

    assert result.crop == (0, 0, *size)
    assert result.changed is False


def test_keeps_minority_edge_touching_opaque_artwork_in_visible_bounds(tmp_path: Path) -> None:
    # A dark stripe covers one quarter of the border; it must not define the background tolerance.
    package = _write_package(
        tmp_path / "board",
        size=(100, 100),
        background=(250, 248, 245, 255),
        visible_rectangles=[(90, 0, 99, 99)],
        holds=[_hold("elsewhere", _rounded_piece(0.3, 0.3, 0.1, 0.1))],
    )

    result = normalize_package_presentation(package, write=False)

    assert result.crop == (28, 0, 100, 100)


@pytest.mark.parametrize(
    "frame",
    [
        _frame(float("nan"), 0.1, 0.2, 0.2),
        _frame(0.1, 0.1, 0.0, 0.2),
        _frame(0.9, 0.1, 0.2, 0.2),
    ],
)
def test_refuses_nonfinite_nonpositive_or_outside_frames_without_writing(
    tmp_path: Path, frame: dict[str, float]
) -> None:
    package = _write_package(
        tmp_path / "board",
        size=(100, 50),
        background=(250, 248, 245, 255),
        visible_rectangles=[(20, 10, 79, 39)],
        holds=[_hold("board", _rounded_piece(0.2, 0.2, 0.6, 0.6))],
    )
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["frame"] = frame
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    before_png = (package / "assets" / "primary.png").read_bytes()

    with pytest.raises(ValueError):
        normalize_package_presentation(package, write=True)

    assert (package / "assets" / "primary.png").read_bytes() == before_png


def test_fails_closed_without_replacing_a_package_when_atomic_exchange_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _write_package(
        tmp_path / "board",
        size=(100, 50),
        background=(250, 248, 245, 255),
        visible_rectangles=[(20, 10, 79, 39)],
        holds=[_hold("board", _rounded_piece(0.2, 0.2, 0.6, 0.6))],
    )
    before_json = (package / "board.json").read_bytes()
    before_png = (package / "assets" / "primary.png").read_bytes()

    def unavailable(_: Path, __: Path) -> None:
        raise OSError("atomic directory exchange is unavailable")

    monkeypatch.setattr(board_presentation, "_atomic_directory_exchange", unavailable, raising=False)

    with pytest.raises(OSError, match="atomic directory exchange is unavailable"):
        normalize_package_presentation(package, write=True)

    assert (package / "board.json").read_bytes() == before_json
    assert (package / "assets" / "primary.png").read_bytes() == before_png


def test_candidate_validation_failure_keeps_live_files_and_skips_exchange(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _write_package(
        tmp_path / "board",
        size=(100, 50),
        background=(250, 248, 245, 255),
        visible_rectangles=[(20, 10, 79, 39)],
        holds=[_hold("board", _rounded_piece(0.2, 0.2, 0.6, 0.6))],
    )
    before_json = (package / "board.json").read_bytes()
    before_png = (package / "assets" / "primary.png").read_bytes()
    original_loader = board_presentation.load_board_package

    def reject_candidate(root: Path):
        if root.resolve() != package.resolve():
            raise ValueError("candidate package is invalid")
        return original_loader(root)

    def exchange_must_not_run(_: Path, __: Path) -> None:
        raise AssertionError("candidate validation must happen before exchange")

    monkeypatch.setattr(board_presentation, "load_board_package", reject_candidate)
    monkeypatch.setattr(board_presentation, "_atomic_directory_exchange", exchange_must_not_run)

    with pytest.raises(ValueError, match="candidate package is invalid"):
        normalize_package_presentation(package, write=True)

    assert (package / "board.json").read_bytes() == before_json
    assert (package / "assets" / "primary.png").read_bytes() == before_png


def test_cli_write_updates_completed_packages_but_not_drafts(tmp_path: Path, capsys) -> None:
    root = tmp_path / "catalog"
    package = _write_package(
        root / "board",
        size=(100, 50),
        background=(250, 248, 245, 255),
        visible_rectangles=[(20, 10, 79, 39)],
        holds=[_hold("board", _rounded_piece(0.2, 0.2, 0.6, 0.6))],
    )
    draft_assets = root / "draft" / "assets"
    draft_assets.mkdir(parents=True)
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(draft_assets / "primary.png")
    draft_before = (draft_assets / "primary.png").read_bytes()

    assert main(["normalize-presentations", "--root", str(root), "--write"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["write"] is True
    assert payload["boards"][0]["changed"] is True
    assert Image.open(package / "assets" / "primary.png").size == (62, 32)
    assert (draft_assets / "primary.png").read_bytes() == draft_before
