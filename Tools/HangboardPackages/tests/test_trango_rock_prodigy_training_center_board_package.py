from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BOARD_PATH = (
    REPO_ROOT
    / "Hangboards"
    / "trango-rock-prodigy-training-center"
    / "board.json"
)

# These digests freeze the exact manually authored two-piece geometry that was
# visually reconciled in the source audit. Keeping the expected values outside
# board.json makes a dropped or substituted piece observable.
EXPECTED_WIDE_GEOMETRY_SHA256 = {
    "pinch-wide-left": "b9d0056a1634332609ddb3209506ac3039b3bdd74b232bce0a64f410cbeadf58",
    "pinch-wide-right": "5215928dcca54dd880353fa7f6199b92896292518278a567afd61d01b31b945d",
}


def _geometry_digest(geometry: object) -> str:
    canonical = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def test_training_center_preserves_audited_compound_contact_geometry() -> None:
    board = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert len(board["holds"]) == 24
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 28
    assert {
        hold_id: len(hold["geometry"])
        for hold_id, hold in holds.items()
        if len(hold["geometry"]) > 1
    } == {
        "pinch-medium-left": 2,
        "pinch-medium-right": 2,
        "pinch-wide-left": 2,
        "pinch-wide-right": 2,
    }
    assert {
        hold_id: _geometry_digest(holds[hold_id]["geometry"])
        for hold_id in EXPECTED_WIDE_GEOMETRY_SHA256
    } == EXPECTED_WIDE_GEOMETRY_SHA256
