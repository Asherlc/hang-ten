from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from conftest import board_document  # noqa: E402
from hangboard_vectorizer.board_shape_change_audit import (
    audit_board_documents,  # noqa: E402
)
from test_board_path_simplification import _hold, _rounded_rect_path  # noqa: E402


def _documents() -> tuple[dict[str, object], dict[str, object]]:
    before = board_document()
    before["holds"] = [_hold("rounded", _rounded_rect_path(0.2))]
    after = copy.deepcopy(before)
    after["holds"][0]["geometry"][0]["shape"] = {
        "type": "roundedRect",
        "cornerRadiusFraction": 0.2,
    }
    return before, after


def test_independent_audit_reports_exact_shape_only_reduction_metrics() -> None:
    before, after = _documents()

    report = audit_board_documents(before, after, width=40, height=20)

    assert report == {
        "boardId": "fixture.board",
        "holdCount": 1,
        "pieceCount": 1,
        "changedPieces": [
            {
                "holdId": "rounded",
                "pieceIndex": 0,
                "beforeType": "path",
                "afterType": "roundedRect",
                "beforeEditablePoints": 13,
                "afterEditablePoints": 0,
                "maximumBoundaryDeviationPixels": 0.0,
                "symmetricDifferenceRatio": 0.0,
            }
        ],
    }


def test_independent_audit_rejects_non_shape_changes() -> None:
    before, after = _documents()
    after["holds"][0]["name"] = "silently changed"

    with pytest.raises(ValueError, match="non-shape fields changed"):
        audit_board_documents(before, after, width=40, height=20)


def test_independent_audit_rejects_an_over_limit_primitive() -> None:
    before, after = _documents()
    before["holds"][0]["geometry"][0]["shape"] = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0, 0]},
            {"command": "line", "to": [1, 0]},
            {"command": "line", "to": [1, 1]},
            {"command": "line", "to": [0.54, 1]},
            {"command": "line", "to": [0.5, 0.945]},
            {"command": "line", "to": [0.46, 1]},
            {"command": "line", "to": [0, 1]},
            {"command": "close"},
        ],
    }
    after["holds"][0]["geometry"][0]["shape"] = {
        "type": "roundedRect",
        "cornerRadiusFraction": 0.0,
    }

    with pytest.raises(ValueError, match="exact boundary"):
        audit_board_documents(before, after, width=40, height=20)
