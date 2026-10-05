"""A configuration exports its own native tree and effective grip depth."""
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compile_board


def configured_board():
    return {
        "contacts": [{"id": "edge-18", "depth": {"range": {"minimum": 18, "maximum": 18}}}],
        "presentations": [
            {"id": f"depth-{depth}mm", "media": {
                "type": "model", "assetPath": f"assets/depth-{depth}.usdz",
                "descriptorPath": f"assets/depth-{depth}.model.json"}}
            for depth in (18, 15, 10)
        ],
        "positions": [
            {"id": f"depth-{depth}mm", "presentationID": f"depth-{depth}mm",
             "contactIDs": ["edge-18"], "effectiveDepths": {
                 "edge-18": {"range": {"minimum": depth, "maximum": depth}}}}
            for depth in (18, 15, 10)
        ],
    }


def test_configuration_depth_guard_checks_blocked_depth():
    assert compile_board._declared_depths(configured_board(), 1, "depth-10mm") == {"edge-18": 10.0}


def test_conflicting_configured_depths_fail_closed():
    board = configured_board()
    board["positions"].append({
        "id": "conflict", "presentationID": "depth-10mm", "contactIDs": ["edge-18"],
        "effectiveDepths": {"edge-18": {"range": {"minimum": 11, "maximum": 11}}},
    })
    with pytest.raises(compile_board.BuildError, match="conflicting"):
        compile_board._declared_depths(board, 1, "depth-10mm")


def test_node_selection_preserves_legacy_default_and_isolates_configurations():
    legacy = SimpleNamespace(PropertiesList=["NodeID"], NodeID="body")
    configured = SimpleNamespace(PropertiesList=["NodeID", "HangTenPresentationID"],
                                 NodeID="body", HangTenPresentationID="depth-10mm")
    document = SimpleNamespace(Objects=[legacy, configured], HangTenPresentationID="depth-18mm")
    assert compile_board._bound_objects(document, "depth-18mm") == [legacy]
    assert compile_board._bound_objects(document, "depth-10mm") == [configured]


def test_presentation_output_paths_are_declared_and_cannot_escape_assets():
    from presentation_targets import model_targets
    targets = model_targets(configured_board())
    assert targets["depth-10mm"] == ("depth-10.usdz", "depth-10.model.json")
    board = configured_board()
    board["presentations"][0]["media"]["assetPath"] = "assets/../escape.usdz"
    with pytest.raises(ValueError, match="assets"):
        model_targets(board)


@pytest.mark.parametrize("value", ["assets//board.usdz", "assets/./board.usdz", "assets/board\\name.usdz"])
def test_output_paths_cannot_be_normalized_to_another_spelling(value):
    from presentation_targets import model_targets
    board = configured_board()
    board["presentations"][0]["media"]["assetPath"] = value
    with pytest.raises(ValueError):
        model_targets(board)


def test_two_native_presentations_cannot_overwrite_one_output():
    from presentation_targets import model_targets
    board = configured_board()
    board["presentations"][1]["media"]["assetPath"] = board["presentations"][0]["media"]["assetPath"]
    with pytest.raises(ValueError, match="unique"):
        model_targets(board)
