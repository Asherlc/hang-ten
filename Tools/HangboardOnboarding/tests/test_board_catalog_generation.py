from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "Hangboards" / "catalog.json"
BOARD_PATH = REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii" / "board.json"
COMPACT_II_HOLD_IDS = [
    "jug-left",
    "jug-right",
    "sloper-flat-left",
    "sloper-flat-right",
    "sloper-round-center",
    "edge-29-left",
    "edge-29-right",
    "pocket-29-three-left",
    "pocket-29-three-right",
    "pocket-29-two-left",
    "pocket-29-two-right",
    "pocket-29-four-center",
    "edge-19-left",
    "edge-19-right",
    "pocket-19-three-left",
    "pocket-19-three-right",
    "pocket-19-two-left",
    "pocket-19-two-right",
    "pocket-19-four-center",
]


def load_module():
    module_path = (
        REPO_ROOT
        / "Tools"
        / "HangboardOnboarding"
        / "src"
        / "hangboard_vectorizer"
        / "board_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("board_catalog_under_test", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise AssertionError("unable to load hangboard_vectorizer.board_catalog")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_render_swift_catalog_contains_compact_ii_and_all_stable_hold_ids() -> None:
    module = load_module()
    board = module.load_board(BOARD_PATH)

    rendered = module.render_swift_catalog(board)

    assert 'id: "metolius.wood-grips-compact-ii"' in rendered
    assert rendered.count("BoardHold(") == 19
    for hold_id in COMPACT_II_HOLD_IDS:
        assert f'id: "{hold_id}"' in rendered


def test_render_swift_catalog_uses_swift_defaults_for_pocket_features() -> None:
    module = load_module()
    board = module.load_board(BOARD_PATH)

    rendered = module.render_swift_catalog(board)
    pocket_block = next(
        block for block in rendered.split("            BoardHold(")
        if 'id: "pocket-29-three-left"' in block
    )

    assert "features:" not in pocket_block


def test_export_swift_catalog_check_detects_drift(tmp_path: Path) -> None:
    module = load_module()
    output_path = tmp_path / "GeneratedBoardCatalog.swift"

    module.export_swift_catalog(CATALOG_PATH, output_path)
    output_path.write_text(output_path.read_text(encoding="utf-8") + "\n// drift\n", encoding="utf-8")

    with pytest.raises(ValueError, match="drift"):
        module.export_swift_catalog(CATALOG_PATH, output_path, check=True)
