"""Read-only readiness checks for a promoted workbench revision."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any

from . import ios_promotion


_PLAN_LIBRARY_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    status: str
    message: str
    details: tuple[str, ...]


@dataclass(frozen=True)
class ValidationReport:
    board_id: str
    revision_id: str
    overall_status: str
    checks: tuple[ValidationCheck, ...]


def build_validation_report(
    run_root: Path,
    repository_root: Path,
    *,
    board_id: str,
    revision_id: str,
) -> ValidationReport:
    """Validate an approved package and native plan library without writing either."""
    try:
        artifacts = ios_promotion._load_approved_artifacts(run_root)
    except (OSError, ValueError) as error:
        return _failed_package_report(board_id, revision_id, error)

    readiness = ValidationCheck(
        check_id="package-readiness",
        status="passed",
        message="approved Stage 2–4 package is ready",
        details=(),
    )
    try:
        ios_promotion._merge_regions(
            artifacts["stage2"], artifacts["stage3"], artifacts["stage4"]
        )
    except (KeyError, ValueError) as error:
        parity = _failed_check("hold-id-parity", "hold ID parity failed", error)
        return _report(board_id, revision_id, (readiness, parity, _not_run()))

    parity = ValidationCheck(
        check_id="hold-id-parity",
        status="passed",
        message="Stage 2, Stage 3, and Stage 4 hold IDs agree",
        details=(),
    )
    plan_library = _plan_library_check(repository_root)
    return _report(board_id, revision_id, (readiness, parity, plan_library))


def _failed_package_report(
    board_id: str, revision_id: str, error: Exception
) -> ValidationReport:
    return _report(
        board_id,
        revision_id,
        (
            _failed_check("package-readiness", "package readiness failed", error),
            _not_run("hold-id-parity"),
            _not_run(),
        ),
    )


def _plan_library_check(repository_root: Path) -> ValidationCheck:
    script = repository_root / "scripts" / "export-plan-library.sh"
    if not script.is_file():
        return ValidationCheck(
            check_id="plan-library",
            status="failed",
            message="plan library validation script is unavailable",
            details=(),
        )
    command = [str(script), "--check"]
    try:
        completed = subprocess.run(
            command,
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PLAN_LIBRARY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ValidationCheck(
            check_id="plan-library",
            status="failed",
            message="plan library validation exceeded 30 seconds",
            details=(),
        )
    except OSError:
        return ValidationCheck(
            check_id="plan-library",
            status="failed",
            message="plan library validation could not start",
            details=(),
        )
    if completed.returncode == 0:
        return ValidationCheck(
            check_id="plan-library",
            status="passed",
            message="plan library matches source-audited definitions",
            details=(),
        )
    return ValidationCheck(
        check_id="plan-library",
        status="failed",
        message="plan library validation failed",
        details=_safe_details(completed.stdout, completed.stderr),
    )


def _report(
    board_id: str, revision_id: str, checks: tuple[ValidationCheck, ...]
) -> ValidationReport:
    overall_status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ValidationReport(board_id, revision_id, overall_status, checks)


def _failed_check(check_id: str, message: str, error: Exception) -> ValidationCheck:
    return ValidationCheck(
        check_id=check_id,
        status="failed",
        message=message,
        details=_safe_details(str(error)),
    )


def _not_run(check_id: str = "plan-library") -> ValidationCheck:
    return ValidationCheck(
        check_id=check_id,
        status="not_run",
        message="not run because an earlier validation check failed",
        details=(),
    )


def _safe_details(*values: Any) -> tuple[str, ...]:
    details: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        for line in value.splitlines():
            cleaned = line.strip()
            if cleaned and "/" not in cleaned and "\\" not in cleaned:
                details.append(cleaned)
    return tuple(details[:3])
