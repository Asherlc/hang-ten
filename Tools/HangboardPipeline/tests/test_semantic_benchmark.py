from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from hangboard_vectorizer.semantic_benchmark import (
    HIGHLIGHT_PIXEL_EQUIVALENCE_MAX_CHANGED_PIXELS,
    _highlight_pixels_equivalent,
    build_metolius_benchmark_report,
    main,
)


PACKAGE = Path(__file__).resolve().parents[3] / "Hangboards" / "metolius-wood-grips-compact-ii"


def test_canonical_package_benchmark_proves_semantic_and_artwork_parity(tmp_path: Path) -> None:
    report = build_metolius_benchmark_report(
        PACKAGE, tmp_path / "report.json", workspace_root=tmp_path
    )
    assert report["boardId"] == "metolius.wood-grips-compact-ii"
    assert report["parity"]["exact"] is True
    assert report["parity"]["semantics"]["exact"] is True
    assert report["parity"]["artwork"]["exact"] is True
    assert len(report["packageSha256"]) == 64


def test_benchmark_cli_writes_canonical_sorted_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert main(["--package", str(PACKAGE), "--output", str(output), "--workspace-root", str(tmp_path)]) == 0
    document = json.loads(output.read_text())
    assert output.read_text() == json.dumps(document, indent=2, sort_keys=True) + "\n"


def test_benchmark_cli_rejects_outputs_outside_workspace_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must stay inside workspace root"):
        main(["--package", str(PACKAGE), "--output", str(tmp_path.parent / "escaped.json"), "--workspace-root", str(tmp_path)])


def test_highlight_pixels_equivalent_accepts_small_rgba_deltas() -> None:
    accepted = np.asarray([[[10, 20, 30, 255]]], dtype=np.uint8)
    replayed = np.asarray([[[11, 20, 29, 254]]], dtype=np.uint8)
    assert HIGHLIGHT_PIXEL_EQUIVALENCE_MAX_CHANGED_PIXELS <= 32
    assert _highlight_pixels_equivalent(accepted, replayed)


def test_highlight_pixels_equivalent_rejects_larger_alpha_delta() -> None:
    accepted = np.asarray([[[10, 20, 30, 255]]], dtype=np.uint8)
    replayed = np.asarray([[[10, 20, 30, 252]]], dtype=np.uint8)
    assert not _highlight_pixels_equivalent(accepted, replayed)
