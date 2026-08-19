from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _boards_by_id() -> dict[str, dict[str, object]]:
    boards: dict[str, dict[str, object]] = {}
    for path in (REPOSITORY_ROOT / "Hangboards").glob("*/board.json"):
        board = json.loads(path.read_text(encoding="utf-8"))
        boards[board["id"]] = board
    return boards


def test_complete_catalog_exposes_authoritative_board_facts() -> None:
    boards = _boards_by_id()

    expected_dimensions = {
        "beastmaker-1000": "580 × 150 × 58 mm",
        "escape-unlimited": "23.5 × 6 in",
        "evolv-kilter-basic-long": "79 × 16 × 6 cm",
        "frictitious-doormount-pro-7": "25.5 × 4.5 × 2.25 in",
        "frictitious-megalith": "26.75 × 6.5 × 2.25 in",
        "metolius-contact": "32.5 × 11 × 2.625 in",
        "metolius-project": "24.5 × 6 in",
        "metolius-simulator-3d": "28 × 8.75 in",
        "moon-armstrong": "65 × 16.5 × 5.5 cm",
        "nature-stoak-board-iii": "57 × 12 × 5.5 cm",
        "tension-grindstone": "22 × 6 × 2.75 in",
        "tension-whetstone": "25 × 6 × 2 in",
        "trango-rock-prodigy-natural": "7.5 × 6 × 1.5 in (each board)",
        "yy-verticalboard-evo": "65 × 14 × 5.5 cm",
        "yy-verticalboard-first": "54 × 13 × 5 cm",
        "yy-verticalboard-light": "54 × 9 × 5 cm",
        "yy-verticalboard-one": "62 × 13 × 5.5 cm",
    }
    assert {
        board_id: boards[board_id]["dimensions"]
        for board_id in expected_dimensions
    } == expected_dimensions

    assert {
        board_id: boards[board_id]["productURL"]
        for board_id in (
            "soill-iron-palm-2",
            "soill-split-palm",
            "soill-training-tiles",
        )
    } == {
        "soill-iron-palm-2": "https://soillholds.com/products/iron-palm-2-0",
        "soill-split-palm": "https://soillholds.com/products/split-palm",
        "soill-training-tiles": "https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin",
    }


def test_complete_catalog_exposes_authoritative_frictitious_product_url() -> None:
    boards = _boards_by_id()

    assert boards["frictitious-doormount-pro-7"]["productURL"] == (
        "https://frictitiousclimbing.com/en-ca/products/doormount-pro"
    )


def test_complete_catalog_exposes_authoritative_iron_palm_name() -> None:
    boards = _boards_by_id()

    assert boards["soill-iron-palm-2"]["name"] == "Iron Palm 2.0"


def test_complete_catalog_omits_contradicted_optional_semantics() -> None:
    boards = _boards_by_id()

    assert (
        boards["escape-unlimited"]["subtitle"]
        == "Four descending finger-pad depth levels."
    )

    for board_id in (
        "yy-verticalboard-evo",
        "yy-verticalboard-first",
        "yy-verticalboard-one",
    ):
        holds = boards[board_id]["holds"]
        assert all(hold.get("gripType") != "threeFingerPocket" for hold in holds)
        assert all(hold.get("fingerCapacity") != 3 for hold in holds)

    whetstone_holds = boards["tension-whetstone"]["holds"]
    assert all(hold.get("gripType") != "fourFingerPocket" for hold in whetstone_holds)
    assert all(hold.get("fingerCapacity") != 4 for hold in whetstone_holds)

    honestone_holds = boards["tension-honestone"]["holds"]
    assert all(hold.get("fingerCapacity") != 4 for hold in honestone_holds)

    for board_id in (
        "frictitious-doormount-pro-7",
        "metolius-contact",
        "metolius-simulator-3d",
    ):
        for hold in boards[board_id]["holds"]:
            assert "gripType" not in hold
            assert "fingerCapacity" not in hold
            assert "features" not in hold
