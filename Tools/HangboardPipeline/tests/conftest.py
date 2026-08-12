from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_board_catalog_module():
    module_path = REPO_ROOT / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer" / "board_catalog.py"
    spec = importlib.util.spec_from_file_location("board_catalog_under_test", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise AssertionError("unable to load hangboard_vectorizer.board_catalog")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
