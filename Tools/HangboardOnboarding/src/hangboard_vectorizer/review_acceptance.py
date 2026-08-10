"""Write and validate Stage 2 review acceptance records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .review_artifacts import ReviewRun, discover_review_run, load_json, sha256_file
from .review_lint import LintReport, _atomic_write_json, lint_review, write_lint_report

_SCHEMA_VERSION = 1
_TOOL_VERSION = "hangboard-review"


@dataclass(frozen=True)
class AcceptanceRecord:
    schemaVersion: int
    decision: Literal["accepted", "rejected"]
    reviewer: str
    reviewedAt: str
    source: dict[str, str]
    toolVersion: str
    notes: str


def write_acceptance(
    run: ReviewRun,
    decision: Literal["accepted", "rejected"],
    reviewer: str,
    notes: str,
    now: datetime | None = None,
) -> Path:
    """Persist one Stage 2 acceptance decision beside the edited artifact."""
    effective_run = run
    if decision == "accepted":
        report = _ensure_current_lint_pass(run)
        if not report.passed:
            raise ValueError("lint must pass before acceptance")
        effective_run = discover_review_run(run.root)
    path = _stage2_dir(effective_run) / "stage-2-review-acceptance.json"
    payload = {
        "schemaVersion": _SCHEMA_VERSION,
        "decision": decision,
        "reviewer": reviewer,
        "reviewedAt": _utc_timestamp(now),
        "source": _source_hashes(effective_run),
        "toolVersion": _TOOL_VERSION,
        "notes": notes,
    }
    _atomic_write_json(path, payload)
    return path


def validate_acceptance(run: ReviewRun) -> AcceptanceRecord:
    """Load one persisted acceptance and verify every recorded source hash."""
    if run.acceptance is None:
        raise ValueError("review acceptance is missing")
    document = load_json(run.acceptance, "review acceptance")
    source = document.get("source")
    if not isinstance(source, dict):
        raise ValueError("review acceptance source must be a JSON object")

    _require_hash_match(source, "stage1ImageSha256", run.stage1_image, "stage 1 image hash changed")
    _require_hash_match(
        source, "baselineSha256", run.stage2_regions, "baseline artifact hash changed"
    )
    _require_optional_hash_match(
        source, "editedSha256", run.edited_regions, "edited artifact hash changed"
    )
    _require_optional_hash_match(
        source, "correctionsSha256", run.corrections, "corrections artifact hash changed"
    )
    _require_optional_hash_match(
        source, "lintReportSha256", run.lint_report, "lint report hash changed"
    )

    decision = document.get("decision")
    if decision not in {"accepted", "rejected"}:
        raise ValueError("review acceptance decision is invalid")
    reviewer = document.get("reviewer")
    reviewed_at = document.get("reviewedAt")
    tool_version = document.get("toolVersion")
    notes = document.get("notes")
    schema_version = document.get("schemaVersion")
    if not isinstance(reviewer, str) or not isinstance(reviewed_at, str):
        raise ValueError("review acceptance reviewer metadata is invalid")
    if not isinstance(tool_version, str) or not isinstance(notes, str):
        raise ValueError("review acceptance tool metadata is invalid")
    if not isinstance(schema_version, int):
        raise ValueError("review acceptance schemaVersion is invalid")

    normalized_source = {str(key): str(value) for key, value in source.items()}
    return AcceptanceRecord(
        schemaVersion=schema_version,
        decision=decision,
        reviewer=reviewer,
        reviewedAt=reviewed_at,
        source=normalized_source,
        toolVersion=tool_version,
        notes=notes,
    )


def _ensure_current_lint_pass(run: ReviewRun) -> LintReport:
    current = _load_current_lint_report(run)
    if current is not None and current.passed:
        return current
    report = lint_review(run)
    write_lint_report(run, report)
    return report


def _load_current_lint_report(run: ReviewRun) -> LintReport | None:
    if run.lint_report is None or run.edited_regions is None:
        return None
    try:
        document = load_json(run.lint_report, "lint report")
    except ValueError:
        return None
    issues = document.get("issues")
    if (
        document.get("baselineSha256") != sha256_file(run.stage2_regions)
        or document.get("editedSha256") != sha256_file(run.edited_regions)
        or not isinstance(document.get("passed"), bool)
        or not isinstance(issues, list)
    ):
        return None
    return LintReport(
        passed=bool(document["passed"]),
        issues=(),
        baseline_sha256=str(document["baselineSha256"]),
        edited_sha256=str(document["editedSha256"]),
    )


def _source_hashes(run: ReviewRun) -> dict[str, str]:
    source = {
        "stage1ImageSha256": sha256_file(run.stage1_image),
        "baselineSha256": sha256_file(run.stage2_regions),
    }
    if run.edited_regions is not None:
        source["editedSha256"] = sha256_file(run.edited_regions)
    if run.corrections is not None:
        source["correctionsSha256"] = sha256_file(run.corrections)
    if run.lint_report is not None:
        source["lintReportSha256"] = sha256_file(run.lint_report)
    return source


def _require_hash_match(
    source: dict[str, object], key: str, path: Path, message: str
) -> None:
    expected = source.get(key)
    if expected is None:
        return
    if not isinstance(expected, str) or sha256_file(path) != expected:
        raise ValueError(message)


def _require_optional_hash_match(
    source: dict[str, object], key: str, path: Path | None, message: str
) -> None:
    if key in source and path is None:
        raise ValueError(message)
    if path is not None:
        _require_hash_match(source, key, path, message)


def _stage2_dir(run: ReviewRun) -> Path:
    if run.edited_regions is None:
        raise ValueError("edited regions artifact is missing")
    stage2_dir = run.edited_regions.parent.resolve(strict=False)
    stage2_dir.relative_to(run.root)
    return stage2_dir


def _utc_timestamp(now: datetime | None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return current.isoformat().replace("+00:00", "Z")
