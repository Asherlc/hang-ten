"""Generic exact-canvas preservation and tensioned-cord method validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .board_catalog import decode_png_rgba
from .tensioned_cord_audit import TensionedCordRecord


_PRESERVATION_INVARIANTS = {
    "backgroundFramingPreserved": "backgroundFraming",
    "boardTransformPreserved": "boardTransform",
    "boardAppearancePreserved": "boardAppearance",
    "unrelatedPixelsPreserved": "unrelatedPixels",
    "overlayAlignmentPreserved": "overlayAlignment",
}


@dataclass(frozen=True)
class CordViolation:
    capture_id: str
    invariant: str
    message: str

    def to_json(self) -> dict[str, str]:
        return {
            "captureID": self.capture_id,
            "invariant": self.invariant,
            "message": self.message,
        }


@dataclass(frozen=True)
class CordCandidateReport:
    capture_id: str
    violations: tuple[CordViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_json(self) -> dict[str, object]:
        return {
            "captureID": self.capture_id,
            "passed": self.passed,
            "violations": [violation.to_json() for violation in self.violations],
        }


@dataclass(frozen=True)
class CordCandidateRun:
    baseline_path: Path
    candidate_path: Path
    record: TensionedCordRecord
    evidence: Mapping[str, Any]


@dataclass(frozen=True)
class CordCohortReport:
    required_capture_ids: tuple[str, ...]
    method_id: str | None
    method_intent: str | None
    configuration_sha256: str
    candidates: tuple[CordCandidateReport, ...]
    violations: tuple[CordViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations and all(candidate.passed for candidate in self.candidates)

    @property
    def promoted(self) -> bool:
        return self.passed and self.method_intent == "promotion"

    def to_json(self) -> dict[str, object]:
        return {
            "requiredCaptureIDs": list(self.required_capture_ids),
            "methodID": self.method_id,
            "methodIntent": self.method_intent,
            "configurationSHA256": self.configuration_sha256,
            "passed": self.passed,
            "promoted": self.promoted,
            "candidates": [candidate.to_json() for candidate in self.candidates],
            "violations": [violation.to_json() for violation in self.violations],
        }


def _capture_id(record: TensionedCordRecord) -> str:
    return f"{record.package_id}::{record.presentation_id}"


def _violation(
    violations: list[CordViolation],
    capture_id: str,
    invariant: str,
    message: str,
) -> None:
    violations.append(CordViolation(capture_id, invariant, message))


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _load_pixels(path: Path) -> tuple[str, tuple[int, int], tuple[tuple[int, int, int, int], ...]]:
    image_path = Path(path)
    decoded = decode_png_rgba(image_path, str(image_path))
    return decoded.source_mode, (decoded.width, decoded.height), decoded.pixels


def _declared_changed_pixels(
    value: object,
    *,
    capture_id: str,
    violations: list[CordViolation],
) -> dict[tuple[int, int], tuple[tuple[int, ...], tuple[int, ...], str]]:
    if not isinstance(value, list):
        _violation(
            violations,
            capture_id,
            "methodRunContract",
            "changedPixels must be an array",
        )
        return {}
    result: dict[tuple[int, int], tuple[tuple[int, ...], tuple[int, ...], str]] = {}
    for index, item in enumerate(value):
        payload = _mapping(item)
        if payload is None or set(payload) != {
            "x",
            "y",
            "beforeRGBA",
            "afterRGBA",
            "classification",
        }:
            _violation(
                violations,
                capture_id,
                "methodRunContract",
                f"changedPixels[{index}] has an invalid shape",
            )
            continue
        x, y = payload["x"], payload["y"]
        before, after = payload["beforeRGBA"], payload["afterRGBA"]
        classification = payload["classification"]
        if (
            isinstance(x, bool)
            or not isinstance(x, int)
            or isinstance(y, bool)
            or not isinstance(y, int)
            or not isinstance(before, list)
            or not isinstance(after, list)
            or len(before) != 4
            or len(after) != 4
            or not all(isinstance(channel, int) and not isinstance(channel, bool) and 0 <= channel <= 255 for channel in before + after)
            or not isinstance(classification, str)
        ):
            _violation(
                violations,
                capture_id,
                "methodRunContract",
                f"changedPixels[{index}] contains invalid values",
            )
            continue
        key = (x, y)
        if key in result:
            _violation(
                violations,
                capture_id,
                "changedPixelAccounting",
                f"pixel {x},{y} is declared more than once",
            )
            continue
        result[key] = (tuple(before), tuple(after), classification)
    return result


def _validate_physics(
    value: object,
    record: TensionedCordRecord,
    capture_id: str,
    canvas_size: tuple[int, int],
    violations: list[CordViolation],
) -> None:
    physics = _mapping(value)
    if physics is None or set(physics) != {
        "proofCaptureID",
        "orientation",
        "gravity",
        "loadDirection",
        "cordPaths",
    }:
        _violation(violations, capture_id, "methodRunContract", "physics has an invalid shape")
        return
    if (
        physics["proofCaptureID"] != capture_id
        or physics["orientation"] != record.orientation
        or physics["gravity"] != record.gravity
        or physics["gravity"] != "canvasDown"
    ):
        _violation(
            violations,
            capture_id,
            "physicsPresentation",
            "physics proof is not bound to this presentation and canvas-down gravity",
        )
    if physics["loadDirection"] != record.tension_direction or physics["loadDirection"] != "towardCanvasBottom":
        _violation(
            violations,
            capture_id,
            "tensionDirection",
            "load direction does not agree with canvas-down gravity",
        )
    paths = physics["cordPaths"]
    if not isinstance(paths, list) or not paths:
        _violation(violations, capture_id, "cordTautness", "cordPaths must contain a path")
        return
    for path_index, path in enumerate(paths):
        if not isinstance(path, list) or len(path) < 2:
            _violation(
                violations,
                capture_id,
                "cordTautness",
                f"cord path {path_index} must contain at least two points",
            )
            continue
        points: list[tuple[float, float]] = []
        for point in path:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in point)
                or not all(math.isfinite(float(value)) for value in point)
            ):
                points = []
                break
            points.append((float(point[0]), float(point[1])))
        if not points:
            _violation(
                violations,
                capture_id,
                "cordTautness",
                f"cord path {path_index} has an invalid point",
            )
            continue
        width, height = canvas_size
        if any(not (0 <= x < width and 0 <= y < height) for x, y in points):
            _violation(
                violations,
                capture_id,
                "cordLoadPath",
                f"cord path {path_index} leaves the candidate canvas",
            )
        if points[-1][1] <= points[0][1]:
            _violation(
                violations,
                capture_id,
                "cordLoadPath",
                f"cord path {path_index} does not end toward canvas-down gravity",
            )
        length = sum(math.dist(first, second) for first, second in zip(points, points[1:]))
        direct = math.dist(points[0], points[-1])
        if direct == 0 or not math.isclose(length, direct, rel_tol=1e-6, abs_tol=1e-6):
            _violation(
                violations,
                capture_id,
                "cordTautness",
                f"cord path {path_index} is not a taut straight segment",
            )


def validate_cord_candidate(
    baseline_path: Path,
    candidate_path: Path,
    record: TensionedCordRecord,
    method_run: Mapping[str, Any],
) -> CordCandidateReport:
    """Validate one candidate without product-specific geometry or thresholds."""
    capture_id = _capture_id(record)
    violations: list[CordViolation] = []
    run = _mapping(method_run)
    required_keys = {
        "schemaVersion",
        "captureID",
        "orientation",
        "gravity",
        "sourcePresentationID",
        "method",
        "claimedTopology",
        "changedPixels",
        "preservation",
        "physics",
    }
    if run is None or set(run) != required_keys or run.get("schemaVersion") != 1:
        _violation(violations, capture_id, "methodRunContract", "method run has an invalid shape")
        return CordCandidateReport(capture_id, tuple(violations))
    if run["captureID"] != capture_id:
        _violation(violations, capture_id, "presentationIdentity", "capture identity does not match")
    if run["orientation"] != record.orientation:
        _violation(violations, capture_id, "presentationOrientation", "orientation proof does not match")
    if run["gravity"] != record.gravity or run["gravity"] != "canvasDown":
        _violation(violations, capture_id, "canvasGravity", "gravity proof is not canvasDown")
    if run["sourcePresentationID"] != record.source_presentation_id:
        _violation(
            violations,
            capture_id,
            "sourcePresentationIdentity",
            "source presentation proof does not match this presentation",
        )
    if record.status != "accepted" or record.blocker is not None:
        _violation(
            violations,
            capture_id,
            "sourceBlocker",
            record.blocker or "source record is not accepted",
        )
    if run["claimedTopology"] != record.visible_topology:
        _violation(
            violations,
            capture_id,
            "cordTopology",
            "claimed topology is not established by the source ledger",
        )
    _method_id, method_intent, _configuration_sha256 = _method_identity(run)
    if method_intent is None:
        _violation(
            violations,
            capture_id,
            "methodRunContract",
            "method must contain an ID, intent, and JSON-normalizable configuration",
        )

    preservation = _mapping(run["preservation"])
    if preservation is None or set(preservation) != set(_PRESERVATION_INVARIANTS):
        _violation(
            violations,
            capture_id,
            "methodRunContract",
            "preservation evidence has an invalid shape",
        )
    else:
        for key, invariant in _PRESERVATION_INVARIANTS.items():
            if preservation[key] is not True:
                _violation(
                    violations,
                    capture_id,
                    invariant,
                    f"method evidence does not prove {key}",
                )

    try:
        baseline_mode, baseline_size, baseline_pixels = _load_pixels(baseline_path)
        candidate_mode, candidate_size, candidate_pixels = _load_pixels(candidate_path)
    except (OSError, ValueError) as error:
        _violation(violations, capture_id, "imageDecode", str(error))
        return CordCandidateReport(capture_id, tuple(violations))
    if baseline_size != candidate_size:
        _violation(
            violations,
            capture_id,
            "canvasDimensions",
            f"candidate canvas {candidate_size} does not match baseline {baseline_size}",
        )
    baseline_has_alpha = "A" in baseline_mode
    candidate_has_alpha = "A" in candidate_mode
    if (
        baseline_mode != candidate_mode
        or baseline_has_alpha != candidate_has_alpha
        or (
            baseline_size == candidate_size
            and baseline_has_alpha
            and [pixel[3] for pixel in baseline_pixels] != [pixel[3] for pixel in candidate_pixels]
        )
    ):
        _violation(
            violations,
            capture_id,
            "alphaCompatibility",
            "candidate alpha mode or values do not match the baseline",
        )

    declared = _declared_changed_pixels(
        run["changedPixels"],
        capture_id=capture_id,
        violations=violations,
    )
    actual: dict[tuple[int, int], tuple[tuple[int, ...], tuple[int, ...]]] = {}
    if baseline_size == candidate_size:
        width, _height = baseline_size
        for index, (before, after) in enumerate(zip(baseline_pixels, candidate_pixels)):
            if before != after:
                actual[(index % width, index // width)] = (before, after)
    if set(actual) != set(declared) or any(
        actual.get(position) != (values[0], values[1])
        for position, values in declared.items()
    ):
        _violation(
            violations,
            capture_id,
            "changedPixelAccounting",
            "declared changed pixels do not exactly match the canvas diff",
        )
    if any(values[2] != "cord" for values in declared.values()):
        _violation(
            violations,
            capture_id,
            "unrelatedPixels",
            "every changed pixel must be classified as cord",
        )
    if method_intent == "negativeControl" and actual:
        _violation(
            violations,
            capture_id,
            "negativeControlMutation",
            "a negative-control candidate must be pixel-identical to its baseline",
        )

    _validate_physics(run["physics"], record, capture_id, candidate_size, violations)
    return CordCandidateReport(capture_id, tuple(violations))


def _method_identity(evidence: Mapping[str, Any]) -> tuple[str | None, str | None, str]:
    method = _mapping(evidence.get("method"))
    if method is None or set(method) != {"id", "intent", "configuration"}:
        return None, None, ""
    method_id = method["id"]
    method_intent = method["intent"]
    configuration = method["configuration"]
    if (
        not isinstance(method_id, str)
        or not method_id
        or method_intent not in {"negativeControl", "promotion"}
        or not isinstance(configuration, Mapping)
    ):
        return None, None, ""
    try:
        canonical = json.dumps(
            configuration,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return None, None, ""
    return method_id, method_intent, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_cord_candidate_runs(
    path: Path,
    *,
    records_by_capture_id: Mapping[str, TensionedCordRecord],
) -> tuple[CordCandidateRun, ...]:
    """Load a closed cohort contract whose files stay beside the contract."""
    contract_path = Path(path)
    if contract_path.is_symlink() or not contract_path.is_file():
        raise ValueError(f"cord method cohort must be a regular file: {contract_path}")
    try:
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"cord method cohort is invalid JSON: {contract_path}") from error
    if not isinstance(payload, Mapping) or set(payload) != {"schemaVersion", "runs"}:
        raise ValueError("cord method cohort has an invalid shape")
    if payload["schemaVersion"] != 1 or isinstance(payload["schemaVersion"], bool):
        raise ValueError("cord method cohort schemaVersion must be 1")
    run_values = payload["runs"]
    if not isinstance(run_values, list) or not run_values:
        raise ValueError("cord method cohort runs must be a non-empty array")
    root = contract_path.parent.resolve()
    runs: list[CordCandidateRun] = []
    seen: set[str] = set()
    for index, value in enumerate(run_values):
        if not isinstance(value, Mapping) or set(value) != {
            "captureID",
            "baselinePath",
            "candidatePath",
            "evidence",
        }:
            raise ValueError(f"cord method cohort runs[{index}] has an invalid shape")
        capture_id = value["captureID"]
        if not isinstance(capture_id, str) or capture_id not in records_by_capture_id:
            raise ValueError(f"unknown capture identity: {capture_id}")
        if capture_id in seen:
            raise ValueError(f"duplicate capture identity: {capture_id}")
        seen.add(capture_id)
        resolved_paths: list[Path] = []
        for key in ("baselinePath", "candidatePath"):
            raw_path = value[key]
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f"cord method cohort runs[{index}].{key} must be a path")
            relative = Path(raw_path)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"cord method cohort runs[{index}].{key} must stay beneath the contract directory")
            unresolved = root / relative
            cursor = root
            if any((cursor := cursor / part).is_symlink() for part in relative.parts):
                raise ValueError(f"cord method cohort runs[{index}].{key} is not a regular file")
            resolved = unresolved.resolve()
            try:
                resolved.relative_to(root)
            except ValueError as error:
                raise ValueError(
                    f"cord method cohort runs[{index}].{key} must stay beneath the contract directory"
                ) from error
            if resolved.is_symlink() or not resolved.is_file():
                raise ValueError(f"cord method cohort runs[{index}].{key} is not a regular file")
            resolved_paths.append(resolved)
        evidence = value["evidence"]
        if not isinstance(evidence, Mapping):
            raise ValueError(f"cord method cohort runs[{index}].evidence must be an object")
        runs.append(
            CordCandidateRun(
                resolved_paths[0],
                resolved_paths[1],
                records_by_capture_id[capture_id],
                evidence,
            )
        )
    return tuple(runs)


def validate_cord_method_cohort(
    runs: Sequence[CordCandidateRun],
    *,
    required_capture_ids: Sequence[str],
) -> CordCohortReport:
    """Require one generic method/configuration across an exact named cohort."""
    required = tuple(required_capture_ids)
    violations: list[CordViolation] = []
    actual_ids = tuple(_capture_id(run.record) for run in runs)
    if len(required) != len(set(required)) or set(actual_ids) != set(required) or len(actual_ids) != len(set(actual_ids)):
        _violation(
            violations,
            "cohort",
            "cohortCompleteness",
            "runs must cover every required capture identity exactly once",
        )
    method_identities = tuple(_method_identity(run.evidence) for run in runs)
    valid_identities = tuple(identity for identity in method_identities if identity[0] is not None)
    if len(valid_identities) != len(runs) or len(set(valid_identities)) != 1:
        _violation(
            violations,
            "cohort",
            "methodConfiguration",
            "every run must use the same method ID and normalized configuration",
        )
    method_id = valid_identities[0][0] if valid_identities else None
    method_intent = valid_identities[0][1] if valid_identities else None
    configuration_sha256 = valid_identities[0][2] if valid_identities else ""
    candidates = tuple(
        validate_cord_candidate(
            run.baseline_path,
            run.candidate_path,
            run.record,
            run.evidence,
        )
        for run in runs
    )
    return CordCohortReport(
        required_capture_ids=required,
        method_id=method_id,
        method_intent=method_intent,
        configuration_sha256=configuration_sha256,
        candidates=candidates,
        violations=tuple(violations),
    )


__all__ = [
    "CordCandidateReport",
    "CordCandidateRun",
    "CordCohortReport",
    "CordViolation",
    "load_cord_candidate_runs",
    "validate_cord_candidate",
    "validate_cord_method_cohort",
]
