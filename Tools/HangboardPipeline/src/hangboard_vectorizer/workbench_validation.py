"""Read-only readiness checks for an approved workbench revision."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any

_PLAN_LIBRARY_TIMEOUT_SECONDS = 30.0
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "sloper"})


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
    """Validate an approved run and plan library without writing either."""
    try:
        artifacts = _load_approved_artifacts(run_root)
    except (OSError, ValueError) as error:
        return _failed_package_report(board_id, revision_id, error)

    readiness = ValidationCheck(
        check_id="package-readiness",
        status="passed",
        message="approved Stage 2–4 package is ready",
        details=(),
    )
    try:
        regions = _merge_regions(
            artifacts["stage2"], artifacts["stage3"], artifacts["stage4"]
        )
    except (KeyError, ValueError) as error:
        parity = _failed_check("hold-id-parity", "hold ID parity failed", error)
        return _report(
            board_id,
            revision_id,
            (readiness, parity, _not_run("semantic-routine-resolution"), _not_run()),
        )

    parity = ValidationCheck(
        check_id="hold-id-parity",
        status="passed",
        message="Stage 2, Stage 3, and Stage 4 hold IDs agree",
        details=(),
    )
    semantic_resolution = _semantic_routine_resolution_check(
        regions, artifacts["stage4"]
    )
    if semantic_resolution.status != "passed":
        return _report(
            board_id,
            revision_id,
            (readiness, parity, semantic_resolution, _not_run()),
        )
    plan_library = _plan_library_check(repository_root)
    return _report(
        board_id,
        revision_id,
        (readiness, parity, semantic_resolution, plan_library),
    )


def _failed_package_report(
    board_id: str, revision_id: str, error: Exception
) -> ValidationReport:
    return _report(
        board_id,
        revision_id,
        (
            _failed_check("package-readiness", "package readiness failed", error),
            _not_run("hold-id-parity"),
            _not_run("semantic-routine-resolution"),
            _not_run(),
        ),
    )


def _semantic_routine_resolution_check(
    regions: tuple[dict[str, Any], ...], stage4: dict[str, Any]
) -> ValidationCheck:
    """Prove each deterministic semantic target resolves to an approved Stage 4 hold."""
    try:
        known_stage4_hold_ids = set(
            _keyed_regions(_regions(stage4, "Stage 4"), "Stage 4")
        )
        semantic_holds = _semantic_holds(regions)
        if not semantic_holds:
            raise ValueError("no semantic routine mappings were derived")
        resolved_hold_ids = {
            hold_id
            for hold_ids in semantic_holds.values()
            for hold_id in hold_ids
        }
        if not resolved_hold_ids <= known_stage4_hold_ids:
            unknown = sorted(resolved_hold_ids - known_stage4_hold_ids)
            raise ValueError(
                f"semantic mappings reference unknown Stage 4 hold IDs: {', '.join(unknown)}"
            )
        if resolved_hold_ids != known_stage4_hold_ids:
            unresolved = sorted(known_stage4_hold_ids - resolved_hold_ids)
            raise ValueError(
                f"approved Stage 4 hold IDs have no semantic mapping: {', '.join(unresolved)}"
            )
    except (KeyError, ValueError) as error:
        return _failed_check(
            "semantic-routine-resolution",
            "semantic routine resolution failed",
            error,
        )
    return ValidationCheck(
        check_id="semantic-routine-resolution",
        status="passed",
        message="approved semantic groups resolve to known Stage 4 hold IDs",
        details=(),
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


def _load_approved_artifacts(run_root: Path) -> dict[str, Any]:
    run = _read_object(run_root / "run.json")
    if run.get("schemaVersion") != 1:
        raise ValueError("unsupported onboarding run schema")
    pipeline = _object(run.get("pipeline"), "run pipeline")
    if pipeline.get("status") != "complete" or pipeline.get("currentStage") != 4:
        raise ValueError("onboarding run must be complete through Stage 4")
    records: dict[int, Mapping[str, Any]] = {}
    for raw in _list(run.get("stages"), "run stages"):
        record = _object(raw, "stage record")
        stage = record.get("stage")
        if isinstance(stage, int) and not isinstance(stage, bool):
            records[stage] = record
    documents: dict[str, Any] = {"run": run}
    for stage, label, filename in (
        (2, "stage2", "stage-2-regions.json"),
        (3, "stage3", "stage-3-vector-regions.json"),
        (4, "stage4", "stage-4-manifest.json"),
    ):
        record = records.get(stage)
        if (
            record is None
            or record.get("status") != "approved"
            or record.get("machinePassed") is not True
        ):
            raise ValueError(f"Stage {stage} must be approved before validation")
        artifact_root = record.get("artifactRoot")
        if not isinstance(artifact_root, str):
            raise ValueError(f"Stage {stage} artifact root is missing")
        path = run_root / artifact_root / filename
        document = _read_object(path)
        if document.get("stage") != stage:
            raise ValueError(f"Stage {stage} artifact is invalid")
        if stage >= 3 and document.get("schemaVersion") != 1:
            raise ValueError(f"Stage {stage} artifact schema is invalid")
        documents[label] = document
    return documents


def _merge_regions(
    stage2: Mapping[str, Any],
    stage3: Mapping[str, Any],
    stage4: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    width, height = _canvas(_object(stage2.get("canvas"), "Stage 2 canvas"))
    for label, document in (("Stage 3", stage3), ("Stage 4", stage4)):
        if _canvas(_object(document.get("canvas"), f"{label} canvas")) != (
            width,
            height,
        ):
            raise ValueError(f"{label} canvas does not match Stage 2")
    stage2_regions = _regions(stage2, "Stage 2")
    keyed3 = _keyed_regions(_regions(stage3, "Stage 3"), "Stage 3")
    keyed4 = _keyed_regions(_regions(stage4, "Stage 4"), "Stage 4")
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for region in stage2_regions:
        key = _string(region.get("key"), "Stage 2 region key")
        if key in seen_ids:
            raise ValueError(f"duplicate hold ID: {key}")
        seen_ids.add(key)
        vector = keyed3.get(key)
        manifest = keyed4.get(key)
        if vector is None or manifest is None:
            raise ValueError(f"missing Stage 3 or Stage 4 region for {key}")
        kind = _string(region.get("type"), f"hold type for {key}")
        if kind not in _HOLD_KINDS:
            raise ValueError(f"unsupported hold kind: {kind}")
        if region.get("id") != vector.get("id") or region.get("id") != manifest.get("id"):
            raise ValueError(f"region ID mismatch for {key}")
        if region.get("type") != vector.get("type") or region.get("type") != manifest.get("type"):
            raise ValueError(f"region type mismatch for {key}")
        path = vector.get("displayPath")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Stage 3 displayPath is missing for {key}")
        left, top, right, bottom = _bounds(
            manifest.get("bounds", region.get("bounds")),
            key,
            width,
            height,
        )
        result.append(
            {
                "id": region["id"],
                "key": key,
                "kind": kind,
                "metadata": _object(region.get("metadata", {}), f"metadata for {key}"),
                "path": path,
                "frame": (
                    left / width,
                    top / height,
                    (right - left) / width,
                    (bottom - top) / height,
                ),
                "symmetry": vector.get("symmetry"),
            }
        )
    if len(keyed3) != len(result) or len(keyed4) != len(result):
        raise ValueError("Stage 2, Stage 3, and Stage 4 region sets differ")
    return tuple(result)


def _semantic_holds(
    regions: Iterable[Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {}
    for region in regions:
        key = _string(region["key"], "hold key")
        kind = _string(region["kind"], "hold kind")
        metadata = _object(region["metadata"], f"metadata for {key}")
        depth = _optional_depth(metadata, key)
        fingers = _finger_capacity(metadata, key, kind)
        if kind == "jug":
            semantic = "outer-jugs"
        elif kind == "sloper":
            profile = _string(metadata.get("profile"), f"sloper profile for {key}")
            semantic = {"flat": "flat-slopers", "round": "round-sloper"}.get(
                profile, ""
            )
            if not semantic:
                raise ValueError(f"unsupported sloper profile for {key}: {profile}")
        elif kind == "edge" and depth is not None:
            semantic = f"edge-{depth}"
        elif kind == "pocket" and depth is not None and fingers is not None:
            word = {2: "two", 3: "three", 4: "four"}.get(fingers)
            if word is None:
                raise ValueError(f"unsupported fingerCount for {key}: {fingers}")
            semantic = f"pocket-{depth}-{word}"
        else:
            raise ValueError(f"cannot derive a semantic mapping for {key}")
        result.setdefault(semantic, []).append(key)
    return {key: tuple(value) for key, value in result.items()}


def _regions(
    document: Mapping[str, Any], label: str
) -> list[Mapping[str, Any]]:
    return [
        _object(item, f"{label} region")
        for item in _list(document.get("regions"), f"{label} regions")
    ]


def _keyed_regions(
    regions: Iterable[Mapping[str, Any]], label: str
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for region in regions:
        key = _string(region.get("key"), f"{label} region key")
        if key in result:
            raise ValueError(f"duplicate hold ID: {key}")
        result[key] = region
    return result


def _canvas(canvas: Mapping[str, Any]) -> tuple[int, int]:
    width, height = canvas.get("width"), canvas.get("height")
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width <= 0
        or height <= 0
    ):
        raise ValueError("canvas must have positive integer dimensions")
    return width, height


def _bounds(
    value: object, key: str, width: int, height: int
) -> tuple[float, float, float, float]:
    values = _list(value, f"bounds for {key}")
    if len(values) != 4 or any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        for item in values
    ):
        raise ValueError(f"bounds are invalid for {key}")
    left, top, right, bottom = (float(item) for item in values)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"bounds are outside the canvas for {key}")
    return left, top, right, bottom


def _optional_depth(metadata: Mapping[str, Any], key: str) -> int | None:
    value = metadata.get("depthMm")
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"depthMm must be a positive integer for {key}")
    return value


def _finger_capacity(
    metadata: Mapping[str, Any], key: str, kind: str
) -> int | None:
    value = metadata.get("fingerCount")
    if kind != "pocket":
        if value is not None:
            raise ValueError(f"fingerCount is only supported for pockets: {key}")
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value not in {2, 3, 4}:
        raise ValueError(f"unsupported fingerCount for {key}")
    return value


def _object(value: object, description: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be an object")
    return value


def _list(value: object, description: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{description} must be an array")
    return value


def _string(value: object, description: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{description} must be a non-empty string")
    return value


def _read_object(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"required validation artifact is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid validation JSON: {path}") from error
    return _object(value, str(path))
