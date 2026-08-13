"""Fail-closed promotion of an approved onboarding run into Hang Ten's Swift contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import unified_diff
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable, Mapping


_PROFILE_NAME = "ios-promotion-profile.json"
_TARGET_PATHS = (
    "HangTen/Models/GeneratedBoardCatalog.swift",
    "HangTen/Views/MetoliusCompactIIDesign.swift",
    "HangTen/Models/PlanStorage.swift",
    "HangTen/Resources/PlanLibrary.json",
)
_HOLD_KINDS = {"jug", "edge", "pocket", "sloper"}
_PATH_TOKEN = re.compile(r"([MLCQZ])|(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


@dataclass(frozen=True)
class IosPromotionProfile:
    schema_version: int
    board_id: str
    manufacturer: str
    name: str
    subtitle: str
    dimensions: str
    aspect_ratio: float
    product_url: str
    _source_bytes: bytes = field(default=b"", repr=False, compare=False)


@dataclass(frozen=True)
class PromotionFile:
    path: str
    current_text: str
    proposed_text: str
    unified_diff: str


@dataclass(frozen=True)
class PromotionIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class PromotionPreview:
    board_id: str
    revision_token: str
    base_ref: str
    files: tuple[PromotionFile, ...]
    issues: tuple[PromotionIssue, ...]
    preview_token: str
    _profile_bytes: bytes = field(default=b"", repr=False, compare=False)


@dataclass(frozen=True)
class PromotionSaveResult:
    board_id: str
    saved: bool
    paths: tuple[str, ...]
    revision_id: str | None = None


def read_promotion_profile(run_root: Path) -> IosPromotionProfile:
    """Read the explicit, versioned data that cannot be inferred from a photo."""
    path = run_root / _PROFILE_NAME
    raw = path.read_bytes()
    document = _read_object(path)
    expected_keys = {
        "schemaVersion", "boardID", "manufacturer", "name", "subtitle",
        "dimensions", "aspectRatio", "productURL",
    }
    if set(document) != expected_keys:
        raise ValueError(f"invalid iOS promotion profile keys in {path}")
    if document["schemaVersion"] != 1:
        raise ValueError("unsupported iOS promotion profile schemaVersion")
    string_fields = {
        "boardID": "board_id", "manufacturer": "manufacturer", "name": "name",
        "subtitle": "subtitle", "dimensions": "dimensions", "productURL": "product_url",
    }
    values: dict[str, Any] = {"schema_version": 1, "_source_bytes": raw}
    for source, destination in string_fields.items():
        value = document[source]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"iOS promotion profile {source} must be a non-empty string")
        values[destination] = value
    ratio = document["aspectRatio"]
    if (
        not isinstance(ratio, (int, float))
        or isinstance(ratio, bool)
        or not math.isfinite(ratio)
        or ratio <= 0
    ):
        raise ValueError("iOS promotion profile aspectRatio must be finite positive")
    values["aspect_ratio"] = float(ratio)
    return IosPromotionProfile(**values)


def build_promotion_preview(
    run_root: Path,
    repository_root: Path,
    profile: IosPromotionProfile,
    *,
    expected_base_ref: str = "main",
) -> PromotionPreview:
    """Render the four native artifacts without writing to the repository."""
    artifacts = _load_approved_artifacts(run_root)
    _assert_targets_at_base(repository_root, expected_base_ref)
    regions = _merge_regions(artifacts["stage2"], artifacts["stage3"], artifacts["stage4"])
    semantic_holds = _semantic_holds(regions)
    files = _render_files(repository_root, profile, artifacts, regions, semantic_holds)
    revision_token = _revision_token(artifacts)
    profile_bytes = _profile_bytes(profile)
    preview_token = _preview_token(
        profile.board_id, revision_token, expected_base_ref, profile_bytes, files
    )
    return PromotionPreview(
        board_id=profile.board_id,
        revision_token=revision_token,
        base_ref=expected_base_ref,
        files=files,
        issues=(),
        preview_token=preview_token,
        _profile_bytes=profile_bytes,
    )


def save_promotion_preview(
    preview: PromotionPreview,
    repository_root: Path,
    *,
    expected_preview_token: str,
) -> PromotionSaveResult:
    """Save an authenticated preview as one rollback-safe file transaction."""
    actual_preview_token = _preview_token(
        preview.board_id,
        preview.revision_token,
        preview.base_ref,
        preview._profile_bytes,
        preview.files,
    )
    if (
        preview.preview_token != expected_preview_token
        or actual_preview_token != preview.preview_token
    ):
        raise ValueError("preview token does not match the preview being saved")
    _assert_targets_at_base(repository_root, preview.base_ref)
    for item in preview.files:
        current = (repository_root / item.path).read_text(encoding="utf-8")
        if current != item.current_text:
            raise ValueError(f"target changed since preview: {item.path}")
    _replace_targets_transactionally(preview.files, repository_root)
    return PromotionSaveResult(
        board_id=preview.board_id,
        saved=True,
        paths=tuple(item.path for item in preview.files),
        revision_id=None,
    )


def _load_approved_artifacts(run_root: Path) -> dict[str, Any]:
    run = _read_object(run_root / "run.json")
    if run.get("schemaVersion") != 1:
        raise ValueError("unsupported onboarding run schema")
    pipeline = _object(run.get("pipeline"), "run pipeline")
    if pipeline.get("status") != "complete" or pipeline.get("currentStage") != 4:
        raise ValueError("onboarding run must be complete through Stage 4")
    stages = _list(run.get("stages"), "run stages")
    records: dict[int, Mapping[str, Any]] = {}
    for raw in stages:
        record = _object(raw, "stage record")
        stage = record.get("stage")
        if isinstance(stage, int):
            records[stage] = record
    documents: dict[str, Any] = {"run": run}
    for stage, label, filename in (
        (2, "stage2", "stage-2-regions.json"),
        (3, "stage3", "stage-3-vector-regions.json"),
        (4, "stage4", "stage-4-manifest.json"),
    ):
        record = records.get(stage)
        if record is None or record.get("status") != "approved" or record.get("machinePassed") is not True:
            raise ValueError(f"Stage {stage} must be approved before iOS promotion")
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
        documents[f"{label}_bytes"] = path.read_bytes()
    return documents


def _merge_regions(
    stage2: Mapping[str, Any], stage3: Mapping[str, Any], stage4: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    canvas = _object(stage2.get("canvas"), "Stage 2 canvas")
    width, height = _canvas(canvas)
    for label, document in (("Stage 3", stage3), ("Stage 4", stage4)):
        if _canvas(_object(document.get("canvas"), f"{label} canvas")) != (width, height):
            raise ValueError(f"{label} canvas does not match Stage 2")
    stage2_regions = _regions(stage2, "Stage 2")
    stage3_regions = _regions(stage3, "Stage 3")
    stage4_regions = _regions(stage4, "Stage 4")
    keyed3 = _keyed_regions(stage3_regions, "Stage 3")
    keyed4 = _keyed_regions(stage4_regions, "Stage 4")
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
            raise ValueError(f"unsupported Swift HoldKind: {kind}")
        if region.get("id") != vector.get("id") or region.get("id") != manifest.get("id"):
            raise ValueError(f"region ID mismatch for {key}")
        if region.get("type") != vector.get("type") or region.get("type") != manifest.get("type"):
            raise ValueError(f"region type mismatch for {key}")
        path = vector.get("displayPath")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Stage 3 displayPath is missing for {key}")
        bounds = manifest.get("bounds", region.get("bounds"))
        left, top, right, bottom = _bounds(bounds, key, width, height)
        result.append({
            "id": region["id"], "key": key, "kind": kind,
            "metadata": _object(region.get("metadata", {}), f"metadata for {key}"),
            "path": path, "frame": (left / width, top / height, (right - left) / width, (bottom - top) / height),
            "symmetry": vector.get("symmetry"),
        })
    if len(keyed3) != len(result) or len(keyed4) != len(result):
        raise ValueError("Stage 2, Stage 3, and Stage 4 region sets differ")
    return tuple(result)


def _render_files(
    repository_root: Path,
    profile: IosPromotionProfile,
    artifacts: Mapping[str, Any],
    regions: tuple[dict[str, Any], ...],
    semantic_holds: Mapping[str, tuple[str, ...]],
) -> tuple[PromotionFile, ...]:
    current = {path: (repository_root / path).read_text(encoding="utf-8") for path in _TARGET_PATHS}
    proposed = dict(current)
    proposed[_TARGET_PATHS[0]] = _replace_swift_declaration(
        current[_TARGET_PATHS[0]], "static let compactII = TrainingBoard(", _render_training_board(profile, regions)
    )
    proposed[_TARGET_PATHS[1]] = _replace_swift_declaration(
        current[_TARGET_PATHS[1]], "static let metoliusCompactII: BoardDesign = {", _render_design(profile, artifacts["stage4"], regions)
    )
    proposed[_TARGET_PATHS[2]] = _replace_swift_collection(
        current[_TARGET_PATHS[2]], "private static let semanticHoldIDs: [String: [String]] = [", _render_semantic_holds(semantic_holds)
    )
    proposed[_TARGET_PATHS[3]] = _render_plan_library(current[_TARGET_PATHS[3]], profile.board_id, semantic_holds)
    return tuple(
        PromotionFile(
            path=path,
            current_text=current[path],
            proposed_text=proposed[path],
            unified_diff="".join(unified_diff(
                current[path].splitlines(keepends=True), proposed[path].splitlines(keepends=True),
                fromfile=f"a/{path}", tofile=f"b/{path}",
            )),
        )
        for path in _TARGET_PATHS
    )


def _render_training_board(profile: IosPromotionProfile, regions: Iterable[Mapping[str, Any]]) -> str:
    lines = [
        "    static let compactII = TrainingBoard(",
        f"        id: {_swift_string(profile.board_id)},",
        f"        manufacturer: {_swift_string(profile.manufacturer)},",
        f"        name: {_swift_string(profile.name)},",
        f"        subtitle: {_swift_string(profile.subtitle)},",
        f"        dimensions: {_swift_string(profile.dimensions)},",
        f"        aspectRatio: {_number(profile.aspect_ratio)},",
        "        holds: [",
    ]
    for region in regions:
        lines.extend(_render_hold(region))
    lines.extend([
        "        ],",
        f"        productURL: URL(string: {_swift_string(profile.product_url)})!,",
        "        photoAssetName: nil",
        "    )",
    ])
    return "\n".join(lines)


def _render_hold(region: Mapping[str, Any]) -> list[str]:
    key = _string(region["key"], "hold key")
    kind = _string(region["kind"], "hold kind")
    metadata = _object(region["metadata"], f"metadata for {key}")
    x, y, width, height = region["frame"]
    depth = _optional_depth(metadata, key)
    finger_capacity = _finger_capacity(metadata, key, kind)
    name, label, detail = _hold_text(key, kind, depth, finger_capacity, metadata)
    lines = [
        "            BoardHold(",
        f"                id: {_swift_string(key)},",
        f"                name: {_swift_string(name)},",
        f"                shortLabel: {_swift_string(label)},",
        f"                detail: {_swift_string(detail)},",
        f"                kind: .{kind},",
        f"                frame: HoldFrame(x: {_number(x)}, y: {_number(y)}, width: {_number(width)}, height: {_number(height)}),",
    ]
    if depth is not None:
        lines.append(f"                sizeMillimeters: {depth},")
    grip = _grip_type(kind, finger_capacity)
    if grip is not None:
        lines.append(f"                gripType: .{grip},")
    features = _features(kind, depth, finger_capacity, metadata, key)
    if features:
        lines.append(f"                features: [{', '.join('.' + feature for feature in features)}]")
    else:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("            ),")
    return lines


def _render_design(profile: IosPromotionProfile, stage4: Mapping[str, Any], regions: tuple[dict[str, Any], ...]) -> str:
    silhouette_paths = _list(stage4.get("silhouettePaths"), "Stage 4 silhouettePaths")
    if len(silhouette_paths) != 1:
        raise ValueError("Stage 4 promotion requires exactly one silhouette path")
    silhouette_path = _string(_object(silhouette_paths[0], "Stage 4 silhouette").get("displayPath"), "Stage 4 silhouette displayPath")
    canvas_width, canvas_height = _canvas(_object(stage4.get("canvas"), "Stage 4 canvas"))
    lines = [
        "    static let metoliusCompactII: BoardDesign = {",
        f"        let silhouette = {_board_shape(silhouette_path, canvas_width, canvas_height)}",
        "        var holds: [BoardHoldPiece] = []",
        "",
        "        func addMirroredPair(",
        "            canonicalID: String, mirroredID: String, frame: CGRect, shape: BoardShape, treatment: BoardHoldTreatment",
        "        ) {",
        "            holds.append(BoardHoldPiece(id: canonicalID + \"-piece\", holdID: canonicalID, frame: frame, shape: shape, treatment: treatment))",
        "            holds.append(BoardHoldPiece(id: mirroredID + \"-piece\", holdID: mirroredID, frame: frame.mirroredHorizontally, shape: shape.mirroredHorizontally, treatment: treatment))",
        "        }",
        "",
    ]
    by_id = {region["id"]: region for region in regions}
    rendered: set[str] = set()
    for region in regions:
        key = _string(region["key"], "hold key")
        symmetry = region.get("symmetry")
        if isinstance(symmetry, Mapping) and symmetry.get("role") == "canonical":
            paired_id = symmetry.get("pair")
            counterpart = next((candidate for candidate in regions if isinstance(candidate.get("symmetry"), Mapping) and candidate["symmetry"].get("pair") == paired_id and candidate["symmetry"].get("role") == "mirrored"), None)
            if counterpart is None:
                raise ValueError(f"symmetric pair is incomplete for {key}")
            lines.extend(_render_mirrored_piece(region, counterpart, canvas_width, canvas_height))
            rendered.update({_string(region["key"], "hold key"), _string(counterpart["key"], "hold key")})
        elif isinstance(symmetry, Mapping) and symmetry.get("role") == "mirrored":
            continue
        elif symmetry is not None:
            raise ValueError(f"unsupported symmetry record for {key}")
    for region in regions:
        key = _string(region["key"], "hold key")
        if key not in rendered:
            lines.extend(_render_piece(region, canvas_width, canvas_height))
    lines.extend([
        "        return BoardDesign(",
        f"            id: {_swift_string(profile.board_id)},",
        "            canvasFrame: CGRect(x: 0, y: 0, width: 1, height: 1),",
        "            silhouette: silhouette,",
        "            layers: [],",
        "            holds: holds,",
        "            palette: .sculptedWood",
        "        )",
        "    }()",
    ])
    return "\n".join(lines)


def _render_piece(region: Mapping[str, Any], canvas_width: int, canvas_height: int) -> list[str]:
    key = _string(region["key"], "hold key")
    x, y, width, height = region["frame"]
    return [
        "        holds.append(",
        "            BoardHoldPiece(",
        f"                id: {_swift_string(key + '-piece')},",
        f"                holdID: {_swift_string(key)},",
        f"                frame: CGRect(x: {_number(x)}, y: {_number(y)}, width: {_number(width)}, height: {_number(height)}),",
        f"                shape: {_board_shape(_string(region['path'], 'Stage 3 displayPath'), canvas_width, canvas_height)},",
        f"                treatment: {_treatment(region)}",
        "            )",
        "        )",
    ]


def _render_mirrored_piece(
    canonical: Mapping[str, Any], mirrored: Mapping[str, Any], canvas_width: int, canvas_height: int
) -> list[str]:
    key = _string(canonical["key"], "hold key")
    pair_key = _string(mirrored["key"], "hold key")
    x, y, width, height = canonical["frame"]
    return [
        "        addMirroredPair(",
        f"            canonicalID: {_swift_string(key)}, mirroredID: {_swift_string(pair_key)},",
        f"            frame: CGRect(x: {_number(x)}, y: {_number(y)}, width: {_number(width)}, height: {_number(height)}),",
        f"            shape: {_board_shape(_string(canonical['path'], 'Stage 3 displayPath'), canvas_width, canvas_height)},",
        f"            treatment: {_treatment(canonical)}",
        "        )",
    ]


def _render_semantic_holds(semantic_holds: Mapping[str, tuple[str, ...]]) -> str:
    lines = ["    private static let semanticHoldIDs: [String: [String]] = ["]
    for semantic, hold_ids in semantic_holds.items():
        lines.append(f"        {_swift_string(semantic)}: [{', '.join(_swift_string(hold_id) for hold_id in hold_ids)}],")
    lines.append("    ]")
    return "\n".join(lines)


def _render_plan_library(current: str, board_id: str, semantic_holds: Mapping[str, tuple[str, ...]]) -> str:
    document = json.loads(current)
    mappings = _list(document.get("boardMappings"), "PlanLibrary boardMappings")
    identity = board_id.replace(".", "-")
    matching_mappings: list[tuple[int, dict[str, Any]]] = []
    for index, value in enumerate(mappings):
        candidate = dict(_object(value, f"PlanLibrary board mapping {index}"))
        candidate_board_id = _string(
            candidate.get("boardID"), f"PlanLibrary board mapping {index} board ID"
        )
        if candidate_board_id.replace(".", "-") == identity:
            matching_mappings.append((index, candidate))
    if len(matching_mappings) != 1:
        raise ValueError("PlanLibrary must contain exactly one board mapping for the active board identity")
    mapping_index, mapping = matching_mappings[0]
    previous_board_id = _string(mapping.get("boardID"), "PlanLibrary board ID")
    if mapping.get("semanticHolds") is None:
        raise ValueError("PlanLibrary board mapping anchor is missing semanticHolds")
    mapping_spans = _json_board_mapping_spans(current)
    if len(mapping_spans) != len(mappings):
        raise ValueError("PlanLibrary board mapping anchors do not match parsed mappings")
    anchor_start, anchor_end = mapping_spans[mapping_index]
    if json.dumps(previous_board_id) not in current[anchor_start:anchor_end]:
        raise ValueError("PlanLibrary board ID anchor is absent")
    mapping["boardID"] = board_id
    mapping["semanticHolds"] = {key: {"holdIDs": list(value)} for key, value in semantic_holds.items()}
    replacement = _indent_json(mapping, 4)
    return current[:anchor_start] + replacement + current[anchor_end:]


def _json_board_mapping_spans(source: str) -> list[tuple[int, int]]:
    matches = list(re.finditer(r'"boardMappings"\s*:\s*\[', source))
    if len(matches) != 1:
        raise ValueError("PlanLibrary board mapping anchor is absent")
    cursor = matches[0].end()
    decoder = json.JSONDecoder()
    spans: list[tuple[int, int]] = []
    expect_mapping = True
    while True:
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source):
            raise ValueError("PlanLibrary board mapping anchor is invalid")
        if source[cursor] == "]":
            if expect_mapping and spans:
                raise ValueError("PlanLibrary board mapping anchor is invalid")
            return spans
        if not expect_mapping or source[cursor] != "{":
            raise ValueError("PlanLibrary board mapping anchor is invalid")
        start = cursor
        try:
            value, end = decoder.raw_decode(source[start:])
        except json.JSONDecodeError as error:
            raise ValueError("PlanLibrary board mapping anchor is invalid") from error
        if not isinstance(value, dict):
            raise ValueError("PlanLibrary board mapping anchor is invalid")
        cursor = start + end
        spans.append((start, cursor))
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source):
            raise ValueError("PlanLibrary board mapping anchor is invalid")
        if source[cursor] == "]":
            return spans
        if source[cursor] != ",":
            raise ValueError("PlanLibrary board mapping anchor is invalid")
        cursor += 1
        expect_mapping = True


def _semantic_holds(regions: Iterable[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
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
            semantic = {"flat": "flat-slopers", "round": "round-sloper"}.get(profile, "")
            if not semantic:
                raise ValueError(f"unsupported sloper profile for {key}: {profile}")
        elif kind == "edge" and depth is not None:
            semantic = f"edge-{depth}"
        elif kind == "pocket" and depth is not None and fingers is not None:
            word = {2: "two", 3: "three", 4: "four"}.get(fingers)
            if word is None:
                raise ValueError(f"unsupported fingerCapacity for {key}: {fingers}")
            semantic = f"pocket-{depth}-{word}"
        else:
            raise ValueError(f"cannot derive a semantic mapping for {key}")
        result.setdefault(semantic, []).append(key)
    return {key: tuple(value) for key, value in result.items()}


def _board_shape(path: str, canvas_width: int, canvas_height: int) -> str:
    commands = _svg_commands(path)
    rendered: list[str] = []
    for command, points in commands:
        if command == "M":
            rendered.append(f".move(CGPoint(x: {_number(points[0] / canvas_width)}, y: {_number(points[1] / canvas_height)}))")
        elif command == "L":
            rendered.append(f".line(CGPoint(x: {_number(points[0] / canvas_width)}, y: {_number(points[1] / canvas_height)}))")
        elif command == "Q":
            rendered.append(
                f".quad(to: CGPoint(x: {_number(points[2] / canvas_width)}, y: {_number(points[3] / canvas_height)}), control: CGPoint(x: {_number(points[0] / canvas_width)}, y: {_number(points[1] / canvas_height)}))"
            )
        elif command == "C":
            rendered.append(
                f".curve(to: CGPoint(x: {_number(points[4] / canvas_width)}, y: {_number(points[5] / canvas_height)}), control1: CGPoint(x: {_number(points[0] / canvas_width)}, y: {_number(points[1] / canvas_height)}), control2: CGPoint(x: {_number(points[2] / canvas_width)}, y: {_number(points[3] / canvas_height)}))"
            )
        else:
            rendered.append(".close")
    return "BoardShape.path(BoardNormalizedPath(commands: [" + ", ".join(rendered) + "]))"


def _svg_commands(path: str) -> tuple[tuple[str, tuple[float, ...]], ...]:
    tokens = [command or number for command, number in _PATH_TOKEN.findall(path)]
    if not tokens or "".join(tokens) != re.sub(r"[\s,]+", "", path):
        raise ValueError("Stage 3 displayPath contains unsupported SVG syntax")
    arity = {"M": 2, "L": 2, "Q": 4, "C": 6, "Z": 0}
    index = 0
    result: list[tuple[str, tuple[float, ...]]] = []
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command not in arity:
            raise ValueError(f"unsupported SVG command: {command}")
        count = arity[command]
        if index + count > len(tokens):
            raise ValueError("truncated Stage 3 displayPath")
        if count == 0:
            result.append((command, ()))
            continue
        values = tokens[index:index + count]
        if any(value in arity for value in values):
            raise ValueError("Stage 3 displayPath command is incomplete")
        index += count
        result.append((command, tuple(float(value) for value in values)))
    return tuple(result)


def _treatment(region: Mapping[str, Any]) -> str:
    key = _string(region["key"], "hold key")
    kind = _string(region["kind"], "hold kind")
    if kind in {"jug", "sloper"}:
        return ".surface"
    if kind == "edge":
        return ".shelf(.broadJug)"
    depth = _optional_depth(_object(region["metadata"], f"metadata for {key}"), key)
    if depth == 29:
        return ".recess(.deepSlot)"
    if depth == 19:
        return ".recess(.shallowSlot)"
    raise ValueError(f"unsupported pocket depth for treatment: {key}")


def _hold_text(key: str, kind: str, depth: int | None, fingers: int | None, metadata: Mapping[str, Any]) -> tuple[str, str, str]:
    if kind == "jug":
        return (key, "J", "Open-hand jug")
    if kind == "edge" and depth is not None:
        return (key, f"{depth}E", f"{depth} mm edge")
    if kind == "pocket" and depth is not None and fingers is not None:
        return (key, f"{depth}·{fingers}", f"{fingers}-finger pocket")
    if kind == "sloper" and depth is not None:
        profile = _string(metadata.get("profile"), f"sloper profile for {key}")
        label = {"flat": "F", "round": "R"}.get(profile)
        if label is None:
            raise ValueError(f"unsupported sloper profile for {key}: {profile}")
        return (key, f"{depth}{label}", f"{profile.title()} open-hand sloper")
    raise ValueError(f"cannot render text for {key}")


def _features(kind: str, depth: int | None, fingers: int | None, metadata: Mapping[str, Any], key: str) -> tuple[str, ...]:
    if kind == "jug":
        return ("jug",)
    if kind == "pocket" and fingers is not None:
        return ("pocket", {2: "twoFingerPocket", 3: "threeFingerPocket", 4: "fourFingerPocket"}[fingers])
    if kind == "sloper":
        profile = _string(metadata.get("profile"), f"sloper profile for {key}")
        return {"flat": ("largeSlope",), "round": ("roundSloper",)}.get(profile, ())
    if kind == "edge":
        if depth == 29:
            return ("largeEdge",)
        if depth == 19:
            return ("mediumEdge", "smallEdge")
    raise ValueError(f"unsupported Swift HoldFeature values for {key}")


def _grip_type(kind: str, fingers: int | None) -> str | None:
    if kind == "sloper":
        return "sloper"
    if kind == "pocket":
        return {2: "twoFingerPocket", 3: "threeFingerPocket", 4: "fourFingerPocket"}.get(fingers)
    return None


def _optional_depth(metadata: Mapping[str, Any], key: str) -> int | None:
    value = metadata.get("depthMm")
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"depthMm must be a positive integer for {key}")
    return value


def _finger_capacity(metadata: Mapping[str, Any], key: str, kind: str) -> int | None:
    value = metadata.get("fingerCount")
    if kind != "pocket":
        if value is not None:
            raise ValueError(f"fingerCount is only supported for pockets: {key}")
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value not in {2, 3, 4}:
        raise ValueError(f"unsupported fingerCapacity for {key}")
    return value


def _replace_swift_declaration(source: str, anchor: str, replacement: str) -> str:
    if source.count(anchor) != 1:
        raise ValueError(f"Swift anchor is absent or duplicated: {anchor}")
    start = source.index(anchor)
    opening = start + len(anchor) - 1
    if source[opening] == "(":
        end = _matching_delimiter(source, opening, "(", ")")
        return source[:start] + replacement + source[end + 1:]
    if source[opening] == "{":
        end = _matching_delimiter(source, opening, "{", "}")
        if source[end + 1:end + 3] != "()":
            raise ValueError(f"Swift declaration anchor is not a closure: {anchor}")
        return source[:start] + replacement + source[end + 3:]
    raise ValueError(f"Swift declaration anchor has an unsupported delimiter: {anchor}")


def _replace_swift_collection(source: str, anchor: str, replacement: str) -> str:
    if source.count(anchor) != 1:
        raise ValueError(f"Swift anchor is absent or duplicated: {anchor}")
    start = source.index(anchor)
    opening = start + len(anchor) - 1
    end = _matching_delimiter(source, opening, "[", "]")
    return source[:start] + replacement + source[end + 1:]


def _matching_delimiter(source: str, opening: int, left: str, right: str) -> int:
    depth = 0
    for index in range(opening, len(source)):
        character = source[index]
        if character == left:
            depth += 1
        elif character == right:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unterminated native anchor")


def _assert_targets_at_base(repository_root: Path, expected_base_ref: str) -> None:
    validation = subprocess.run(
        ["git", "-C", str(repository_root), "check-ref-format", "--allow-onelevel", expected_base_ref],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if validation.returncode != 0:
        raise ValueError(f"invalid base ref: {expected_base_ref}")
    for path in _TARGET_PATHS:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "diff", "--quiet", expected_base_ref, "--", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if result.returncode == 1:
            raise ValueError(f"target changed relative to {expected_base_ref}: {path}")
        if result.returncode != 0:
            raise ValueError(f"cannot verify target against {expected_base_ref}: {path}")


def _revision_token(artifacts: Mapping[str, Any]) -> str:
    digest = sha256()
    digest.update(_canonical_json(artifacts["run"]))
    for label in ("stage2_bytes", "stage3_bytes", "stage4_bytes"):
        digest.update(artifacts[label])
    return digest.hexdigest()


def _replace_targets_transactionally(
    files: Iterable[PromotionFile], repository_root: Path
) -> None:
    transaction_root = Path(tempfile.mkdtemp(prefix=".hangboard-promotion-", dir=repository_root))
    staged_root = transaction_root / "staged"
    backup_root = transaction_root / "backup"
    file_items = tuple(files)
    backups: list[tuple[Path, Path]] = []
    try:
        for item in file_items:
            staged = staged_root / item.path
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(item.proposed_text, encoding="utf-8")
        for item in file_items:
            target = repository_root / item.path
            staged = staged_root / item.path
            backup = backup_root / item.path
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            backups.append((target, backup))
            os.replace(staged, target)
    except Exception:
        rollback_error: Exception | None = None
        for target, backup in reversed(backups):
            if not backup.exists():
                continue
            try:
                os.replace(backup, target)
            except Exception as restore_error:  # pragma: no cover - catastrophic filesystem failure
                rollback_error = restore_error
                break
        if rollback_error is not None:
            raise RuntimeError("promotion save failed and rollback could not restore all targets") from rollback_error
        raise
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)


def _profile_bytes(profile: IosPromotionProfile) -> bytes:
    return profile._source_bytes or _canonical_json({
        "schemaVersion": profile.schema_version, "boardID": profile.board_id,
        "manufacturer": profile.manufacturer, "name": profile.name, "subtitle": profile.subtitle,
        "dimensions": profile.dimensions, "aspectRatio": profile.aspect_ratio, "productURL": profile.product_url,
    })


def _preview_token(
    board_id: str,
    revision_token: str,
    base_ref: str,
    profile_bytes: bytes,
    files: Iterable[PromotionFile],
) -> str:
    digest = sha256()
    digest.update(board_id.encode())
    digest.update(revision_token.encode())
    digest.update(base_ref.encode())
    digest.update(profile_bytes)
    for item in files:
        digest.update(item.path.encode())
        digest.update(item.proposed_text.encode())
    return digest.hexdigest()


def _regions(document: Mapping[str, Any], label: str) -> list[Mapping[str, Any]]:
    return [_object(item, f"{label} region") for item in _list(document.get("regions"), f"{label} regions")]


def _keyed_regions(regions: Iterable[Mapping[str, Any]], label: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for region in regions:
        key = _string(region.get("key"), f"{label} region key")
        if key in result:
            raise ValueError(f"duplicate hold ID: {key}")
        result[key] = region
    return result


def _canvas(canvas: Mapping[str, Any]) -> tuple[int, int]:
    width, height = canvas.get("width"), canvas.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("canvas must have positive integer dimensions")
    return width, height


def _bounds(value: object, key: str, width: int, height: int) -> tuple[float, float, float, float]:
    values = _list(value, f"bounds for {key}")
    if len(values) != 4 or any(not isinstance(item, (int, float)) for item in values):
        raise ValueError(f"bounds are invalid for {key}")
    left, top, right, bottom = (float(item) for item in values)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"bounds are outside the canvas for {key}")
    return left, top, right, bottom


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
        raise ValueError(f"required promotion artifact is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid promotion JSON: {path}") from error
    return _object(value, str(path))


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _indent_json(value: object, spaces: int) -> str:
    prefix = " " * spaces
    return prefix + json.dumps(value, ensure_ascii=False, indent=2).replace("\n", "\n" + prefix)


def _swift_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
