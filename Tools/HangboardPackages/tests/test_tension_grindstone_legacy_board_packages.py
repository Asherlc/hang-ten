from __future__ import annotations

from pathlib import Path

from hangboard_packages.board_catalog import load_board_package


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_tension_grindstone_catalog_preserves_mk2_and_adds_both_legacy_models() -> None:
    packages = {
        slug: load_board_package(REPOSITORY_ROOT / "Hangboards" / slug).board
        for slug in (
            "tension-grindstone",
            "tension-grindstone-original",
            "tension-grindstone-pro",
        )
    }

    assert packages["tension-grindstone"].id == "tension.grindstone"
    assert packages["tension-grindstone"].name == "Grindstone Mk2"
    assert packages["tension-grindstone-original"].id == "tension.grindstone-original"
    assert packages["tension-grindstone-original"].name == "Grindstone"
    assert packages["tension-grindstone-pro"].id == "tension.grindstone-pro"
    assert packages["tension-grindstone-pro"].name == "Grindstone Pro"

    for board in packages.values():
        assert board.presentation_asset_path == "assets/primary.png"
        assert board.holds

    assert len(packages["tension-grindstone-original"].holds) == 12
    assert len(packages["tension-grindstone-pro"].holds) == 16
