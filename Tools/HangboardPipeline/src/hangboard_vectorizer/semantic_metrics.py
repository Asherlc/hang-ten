"""Honest runtime telemetry and benchmark arithmetic for semantic refinement."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


class UnmeasuredBaselineTokensError(ValueError):
    """A token reduction cannot be claimed without measured baseline tokens."""


def _nonnegative(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class ModelProcessingMetrics:
    """Only provider/model activity; deterministic local work is excluded."""

    provider_id: str
    model_id: str
    request_kind: str
    model_calls: int
    total_tokens: int | None
    wall_milliseconds: int
    cache_hit: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id or not self.model_id or not self.request_kind:
            raise ValueError("model processing identity fields are required")
        _nonnegative(self.model_calls, name="model calls")
        _nonnegative(self.wall_milliseconds, name="model wall milliseconds")
        if self.total_tokens is not None:
            _nonnegative(self.total_tokens, name="model tokens")
        if self.cache_hit and self.model_calls != 0:
            raise ValueError("a cache hit cannot report a model call")
        if self.model_calls == 0 and self.total_tokens not in (0, None):
            raise ValueError("zero model calls cannot consume model tokens")


@dataclass(frozen=True, slots=True)
class LocalProcessingMetrics:
    """Deterministic CPU processing, intentionally separate from model usage."""

    operation: str
    wall_milliseconds: int

    def __post_init__(self) -> None:
        if not self.operation:
            raise ValueError("local processing operation is required")
        _nonnegative(self.wall_milliseconds, name="local wall milliseconds")


@dataclass(frozen=True, slots=True)
class SemanticRunMetrics:
    model: tuple[ModelProcessingMetrics, ...]
    local: LocalProcessingMetrics
    escalation_count: int = 0

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("semantic run metrics require model/cache telemetry")
        if any(type(value) is not ModelProcessingMetrics for value in self.model):
            raise ValueError("semantic run model telemetry is not typed")
        if type(self.local) is not LocalProcessingMetrics:
            raise ValueError("semantic run local telemetry is not typed")
        _nonnegative(self.escalation_count, name="escalation count")

    @property
    def total_model_tokens(self) -> int | None:
        if any(value.model_calls and value.total_tokens is None for value in self.model):
            return None
        return sum(value.total_tokens or 0 for value in self.model)

    @property
    def cache_hit(self) -> bool:
        return any(value.cache_hit for value in self.model)


@dataclass(frozen=True, slots=True)
class SemanticBenchmarkSummary:
    baseline_median_tokens: float | None
    baseline_worst_tokens: int | None
    optimized_median_tokens: float | None
    optimized_worst_tokens: int | None
    cache_hit_model_tokens: float | None
    cache_hit_rate: float
    escalation_frequency: float
    optimized_local_median_milliseconds: float

    @property
    def percentage_reduction(self) -> float:
        baseline = self.baseline_median_tokens
        if baseline is None:
            raise UnmeasuredBaselineTokensError(
                "percentage reduction requires measured baseline model tokens"
            )
        if baseline <= 0:
            raise UnmeasuredBaselineTokensError(
                "percentage reduction requires a positive measured baseline"
            )
        optimized = self.optimized_median_tokens
        if optimized is None:
            raise ValueError("percentage reduction requires measured optimized model tokens")
        return (baseline - optimized) * 100.0 / baseline


def benchmark_semantic_runs(
    baseline: tuple[SemanticRunMetrics, ...],
    optimized: tuple[SemanticRunMetrics, ...],
) -> SemanticBenchmarkSummary:
    """Summarize model tokens without treating local time as model usage."""
    if not baseline or not optimized:
        raise ValueError("semantic benchmark requires baseline and optimized runs")
    if any(type(run) is not SemanticRunMetrics for run in (*baseline, *optimized)):
        raise ValueError("semantic benchmark runs must use typed telemetry")
    baseline_median, baseline_worst = _token_summary(baseline)
    optimized_median, optimized_worst = _token_summary(optimized)
    optimized_requests = tuple(metric for run in optimized for metric in run.model)
    cache_hits = tuple(metric for metric in optimized_requests if metric.cache_hit)
    hit_median = (
        float(median(metric.total_tokens or 0 for metric in cache_hits))
        if cache_hits else None
    )
    return SemanticBenchmarkSummary(
        baseline_median_tokens=baseline_median,
        baseline_worst_tokens=baseline_worst,
        optimized_median_tokens=optimized_median,
        optimized_worst_tokens=optimized_worst,
        cache_hit_model_tokens=hit_median,
        cache_hit_rate=len(cache_hits) / len(optimized_requests),
        escalation_frequency=sum(run.escalation_count for run in optimized) / len(optimized),
        optimized_local_median_milliseconds=float(median(
            run.local.wall_milliseconds for run in optimized
        )),
    )


def _token_summary(
    runs: tuple[SemanticRunMetrics, ...],
) -> tuple[float | None, int | None]:
    tokens = tuple(run.total_model_tokens for run in runs)
    if any(value is None for value in tokens):
        return None, None
    measured = tuple(int(value) for value in tokens if value is not None)
    return float(median(measured)), max(measured)
