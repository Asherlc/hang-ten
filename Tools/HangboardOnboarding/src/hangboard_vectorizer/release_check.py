"""Run deterministic repository-facing release checks for reviewed boards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

from .promotion_profile import PromotionProfile, load_promotion_profile
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


@dataclass(frozen=True)
class _PromotionReportState:
    document: dict[str, object] | None
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
    promotion_report = _promotion_report_state(run)

    results: list[ReleaseCheckResult] = []
    results.append(_check_promotion_status(promotion_report))
    results.append(_check_acceptance_current(run))
    results.append(_check_promotion_input_hashes(run, promotion_report))
    results.append(_check_promotion_output_hashes(run, repository_root, promotion_report))
    results.append(_check_runtime_integration(run, promotion_report))
    results.append(_check_generated_artifacts_clean(repository_root, promotion_report))
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


def _check_promotion_status(report_state: _PromotionReportState) -> ReleaseCheckResult:
    command = ("promotion-report",)
    if report_state.error is not None:
        return _failed(command, "promotion-status", report_state.error)
    report = report_state.document
    assert report is not None

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


def _check_promotion_input_hashes(
    run: ReviewRun, report_state: _PromotionReportState
) -> ReleaseCheckResult:
    command = ("promotion-report", "input-hashes")
    if report_state.error is not None:
        return _failed(command, "promotion-input-hashes", report_state.error)
    report = report_state.document
    assert report is not None
    input_hashes = report.get("inputHashes")
    if not isinstance(input_hashes, dict):
        return _failed(
            command, "promotion-input-hashes", "promotion report inputHashes must be a JSON object"
        )

    expected = _current_input_hashes(run)
    provenance = report.get("profileProvenance")
    if isinstance(provenance, dict) and isinstance(provenance.get("path"), str):
        profile_path = Path(provenance["path"])
        if profile_path.is_file():
            expected["promotion-profile.json"] = sha256_file(profile_path)
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
    run: ReviewRun, repository_root: Path, report_state: _PromotionReportState
) -> ReleaseCheckResult:
    command = ("promotion-report", "output-hashes")
    if report_state.error is not None:
        return _failed(command, "promotion-output-hashes", report_state.error)
    report = report_state.document
    assert report is not None
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
        destination = plan["destination"]
        destination_path = _output_path(run, repository_root, destination)
        if destination_path is None:
            errors.append(f"planned destination resolves outside repository root: {destination}")
        elif not destination_path.is_file():
            errors.append(f"planned destination artifact is missing: {destination}")
        elif sha256_file(destination_path) != expected_hash:
            errors.append(f"planned destination artifact hash changed: {destination}")

    if errors:
        return _failed(command, "promotion-output-hashes", "; ".join(errors))
    return ReleaseCheckResult(
        name="promotion-output-hashes",
        passed=True,
        command=command,
        output="promotion output hashes are current",
        error=None,
    )


def _check_runtime_integration(
    run: ReviewRun, report_state: _PromotionReportState
) -> ReleaseCheckResult:
    command = ("promotion-report", "runtime-integration")
    if report_state.error is not None:
        return _failed(command, "promotion-runtime", report_state.error)
    report = report_state.document
    assert report is not None

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
    problems.extend(_profile_provenance_issues(run, report))

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
    repository_root: Path, report_state: _PromotionReportState
) -> ReleaseCheckResult:
    command = ("git", "status", "--short", "--untracked-files=all")
    if report_state.error is not None:
        return _failed(command, "generated-artifacts-clean", report_state.error)
    report = report_state.document
    assert report is not None
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


def _promotion_report_state(run: ReviewRun) -> _PromotionReportState:
    if run.promotion_report is None:
        return _PromotionReportState(None, "promotion report is missing")
    try:
        document = load_json(run.promotion_report, "promotion report")
    except ValueError as error:
        return _PromotionReportState(None, _first_line(error))
    return _PromotionReportState(document, None)


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


def _profile_provenance_issues(run: ReviewRun, report: dict[str, object]) -> list[str]:
    raw_profile = report.get("profile")
    if not isinstance(raw_profile, dict):
        return ["promotion report profile provenance is missing"]

    provenance = report.get("profileProvenance")
    current_profile: PromotionProfile | None = None
    problems: list[str] = []
    if not isinstance(provenance, dict):
        problems.append("promotion report profileProvenance is missing")
    else:
        source_path = provenance.get("path")
        expected_hash = provenance.get("sha256")
        if not isinstance(source_path, str) or not source_path:
            problems.append("profileProvenance.path is missing")
        elif not isinstance(expected_hash, str) or len(expected_hash) != 64:
            problems.append("profileProvenance.sha256 is invalid")
        else:
            profile_path = Path(source_path)
            if not profile_path.is_file():
                problems.append("profile provenance source is missing")
            elif sha256_file(profile_path) != expected_hash:
                problems.append("profile hash changed after promotion")
            else:
                try:
                    current_profile = load_promotion_profile(profile_path)
                except ValueError as error:
                    problems.append(_first_line(error))

    required_region_keys = raw_profile.get("requiredRegionKeys")
    runtime_mappings = raw_profile.get("runtimeMappings")

    if not isinstance(required_region_keys, list) or not required_region_keys:
        problems.append("profile.requiredRegionKeys must be a non-empty list")
        required_keys: tuple[str, ...] = ()
    else:
        required_keys = tuple(
            value for value in required_region_keys if isinstance(value, str) and value.strip()
        )
        if len(required_keys) != len(required_region_keys):
            problems.append("profile.requiredRegionKeys must contain non-empty strings")
        if len(set(required_keys)) != len(required_keys):
            problems.append("profile.requiredRegionKeys must be unique")

    if not isinstance(runtime_mappings, list) or not runtime_mappings:
        problems.append("profile.runtimeMappings must be a non-empty list")
        mappings: list[dict[str, str]] = []
    else:
        mappings = []
        seen_region_keys: set[str] = set()
        seen_runtime_ids: set[str] = set()
        for index, entry in enumerate(runtime_mappings):
            if not isinstance(entry, dict):
                problems.append(f"profile.runtimeMappings[{index}] must be an object")
                continue
            region_key = entry.get("regionKey")
            runtime_hold_id = entry.get("runtimeHoldId")
            grip_type = entry.get("gripType")
            interaction_mode = entry.get("interactionMode")
            if not all(
                isinstance(value, str) and value.strip()
                for value in (region_key, runtime_hold_id, grip_type, interaction_mode)
            ):
                problems.append(
                    f"profile.runtimeMappings[{index}] must define non-empty regionKey, runtimeHoldId, gripType, and interactionMode"
                )
                continue
            if region_key in seen_region_keys:
                problems.append(f"duplicate profile.runtimeMappings regionKey: {region_key}")
            if runtime_hold_id in seen_runtime_ids:
                problems.append(
                    f"duplicate profile.runtimeMappings runtimeHoldId: {runtime_hold_id}"
                )
            seen_region_keys.add(region_key)
            seen_runtime_ids.add(runtime_hold_id)
            mappings.append(
                {
                    "regionKey": region_key,
                    "runtimeHoldId": runtime_hold_id,
                    "gripType": grip_type,
                    "interactionMode": interaction_mode,
                }
            )

        if required_keys:
            unknown = sorted(
                mapping["regionKey"]
                for mapping in mappings
                if mapping["regionKey"] not in set(required_keys)
            )
            if unknown:
                problems.append(
                    "profile.runtimeMappings reference unknown requiredRegionKeys: "
                    + ", ".join(unknown)
                )
            mapped_keys = {mapping["regionKey"] for mapping in mappings}
            missing = sorted(set(required_keys) - mapped_keys)
            if missing:
                problems.append(
                    "profile.runtimeMappings missing requiredRegionKeys: "
                    + ", ".join(missing)
                )

    if current_profile is not None:
        expected_required = list(current_profile.required_region_keys)
        if required_region_keys != expected_required:
            problems.append(
                "profile.requiredRegionKeys does not match current profile: "
                f"reported {required_region_keys!r}, current {expected_required!r}"
            )
        expected_mappings = [
            {
                "regionKey": mapping.region_key,
                "runtimeHoldId": mapping.runtime_hold_id,
                "gripType": mapping.grip_type,
                "interactionMode": mapping.interaction_mode,
            }
            for mapping in current_profile.runtime_mappings
        ]
        for index, expected_mapping in enumerate(expected_mappings):
            reported = mappings[index] if index < len(mappings) else None
            if reported is None:
                continue
            for field, expected_value in expected_mapping.items():
                if reported.get(field) != expected_value:
                    problems.append(
                        f"profile.runtimeMappings[{index}].{field} does not match current profile"
                    )
        expected_destinations = {
            (destination.source_relative, destination.destination_relative)
            for destination in current_profile.destinations
        }
        reported_destinations = {
            (plan["source"].removeprefix("promotion/"), plan["destination"])
            for plan in _planned_writes(report)
        }
        missing_destinations = expected_destinations - reported_destinations
        for source, destination in sorted(missing_destinations):
            problems.append(
                f"configured profile destination is missing from plannedWrites: {source} -> {destination}"
            )

    if required_keys:
        if run.edited_regions is None:
            problems.append("edited regions artifact is missing")
        else:
            try:
                edited = load_json(run.edited_regions, "stage-2 edited regions")
            except ValueError as error:
                problems.append(_first_line(error))
                return problems
            regions = edited.get("regions")
            if not isinstance(regions, list):
                problems.append("stage-2 edited regions missing regions array")
            else:
                by_key = {
                    region.get("key"): region
                    for region in regions
                    if isinstance(region, dict) and isinstance(region.get("key"), str)
                }
                missing_regions = sorted(set(required_keys) - set(by_key))
                if missing_regions:
                    problems.append(
                        "profile.requiredRegionKeys missing reviewed geometry: "
                        + ", ".join(missing_regions)
                    )
                for mapping in mappings:
                    region = by_key.get(mapping["regionKey"])
                    if region is None:
                        continue
                    if region.get("type") != mapping["gripType"]:
                        problems.append(
                            f"profile.runtimeMappings gripType disagrees with reviewed region {mapping['regionKey']}"
                        )
                    metadata = region.get("metadata")
                    mode = (
                        metadata.get("mode")
                        if isinstance(metadata, dict) and metadata.get("mode") is not None
                        else region.get("mode", region.get("visualMode"))
                    )
                    if mode != mapping["interactionMode"]:
                        problems.append(
                            f"profile.runtimeMappings interactionMode disagrees with reviewed region {mapping['regionKey']}"
                        )
    return problems


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
