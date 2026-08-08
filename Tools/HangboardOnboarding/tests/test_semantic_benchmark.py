from __future__ import annotations

import json
from pathlib import Path

import pytest

from hangboard_vectorizer.semantic_benchmark import (
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
    assert report["parity"]["exact"] is True
    assert report["parity"]["stage2"]["labelsExact"] is True
    assert report["parity"]["stage2"]["regionsExact"] is True
    assert report["parity"]["stage3"]["geometryExact"] is True
    assert all(report["parity"]["stage4"]["highlightPixelsExact"].values())
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


def _accepted_run() -> Path:
    repository = Path(__file__).resolve().parents[3]
    return (
        repository
        / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii"
    )
