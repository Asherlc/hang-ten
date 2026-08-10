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


def test_cache_only_benchmark_refuses_unmeasured_token_reduction_and_proves_parity(
    tmp_path: Path,
) -> None:
    accepted = _accepted_run()
    report_path = tmp_path / "report.json"

    report = build_metolius_benchmark_report(
        accepted,
        report_path,
        workspace_root=tmp_path,
        cache_root=tmp_path / "cache",
    )

    assert report["model"]["cacheReplay"] == {
        "cacheHit": True,
        "calls": 0,
        "inputTokens": 0,
        "outputTokens": 0,
        "retries": 0,
        "totalTokens": 0,
        "wallMilliseconds": 0,
    }
    assert report["model"]["historicalBaseline"]["totalTokens"] is None
    assert report["model"]["percentageTokenReduction"] is None
    assert "not measured" in report["model"]["percentageTokenReductionReason"]
    assert report["localProcessing"]["wallMilliseconds"] >= 0
    assert report["parity"]["exact"] is True, repr(report["parity"])
    assert report["parity"]["stage2"]["labelsExact"] is True
    assert report["parity"]["stage2"]["regionsExact"] is True
    assert report["parity"]["stage3"]["geometryExact"] is True
    highlight_exact = report["parity"]["stage4"]["highlightPixelsExact"]
    highlight_equivalent = report["parity"]["stage4"]["highlightPixelsEquivalent"]
    assert all(isinstance(value, bool) for value in highlight_exact.values())
    assert all(highlight_equivalent.values())
    highlight_diffs = report["parity"]["stage4"]["highlightPixelDiffs"]
    assert highlight_diffs
    assert all(
        set(diff) == {"differingPixelCount", "maxAbsChannelDifference"}
        for diff in highlight_diffs.values()
    )
    assert all(
        isinstance(diff["differingPixelCount"], int)
        and diff["differingPixelCount"] >= 0
        and isinstance(diff["maxAbsChannelDifference"], int)
        and diff["maxAbsChannelDifference"] >= 0
        for diff in highlight_diffs.values()
    )
    assert report["nonTokenByteProxy"]["compactResponseBytes"] < report["nonTokenByteProxy"]["fullProposalBytes"]
    assert "not token" in report["nonTokenByteProxy"]["label"].lower()


def test_benchmark_cli_writes_canonical_sorted_report(tmp_path: Path) -> None:
    accepted = _accepted_run()
    report_path = tmp_path / "cli-report.json"

    assert main([
        "--accepted-run", str(accepted),
        "--output", str(report_path),
        "--cache-dir", str(tmp_path / "cli-cache"),
        "--workspace-root", str(tmp_path),
    ]) == 0

    document = json.loads(report_path.read_text())
    assert document["parity"]["exact"] is True
    assert document["model"]["cacheReplay"]["calls"] == 0
    assert report_path.read_bytes() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    ).encode()


def test_benchmark_cli_rejects_outputs_outside_workspace_root(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "escaped-report.json"

    with pytest.raises(ValueError, match="must stay inside workspace root"):
        main([
            "--accepted-run", str(_accepted_run()),
            "--output", str(outside),
            "--workspace-root", str(tmp_path),
        ])

    assert not outside.exists()


def test_benchmark_cli_includes_parity_report_when_replay_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parity = {
        "exact": False,
        "stage4": {
            "highlightPixelDiffs": {"all": {"differingPixelCount": 3}},
            "highlightPixelsEquivalent": {"all": False},
        },
    }
    monkeypatch.setattr(
        "hangboard_vectorizer.semantic_benchmark.build_metolius_benchmark_report",
        lambda *_args, **_kwargs: {"parity": parity},
    )

    with pytest.raises(SystemExit, match="semantic replay parity failed") as error:
        main([
            "--accepted-run", str(_accepted_run()),
            "--output", str(tmp_path / "failed-report.json"),
            "--workspace-root", str(tmp_path),
        ])

    assert json.dumps(parity, sort_keys=True, separators=(",", ":")) in str(error.value)


def test_highlight_pixels_equivalent_accepts_small_rgba_deltas() -> None:
    accepted = _rgba(
        [[10, 20, 30, 255], [40, 50, 60, 128]],
        [[70, 80, 90, 255], [100, 110, 120, 0]],
    )
    replayed = _rgba(
        [[11, 20, 29, 254], [40, 51, 60, 128]],
        [[70, 80, 90, 255], [100, 110, 120, 0]],
    )

    assert HIGHLIGHT_PIXEL_EQUIVALENCE_MAX_CHANGED_PIXELS <= 32
    assert _highlight_pixels_equivalent(accepted, replayed) is True


def test_highlight_pixels_equivalent_rejects_larger_alpha_delta() -> None:
    accepted = _rgba([[10, 20, 30, 255]])
    replayed = _rgba([[10, 20, 30, 252]])

    assert _highlight_pixels_equivalent(accepted, replayed) is False


def test_highlight_pixels_equivalent_rejects_when_too_many_pixels_change() -> None:
    changed_pixels = HIGHLIGHT_PIXEL_EQUIVALENCE_MAX_CHANGED_PIXELS + 1
    accepted = _rgba(*([[10, 20, 30, 255]] * changed_pixels))
    replayed = _rgba(*([[11, 20, 30, 255]] * changed_pixels))

    assert _highlight_pixels_equivalent(accepted, replayed) is False


def _accepted_run() -> Path:
    repository = Path(__file__).resolve().parents[3]
    return (
        repository
        / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii"
    )


def _rgba(*rows: list[int]) -> np.ndarray:
    return np.asarray(rows, dtype=np.uint8)
