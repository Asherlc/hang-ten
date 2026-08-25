"""Migrate all checked-in board packages to the unversioned presentation shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPOSITORY_ROOT / "Hangboards"


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    """Return a board document using the one unversioned presentation shape."""
    document.pop("schemaVersion", None)
    document.pop("presentation", None)

    if "presentations" not in document:
        document["presentations"] = [
            {
                "id": "primary",
                "name": "Primary",
                "assetPath": "assets/primary.png",
                "aspectRatio": document["aspectRatio"],
                "default": True,
            }
        ]

    for hold in document["holds"]:
        hold.setdefault("presentationID", "primary")

    return document


def main() -> None:
    for board_path in sorted(HANGBOARDS_ROOT.glob("*/board.json")):
        document = json.loads(board_path.read_text(encoding="utf-8"))
        board_path.write_text(
            json.dumps(migrate(document), indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
