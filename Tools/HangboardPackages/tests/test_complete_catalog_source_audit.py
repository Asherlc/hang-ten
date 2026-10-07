from __future__ import annotations

import json
from pathlib import Path

from conftest import package_board_text, package_roots


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _boards_by_id() -> dict[str, dict[str, object]]:
    boards: dict[str, dict[str, object]] = {}
    for package_root in package_roots(REPOSITORY_ROOT / "Hangboards"):
        board = json.loads(package_board_text(package_root))
        boards[board["id"]] = board
    return boards


def test_complete_catalog_exposes_authoritative_board_facts() -> None:
    boards = _boards_by_id()

    expected_dimensions = {
        "beastmaker-1000": "580 × 150 × 58 mm",
        "escape.unlimited": "23.5 × 6 in",
        "evolv-kilter-basic-long": "79 × 16 × 6 cm",
        "frictitious.doormount-pro-7": "25.5 × 4.5 × 2.25 in",
        "frictitious.megalith": "26.75 × 6.5 × 2.25 in",
        "metolius.contact": "32.5 × 11 × 2.625 in",
        "metolius.project": "24.5 × 6 in",
        "metolius.simulator-3d": "28 × 8.75 in",
        "moon.armstrong": "65 × 16.5 × 5.5 cm",
        "nature.stoak-board-iii": "57 × 12 × 5.5 cm",
        "tension.grindstone": "22 × 6 × 2.75 in",
        "tension.whetstone": "25 × 6 × 2 in",
        "trango.rock-prodigy-natural": "7.5 × 6 × 1.5 in (each board)",
        "yy.verticalboard-evo": "65 × 14 × 5.5 cm",
        "yy.verticalboard-first": "54 × 13 × 5 cm",
        "yy.verticalboard-light": "54 × 9 × 5 cm",
        "yy.verticalboard-one": "62 × 13 × 5.5 cm",
    }
    assert {
        board_id: boards[board_id]["dimensions"]
        for board_id in expected_dimensions
    } == expected_dimensions

    assert {
        board_id: boards[board_id]["productURL"]
        for board_id in (
            "soill.iron-palm-2",
            "soill.split-palm",
            "soill.training-tiles",
        )
    } == {
        "soill.iron-palm-2": "https://soillholds.com/products/iron-palm-2-0",
        "soill.split-palm": "https://soillholds.com/products/split-palm",
        "soill.training-tiles": "https://soill.ca/products/training-tiles-so-ill-x-meagan-martin",
    }


def test_complete_catalog_exposes_authoritative_frictitious_product_url() -> None:
    boards = _boards_by_id()

    assert boards["frictitious.doormount-pro-7"]["productURL"] == (
        "https://frictitiousclimbing.com/en-ca/products/doormount-pro"
    )


def test_complete_catalog_exposes_authoritative_iron_palm_name() -> None:
    boards = _boards_by_id()

    assert boards["soill.iron-palm-2"]["name"] == "Iron Palm 2.0"


def test_complete_catalog_authors_finger_capacity_on_every_contact() -> None:
    boards = _boards_by_id()
    missing = [
        f"{board_id}/{contact['id']}"
        for board_id, board in boards.items()
        for contact in board["contacts"]
        if type(contact.get("fingerCapacity")) is not int
        or contact["fingerCapacity"] not in range(1, 5)
    ]

    assert not missing, f"Contacts without an authored capacity: {missing}"


def test_catalog_finger_capacities_match_reviewed_source_mappings() -> None:
    boards = _boards_by_id()
    audit = json.loads(
        (REPOSITORY_ROOT / "docs/source-audits/2026-10-06-finger-capacity.json").read_text()
    )
    assert audit["reviewedAt"]
    assert audit["definition"]
    mapped_contacts: set[tuple[str, str]] = set()

    for mapping in audit["boards"]:
        board = boards[mapping["boardID"]]
        assert mapping["sourceURL"].startswith("https://")
        assert mapping["nativeSource"] == f"Hangboards/{mapping['slug']}.FCStd"
        assert (REPOSITORY_ROOT / mapping["nativeSource"]).is_file()
        contacts = {contact["id"]: contact for contact in board["contacts"]}
        for record in mapping["records"]:
            assert record["basis"] in {"reviewedEstimate", "manufacturerDefinition"}
            assert record["reason"]
            assert record["contactIDs"]
            for contact_id in record["contactIDs"]:
                identity = (mapping["boardID"], contact_id)
                assert identity not in mapped_contacts, f"Duplicate capacity mapping: {identity}"
                mapped_contacts.add(identity)
                assert contacts[contact_id]["fingerCapacity"] == record["fingerCapacity"], identity

    # This dated audit covers the 626 counts introduced by the catalog backfill.
    assert len(mapped_contacts) == 626


def test_complete_catalog_omits_contradicted_optional_semantics() -> None:
    boards = _boards_by_id()

    assert (
        boards["escape.unlimited"]["subtitle"]
        == "Premium Baltic Birch hangboard with a continuous top sloper and three mirrored edge rows."
    )

    for board_id in (
        "yy.verticalboard-evo",
        "yy.verticalboard-first",
        "yy.verticalboard-one",
    ):
        contacts = boards[board_id]["contacts"]
        assert all("threeFingerPocket" not in contact["gripTypes"] for contact in contacts)
        assert all(contact.get("fingerCapacity") != 3 for contact in contacts)

    whetstone_contacts = boards["tension.whetstone"]["contacts"]
    assert all("fourFingerPocket" not in contact["gripTypes"] for contact in whetstone_contacts)
    assert all(contact["fingerCapacity"] == 2 for contact in whetstone_contacts if contact["kind"] == "pocket")

    honestone_contacts = boards["tension.honestone"]["contacts"]
    assert all(contact["fingerCapacity"] == 1 for contact in honestone_contacts if contact["kind"] == "pocket")
