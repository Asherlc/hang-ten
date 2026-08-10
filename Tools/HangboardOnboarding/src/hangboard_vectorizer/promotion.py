"""Generate promotion reports and apply reviewed hold-region artifacts safely."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

from .promotion_profile import PromotionProfile
from .review_acceptance import validate_acceptance
from .review_artifacts import ReviewRun, discover_review_run, load_json, sha256_file
from .review_lint import lint_review, write_lint_report, _atomic_write_json

_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PromotionReport:
    schemaVersion: int
    status: str
    profileId: str | None
    boardId: str | None
    profile: dict[str, object] | None
    inputHashes: dict[str, str]
    outputHashes: dict[str, str]
    plannedWrites: tuple[dict[str, str], ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    handoffRequired: bool = False


def promote_run(
    run: ReviewRun,
    profile: PromotionProfile | None,
    repository_root: Path,
    *,
    apply: bool = False,
) -> PromotionReport:
    """Create a promotion package for one accepted review run."""
    if apply and profile is None:
        raise ValueError("--apply requires --profile")

    current_run = discover_review_run(run.root)
    stage2_dir = current_run.stage2_regions.parent.resolve(strict=False)
    stage2_dir.relative_to(current_run.root)
    promotion_dir = stage2_dir / "promotion"
    promotion_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        validate_acceptance(current_run)
    except ValueError as error:
        errors.append(_first_line(error))

    try:
        lint_report = lint_review(current_run)
        lint_report_path = write_lint_report(current_run, lint_report)
        if not lint_report.passed:
            errors.extend(
                f"{issue.code}: {issue.message}" for issue in lint_report.issues
            )
    except ValueError as error:
        lint_report_path = None
        errors.append(_first_line(error))

    package_copy = _copy_edited_regions(current_run, promotion_dir, errors)

    refreshed_run = discover_review_run(current_run.root)
    input_hashes = _input_hashes(refreshed_run)
    if lint_report_path is not None:
        input_hashes["lint-report.json"] = sha256_file(lint_report_path)

    output_hashes: dict[str, str] = {}
    if package_copy is not None:
        output_hashes["promotion/edited-regions.json"] = sha256_file(package_copy)

    planned_writes: tuple[dict[str, str], ...] = ()
    package_sources: dict[str, Path] = {}
    if package_copy is not None:
        package_sources["edited-regions.json"] = package_copy

    if profile is None:
        warnings.append("runtime integration profile is not configured")
        status = "blocked" if errors else "handoff-required"
        report = PromotionReport(
            schemaVersion=_SCHEMA_VERSION,
            status=status,
            profileId=None,
            boardId=None,
            profile=None,
            inputHashes=input_hashes,
            outputHashes=output_hashes,
            plannedWrites=planned_writes,
            warnings=tuple(warnings),
            errors=tuple(errors),
            handoffRequired=not errors,
        )
        _write_report(promotion_dir / "board-promotion-report.json", report)
        return report

    errors.extend(_missing_required_regions(current_run, profile))
    planned_write_details = _planned_writes(
        profile, repository_root, promotion_dir, package_sources
    )
    planned_writes = tuple(plan["manifest"] for plan in planned_write_details)

    if not errors and apply:
        for plan in planned_write_details:
            _atomic_copy(plan["source_path"], plan["destination_path"])
            output_hashes[plan["destination"]] = sha256_file(plan["destination_path"])

    status = "blocked" if errors else ("applied" if apply else "ready")
    report = PromotionReport(
        schemaVersion=_SCHEMA_VERSION,
        status=status,
        profileId=profile.profile_id,
        boardId=profile.board_id,
        profile=_profile_payload(profile),
        inputHashes=input_hashes,
        outputHashes=output_hashes,
        plannedWrites=planned_writes,
        warnings=tuple(warnings),
        errors=tuple(errors),
        handoffRequired=False,
    )
    _write_report(promotion_dir / "board-promotion-report.json", report)
    return report


def promotion_report_payload(report: PromotionReport) -> dict[str, object]:
    payload: dict[str, object] = {
        "schemaVersion": report.schemaVersion,
        "status": report.status,
        "profileId": report.profileId,
        "boardId": report.boardId,
        "inputHashes": report.inputHashes,
        "outputHashes": report.outputHashes,
        "plannedWrites": list(report.plannedWrites),
        "warnings": list(report.warnings),
        "errors": list(report.errors),
    }
    if report.profile is not None:
        payload["profile"] = report.profile
    if report.handoffRequired:
        payload["handoffRequired"] = True
    return payload


def _profile_payload(profile: PromotionProfile) -> dict[str, object]:
    return {
        "schemaVersion": profile.schema_version,
        "requiredRegionKeys": list(profile.required_region_keys),
        "runtimeMappings": [
            {
                "regionKey": mapping.region_key,
                "runtimeHoldId": mapping.runtime_hold_id,
                "gripType": mapping.grip_type,
                "interactionMode": mapping.interaction_mode,
                "notes": mapping.notes,
            }
            for mapping in profile.runtime_mappings
        ],
    }


def _copy_edited_regions(
    run: ReviewRun, promotion_dir: Path, errors: list[str]
) -> Path | None:
    if run.edited_regions is None:
        errors.append("edited regions artifact is missing")
        return None
    destination = promotion_dir / "edited-regions.json"
    _atomic_copy(run.edited_regions, destination)
    return destination


def _input_hashes(run: ReviewRun) -> dict[str, str]:
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


def _missing_required_regions(run: ReviewRun, profile: PromotionProfile) -> list[str]:
    if run.edited_regions is None:
        return ["edited regions artifact is missing"]
    edited = load_json(run.edited_regions, "stage-2 edited regions")
    regions = edited.get("regions")
    if not isinstance(regions, list):
        return ["stage-2 edited regions missing regions array"]
    present = {
        region.get("key")
        for region in regions
        if isinstance(region, Mapping) and isinstance(region.get("key"), str)
    }
    return [
        f"required region mapping missing reviewed geometry: {region_key}"
        for region_key in profile.required_region_keys
        if region_key not in present
    ]


def _planned_writes(
    profile: PromotionProfile,
    repository_root: Path,
    promotion_dir: Path,
    package_sources: Mapping[str, Path],
) -> list[dict[str, object]]:
    repository_root_resolved = repository_root.resolve(strict=False)
    plans: list[dict[str, object]] = []
    for destination in profile.destinations:
        source_path = package_sources.get(destination.source_relative)
        if source_path is None:
            raise ValueError(
                f"promotion package source is missing: {destination.source_relative}"
            )
        source_path.resolve(strict=False).relative_to(promotion_dir.resolve(strict=False))
        destination_path = (repository_root_resolved / destination.destination_relative).resolve(
            strict=False
        )
        try:
            destination_path.relative_to(repository_root_resolved)
        except ValueError as error:
            raise ValueError("promotion destination resolves outside repository root") from error
        plans.append(
            {
                "source_path": source_path,
                "destination_path": destination_path,
                "destination": destination.destination_relative,
                "manifest": {
                    "destination": destination.destination_relative,
                    "sha256": sha256_file(source_path),
                    "source": f"promotion/{destination.source_relative}",
                },
            }
        )
    return plans


def _write_report(path: Path, report: PromotionReport) -> None:
    _atomic_write_json(path, promotion_report_payload(report))


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.tmp-", dir=destination.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with open(source, "rb") as source_handle, os.fdopen(descriptor, "wb") as target:
            target.write(source_handle.read())
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def _first_line(error: BaseException) -> str:
    message = str(error)
    return message.splitlines()[0] if message else error.__class__.__name__
