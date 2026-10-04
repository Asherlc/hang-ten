"""Configured depths describe one contact, with no duplicated cavity IDs."""
from copy import deepcopy
import pytest
from conftest import board_document, load_board_catalog_module


def document():
    value = board_document()
    contact = value["contacts"][0]
    contact["depth"] = {"range": {"minimum": 18, "maximum": 18}}
    value["positions"] = [{"id": "front", "presentationID": value["presentations"][0]["id"],
                           "contactIDs": [contact["id"]],
                           "effectiveDepths": {contact["id"]: {"range": {"minimum": 10, "maximum": 10}}}}]
    return value


def test_position_exposes_effective_depth_without_changing_contact_identity():
    module = load_board_catalog_module()
    board = module._load_board(document())
    contact = board.contacts[0]
    assert contact.depth.range.minimum == 18
    assert board.positions[0].effective_depths[contact.id].range.minimum == 10


@pytest.mark.parametrize("bad", [None, {}, {"missing": {"range": {"minimum": 10, "maximum": 10}}},
    {"hold-left": {"range": {"minimum": 19, "maximum": 19}}},
    {"hold-left": {"range": {"minimum": 8, "maximum": 10}}},
    {"hold-left": {"category": "small"}}])
def test_invalid_effective_depths_fail_closed(bad):
    value = document()
    value["positions"][0]["effectiveDepths"] = bad
    with pytest.raises(ValueError, match="effectiveDepths"):
        load_board_catalog_module()._load_board(value)


def test_every_position_showing_a_configured_contact_must_declare_its_depth():
    value = document()
    other = deepcopy(value["positions"][0])
    other["id"] = "unconfigured"
    del other["effectiveDepths"]
    value["positions"].append(other)
    with pytest.raises(ValueError, match="effectiveDepths"):
        load_board_catalog_module()._load_board(value)
