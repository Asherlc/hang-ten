"""Run deterministic repository-facing release checks for reviewed boards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

from .review_acceptance import validate_acceptance
from .review_artifacts import ReviewRun, load_json, sha256_file
from .review_lint import _atomic_write_json

_PASSING_PROMOTION_STATUSES = frozenset({"ready", "applied"})
_UUID_LENGTHS = {36}


@dataclass(frozen=True)
class ReleaseCheckResult:
    name: str
    passed: bool
    command: tuple[str, ...]
    output: str
    error: str | None


def run_release_check(
    run: ReviewRun, repository_root: Path, *, run_xcode: bool = False
) -> tuple[ReleaseCheckResult, ...]:
    """Collect every deterministic release check and persist one report."""
    repository_root = repository_root.resolve(strict=False)
    if not repository_root.is_dir():
        raise ValueError(f"repository root must be a directory: {repository_root}")

    promotion_dir = run.stage2_regions.parent / "promotion"
    promotion_dir.mkdir(parents=True, exist_ok=True)

    results: list[ReleaseCheckResult] = []
    results.append(_check_promotion_status(run))
    results.append(_check_acceptance_current(run))
    results.append(_check_promotion_input_hashes(run))
    results.append(_check_promotion_output_hashes(run, repository_root))
    results.append(_check_runtime_integration(run))
    results.append(_check_generated_artifacts_clean(run, repository_root))
    results.append(_run_export_plan_library(repository_root))
    if run_xcode:
        results.append(_run_xcode_tests(run, repository_root))

    _atomic_write_json(promotion_dir / "release-check.json", release_check_report(tuple(results)))
    return tuple(results)


def release_check_report(results: tuple[ReleaseCheckResult, ...]) -> dict[str, object]:
    """Return a JSON-safe machine report for one release-check run."""
    return {
        "passed": all(result.passed for result in results),
        "checks": [
            {
                "name": result.name,
                "passed": result.passed,
                "command": list(result.command),
                "output": result.output,
                "error": result.error,
            }
            for result in results
        ],
        "generatedAt": _utc_now(),
    }


def release_check_blockers(results: tuple[ReleaseCheckResult, ...]) -> list[dict[str, str]]:
    """Return machine-readable blockers and remediations for failing checks."""
    blockers: list[dict[str, str]] = []
    for result in results:
        if result.passed:
            continue
        blockers.append(
            {
                "check": result.name,
                "reason": result.error or result.output or "check failed",
                "remediation": _remediation_for(result.name),
            }
        )
    return blockers


def _check_promotion_status(run: ReviewRun) -> ReleaseCheckResult:
    command = ("promotion-report",)
    report = _promotion_report_document(run)
    if report is None:
        return _failed(command, "promotion-status", "promotion report is missing")

    status = report.get("status")
    if status not in _PASSING_PROMOTION_STATUSES:
        return _failed(
            command,
            "promotion-status",
            f"promotion report status must be ready or applied; found {status!r}",
        )
    warnings = _string_list(report.get("warnings"))
    if warnings:
        return _failed(
            command,
            "promotion-status",
            "promotion report contains warnings: " + "; ".join(warnings),
        )
    errors = _string_list(report.get("errors"))
    if errors:
        return _failed(
            command,
            "promotion-status",
            "promotion report contains errors: " + "; ".join(errors),
        )
    return ReleaseCheckResult(
        name="promotion-status",
        passed=True,
        command=command,
        output=f"promotion status {status}",
        error=None,
    )


def _check_acceptance_current(run: ReviewRun) -> ReleaseCheckResult:
    command = ("hangboard-review", "accept", "--decision", "accepted")
    try:
        record = validate_acceptance(run)
    except ValueError as error:
        return _failed(command, "acceptance-current", _first_line(error))
    if record.decision != "accepted":
        return _failed(
            command, "acceptance-current", f"review acceptance decision must be accepted; found {record.decision!r}"
        )
    return ReleaseCheckResult(
        name="acceptance-current",
        passed=True,
        command=command,
        output="review acceptance is current",
        error=None,
    )


def _check_promotion_input_hashes(run: ReviewRun) -> ReleaseCheckResult:
    command = ("promotion-report", "input-hashes")
    report = _promotion_report_document(run)
    if report is None:
        return _failed(command, "promotion-input-hashes", "promotion report is missing")
    input_hashes = report.get("inputHashes")
    if not isinstance(input_hashes, dict):
        return _failed(
            command, "promotion-input-hashes", "promotion report inputHashes must be a JSON object"
        )

    expected = _current_input_hashes(run)
    missing = sorted(key for key in expected if input_hashes.get(key) != expected[key])
    extra = sorted(key for key in input_hashes if key not in expected)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("mismatched or missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        return _failed(command, "promotion-input-hashes", "promotion input hashes changed; " + "; ".join(details))
    return ReleaseCheckResult(
        name="promotion-input-hashes",
        passed=True,
        command=command,
        output="promotion input hashes are current",
        error=None,
    )


def _check_promotion_output_hashes(
    run: ReviewRun, repository_root: Path
) -> ReleaseCheckResult:
    command = ("promotion-report", "output-hashes")
    report = _promotion_report_document(run)
    if report is None:
        return _failed(command, "promotion-output-hashes", "promotion report is missing")
    output_hashes = report.get("outputHashes")
    if not isinstance(output_hashes, dict):
        return _failed(
            command, "promotion-output-hashes", "promotion report outputHashes must be a JSON object"
        )
    planned_writes = _planned_writes(report)

    errors: list[str] = []
    for relative_path, expected_hash in output_hashes.items():
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            errors.append("outputHashes entries must be string-to-string")
            continue
        artifact_path = _output_path(run, repository_root, relative_path)
        if artifact_path is None:
            errors.append(f"unknown output hash path: {relative_path}")
            continue
        if not artifact_path.is_file():
            errors.append(f"output artifact is missing: {relative_path}")
            continue
        if sha256_file(artifact_path) != expected_hash:
            errors.append(f"output artifact hash changed: {relative_path}")

    for plan in planned_writes:
        expected_hash = plan["sha256"]
        source_path = plan["source"]
        if output_hashes.get(source_path) != expected_hash:
            errors.append(
                f"planned write hash does not match promotion outputHashes: {source_path}"
            )

    if errors:
        return _failed(command, "promotion-output-hashes", "; ".join(errors))
    return ReleaseCheckResult(
        name="promotion-output-hashes",
        passed=True,
        command=command,
        output="promotion output hashes are current",
        error=None,
    )


def _check_runtime_integration(run: ReviewRun) -> ReleaseCheckResult:
    command = ("promotion-report", "runtime-integration")
    report = _promotion_report_document(run)
    if report is None:
        return _failed(command, "promotion-runtime", "promotion report is missing")

    problems: list[str] = []
    if not isinstance(report.get("profileId"), str) or not report["profileId"].strip():
        problems.append("profileId is missing")
    if not isinstance(report.get("boardId"), str) or not report["boardId"].strip():
        problems.append("boardId is missing")
    planned_writes = _planned_writes(report)
    if not planned_writes:
        problems.append("plannedWrites is empty")
    if report.get("status") not in _PASSING_PROMOTION_STATUSES:
        problems.append("promotion status is not release-ready")

    if problems:
        return _failed(command, "promotion-runtime", "; ".join(problems))
    return ReleaseCheckResult(
        name="promotion-runtime",
        passed=True,
        command=command,
        output="promotion report includes configured runtime handoff",
        error=None,
    )


def _check_generated_artifacts_clean(
    run: ReviewRun, repository_root: Path
) -> ReleaseCheckResult:
    report = _promotion_report_document(run)
    command = ("git", "status", "--short", "--untracked-files=all")
    if report is None:
        return _failed(command, "generated-artifacts-clean", "promotion report is missing")
    if not (repository_root / ".git").exists():
        return ReleaseCheckResult(
            name="generated-artifacts-clean",
            passed=True,
            command=command,
            output="git repository not detected; skipped",
            error=None,
        )

    planned_writes = _planned_writes(report)
    if not planned_writes:
        return _failed(
            command, "generated-artifacts-clean", "promotion report plannedWrites is empty"
        )

    relative_paths = [plan["destination"] for plan in planned_writes]
    git_command = command + ("--", *relative_paths)
    completed = subprocess.run(
        git_command,
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    output = _combine_output(completed.stdout, completed.stderr).strip()
    if completed.returncode != 0:
        return _failed(
            git_command,
            "generated-artifacts-clean",
            output or f"git status failed with exit code {completed.returncode}",
        )
    if output:
        return _failed(
            git_command,
            "generated-artifacts-clean",
            "generated destination files have uncommitted changes",
            output=output,
        )
    return ReleaseCheckResult(
        name="generated-artifacts-clean",
        passed=True,
        command=git_command,
        output="generated destination files are clean",
        error=None,
    )


def _run_export_plan_library(repository_root: Path) -> ReleaseCheckResult:
    script_directory = repository_root / "scripts"
    command = ("export-plan-library.sh", "--check")
    environment = os.environ.copy()
    path_entries = [str(script_directory)]
    if environment.get("PATH"):
        path_entries.append(environment["PATH"])
    environment["PATH"] = os.pathsep.join(path_entries)
    return _run_command(
        "export-plan-library",
        command,
        cwd=repository_root,
        env=environment,
    )


def _run_xcode_tests(run: ReviewRun, repository_root: Path) -> ReleaseCheckResult:
    uuid = _simulator_uuid(repository_root)
    if uuid is None:
        return _failed(
            ("xcodebuild", "test"),
            "xcode-tests",
            "no isolated simulator UUID was found in HANG_TEN_TEST_DEVICE_UDID or .context/conductor-owned-simulators",
        )

    derived_data = run.root / ".context/release-check-derived-data"
    command = (
        "xcodebuild",
        "-project",
        "HangTen.xcodeproj",
        "-scheme",
        "HangTen",
        "-configuration",
        "Debug",
        "-destination",
        f"platform=iOS Simulator,id={uuid}",
        "-parallel-testing-enabled",
        "NO",
        "-maximum-parallel-testing-workers",
        "1",
        "-derivedDataPath",
        str(derived_data),
        "CODE_SIGNING_ALLOWED=NO",
        "CODE_SIGNING_REQUIRED=NO",
        "CODE_SIGN_IDENTITY=-",
        "test",
    )
    return _run_command("xcode-tests", command, cwd=repository_root)


def _run_command(
    name: str,
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> ReleaseCheckResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        return _failed(
            command,
            name,
            _combine_output(error.stdout, error.stderr).strip()
            or f"command failed with exit code {error.returncode}",
        )
    except OSError as error:
        return _failed(command, name, _first_line(error))
    return ReleaseCheckResult(
        name=name,
        passed=True,
        command=command,
        output=_combine_output(completed.stdout, completed.stderr).strip() or "ok",
        error=None,
    )


def _promotion_report_document(run: ReviewRun) -> dict[str, object] | None:
    if run.promotion_report is None:
        return None
    return load_json(run.promotion_report, "promotion report")


def _current_input_hashes(run: ReviewRun) -> dict[str, str]:
    hashes = {
        "stage-1-auto-rgba.png": sha256_file(run.stage1_image),
        "stage-2-regions.json": sha256_file(run.stage2_regions),
    }
    if run.edited_regions is not None:
        hashes["stage-2-regions.edited.json"] = sha256_file(run.edited_regions)
    if run.corrections is not None:
        hashes["stage-2-human-corrections.json"] = sha256_file(run.corrections)
    if run.acceptance is not None:
        hashes["stage-2-review-acceptance.json"] = sha256_file(run.acceptance)
    if run.lint_report is not None:
        hashes["lint-report.json"] = sha256_file(run.lint_report)
    return hashes


def _planned_writes(report: dict[str, object]) -> list[dict[str, str]]:
    raw = report.get("plannedWrites")
    if not isinstance(raw, list):
        return []

    planned_writes: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        destination = entry.get("destination")
        sha256 = entry.get("sha256")
        source = entry.get("source")
        if (
            isinstance(destination, str)
            and isinstance(sha256, str)
            and isinstance(source, str)
        ):
            planned_writes.append(
                {"destination": destination, "sha256": sha256, "source": source}
            )
    return planned_writes


def _output_path(run: ReviewRun, repository_root: Path, relative_path: str) -> Path | None:
    if relative_path.startswith("promotion/"):
        return run.stage2_regions.parent / relative_path
    candidate = (repository_root / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(repository_root)
    except ValueError:
        return None
    return candidate


def _simulator_uuid(repository_root: Path) -> str | None:
    environment_uuid = os.environ.get("HANG_TEN_TEST_DEVICE_UDID")
    if _is_uuid(environment_uuid):
        return environment_uuid

    manifest_path = repository_root / ".context/conductor-owned-simulators"
    if not manifest_path.is_file():
        return None
    entries = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for entry in reversed(entries):
        if _is_uuid(entry):
            return entry
    return None


def _is_uuid(value: str | None) -> bool:
    if value is None or len(value) not in _UUID_LENGTHS:
        return False
    parts = value.split("-")
    return [len(part) for part in parts] == [8, 4, 4, 4, 12] and all(
        all(character in "0123456789abcdefABCDEF" for character in part)
        for part in parts
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _failed(
    command: tuple[str, ...], name: str, error: str, *, output: str = ""
) -> ReleaseCheckResult:
    return ReleaseCheckResult(
        name=name,
        passed=False,
        command=command,
        output=output,
        error=error,
    )


def _combine_output(stdout: str | None, stderr: str | None) -> str:
    chunks = [chunk.strip() for chunk in (stdout, stderr) if chunk and chunk.strip()]
    return "\n".join(chunks)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _first_line(error: BaseException) -> str:
    message = str(error)
    return message.splitlines()[0] if message else error.__class__.__name__


def _remediation_for(name: str) -> str:
    remediations = {
        "promotion-status": "Re-run hangboard-promote with the current accepted run until the promotion report status is ready or applied and warnings/errors are cleared.",
        "acceptance-current": "Re-run hangboard-review lint and accept the current edited regions before promoting again.",
        "promotion-input-hashes": "Rebuild the promotion package from the current accepted artifacts so the report input hashes match the run.",
        "promotion-output-hashes": "Rebuild the promotion package and restore the generated promotion outputs to the recorded hashes.",
        "promotion-runtime": "Generate a profile-backed promotion report with profileId, boardId, and plannedWrites populated.",
        "generated-artifacts-clean": "Commit, revert, or remove generated destination-file changes before running release-check again.",
        "export-plan-library": "Run scripts/export-plan-library.sh and commit the regenerated plan-library artifacts before release.",
        "xcode-tests": "Provide an isolated simulator UUID through HANG_TEN_TEST_DEVICE_UDID or .context/conductor-owned-simulators, then rerun with --xcode.",
    }
    return remediations.get(name, "Address the failing check and rerun release-check.")
