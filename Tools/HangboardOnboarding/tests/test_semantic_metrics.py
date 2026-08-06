from __future__ import annotations

import pytest

from hangboard_vectorizer.semantic_metrics import (
    LocalProcessingMetrics,
    ModelProcessingMetrics,
    SemanticRunMetrics,
    UnmeasuredBaselineTokensError,
    benchmark_semantic_runs,
)


def test_benchmark_reports_median_worst_cache_and_escalation_arithmetic() -> None:
    baseline = (
        _run(100, local_ms=300),
        _run(120, local_ms=280),
        _run(140, local_ms=320),
    )
    optimized = (
        _run(40, local_ms=500),
        _run(0, local_ms=510, cache_hit=True),
        _run(60, local_ms=490, escalation_count=1),
    )

    summary = benchmark_semantic_runs(baseline, optimized)

    assert summary.baseline_median_tokens == 120
    assert summary.baseline_worst_tokens == 140
    assert summary.optimized_median_tokens == 40
    assert summary.optimized_worst_tokens == 60
    assert summary.cache_hit_model_tokens == 0
    assert summary.cache_hit_rate == pytest.approx(1 / 3)
    assert summary.escalation_frequency == pytest.approx(1 / 3)
    assert summary.percentage_reduction == pytest.approx(66.6666666667)
    assert summary.optimized_local_median_milliseconds == 500


def test_benchmark_refuses_percentage_reduction_for_unmeasured_baseline_tokens() -> None:
    baseline = (_run(None, local_ms=300),)
    optimized = (_run(40, local_ms=500),)

    summary = benchmark_semantic_runs(baseline, optimized)

    assert summary.baseline_median_tokens is None
    with pytest.raises(UnmeasuredBaselineTokensError, match="baseline"):
        _ = summary.percentage_reduction


def test_cache_usage_is_measured_per_request_not_per_mixed_escalation_run() -> None:
    baseline = (_run(100, local_ms=300),)
    mixed = SemanticRunMetrics(
        model=(
            ModelProcessingMetrics(
                provider_id="fixture-provider",
                model_id="fixture-model-v1",
                request_kind="full-board",
                model_calls=0,
                total_tokens=0,
                wall_milliseconds=0,
                cache_hit=True,
            ),
            ModelProcessingMetrics(
                provider_id="fixture-provider",
                model_id="fixture-strong-v1",
                request_kind="region-escalation",
                model_calls=1,
                total_tokens=30,
                wall_milliseconds=20,
                cache_hit=False,
            ),
        ),
        local=LocalProcessingMetrics("deterministic-refinement", 500),
        escalation_count=1,
    )

    summary = benchmark_semantic_runs(baseline, (mixed,))

    assert summary.optimized_median_tokens == 30
    assert summary.cache_hit_model_tokens == 0
    assert summary.cache_hit_rate == 0.5


def _run(
    tokens: int | None,
    *,
    local_ms: int,
    cache_hit: bool = False,
    escalation_count: int = 0,
) -> SemanticRunMetrics:
    return SemanticRunMetrics(
        model=(ModelProcessingMetrics(
            provider_id="fixture-provider",
            model_id="fixture-model-v1",
            request_kind="full-board",
            model_calls=0 if cache_hit else 1,
            total_tokens=tokens,
            wall_milliseconds=0 if cache_hit else 20,
            cache_hit=cache_hit,
        ),),
        local=LocalProcessingMetrics(
            operation="deterministic-refinement",
            wall_milliseconds=local_ms,
        ),
        escalation_count=escalation_count,
    )
