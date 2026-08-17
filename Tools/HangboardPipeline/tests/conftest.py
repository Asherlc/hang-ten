from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src"


def load_board_catalog_module() -> ModuleType:
    """Return the real ``hangboard_vectorizer.board_catalog`` module."""
    if str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))
    from hangboard_vectorizer import board_catalog

    return board_catalog
