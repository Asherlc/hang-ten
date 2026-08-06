"""Transactional Stage 4 publication from accepted Stage 1--3 evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Mapping
import xml.etree.ElementTree as ET

import cv2
import numpy as np

from .display_paths import DisplayPath, parse_display_path
from .stage4_composition import Stage4Candidate, compose_stage4
from .vector_smoothing import (
    OpenPath, VectorizationProfile, _ordered_seam, _piece_masks,
    display_path_contains_open_path, parse_open_path_data, rasterize_display_path,
    rasterize_paths_half_open, rasterize_paths_independent, validate_display_path,
)


_CANDIDATE_NAMES = (
    "stage-4-product.svg", "stage-4-manifest.json", "stage-4-normal.png",
    "stage-4-highlight-jugs.png", "stage-4-highlight-slopers.png",
    "stage-4-highlight-symmetric-pockets.png", "stage-4-highlight-mixed.png",
    "stage-4-highlight-all.png", "stage-4-highlights.json",
)


@dataclass(frozen=True, slots=True)
class Stage4EvidenceInputs:
    stage1_acceptance_path: Path
    stage1_rgba_path: Path
    stage2_acceptance_path: Path
    stage3_acceptance_path: Path
    stage3_regions_path: Path
    stage3_svg_path: Path

    @classmethod
    def from_roots(cls, stage1_root: Path, stage2_root: Path, stage3_root: Path) -> "Stage4EvidenceInputs":
        return cls(stage1_root / "stage-1-acceptance.json", stage1_root / "stage-1-auto-rgba.png", stage2_root / "stage-2-acceptance.json", stage3_root / "stage-3-acceptance.json", stage3_root / "stage-3-vector-regions.json", stage3_root / "stage-3-vector.svg")


def run_stage4_onboarding(
    evidence: Stage4EvidenceInputs, artifact_root: Path, *, manual_oracle_path: Path | None = None,
    browser_oracle_path: Path | None = None, oracle_paths: Mapping[str, str] | None = None,
    comparison_policy: str | None = None,
) -> Mapping[str, object]:
    """Validate provenance, finalize bytes before oracle access, then publish atomically."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"stage 4 artifact root already exists: {artifact_root}")
    if comparison_policy not in {None, "beastmaker-v14"}:
        raise ValueError(f"unsupported Stage 4 comparison policy: {comparison_policy}")
    source_png, document, stage3_digest, stage3_acceptance = _validate_evidence(evidence)
    beastmaker_mode = oracle_paths is not None or comparison_policy == "beastmaker-v14"
    first, second = compose_stage4(source_png, document), compose_stage4(source_png, document)
    if first != second:
        raise ValueError("Stage 4 composition is nondeterministic")
    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    lock_path = artifact_root.parent / f".{artifact_root.name}.publish.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise FileExistsError(f"stage 4 publication is already in progress: {artifact_root}") from error
    temporary: Path | None = None
    try:
        temporary = Path(mkdtemp(prefix=f".{artifact_root.name}.", dir=artifact_root.parent))
        try:
            _write_candidate(temporary, first)
            evaluator = importlib.import_module("hangboard_vectorizer.stage4_evaluation")
            acceptance = evaluator.evaluate_stage4_candidate(
                temporary, source_png=source_png, stage3_document=document,
                stage3_acceptance_raw_sha256=stage3_digest, manual_oracle_path=manual_oracle_path,
                browser_oracle_path=browser_oracle_path, oracle_paths=oracle_paths,
                # Generic composition validates only its supplied evidence.  The
                # Beastmaker/V14 contract is an explicit comparison mode, never a
                # hidden dependency of a portable Stage 4 candidate.
                stage3_acceptance=stage3_acceptance if beastmaker_mode else None,
            )
            if artifact_root.exists():
                raise FileExistsError(f"stage 4 artifact root already exists: {artifact_root}")
            temporary.rename(artifact_root)
            temporary = None
        except Exception:
            if temporary is not None:
                rmtree(temporary, ignore_errors=True)
            raise
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)
    return acceptance


def _validate_evidence(evidence: Stage4EvidenceInputs) -> tuple[bytes, dict[str, object], str, dict[str, object]]:
    paths = tuple(getattr(evidence, field.name) for field in fields(evidence))
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("required accepted Stage 1--3 evidence is missing")
    if (evidence.stage1_rgba_path.name, evidence.stage3_regions_path.name, evidence.stage3_svg_path.name) != ("stage-1-auto-rgba.png", "stage-3-vector-regions.json", "stage-3-vector.svg"):
        raise ValueError("Stage 4 evidence filenames are invalid")
    stage1_raw = evidence.stage1_acceptance_path.read_bytes()
    stage2_raw = evidence.stage2_acceptance_path.read_bytes()
    stage3_raw = evidence.stage3_acceptance_path.read_bytes()
    stage1, stage2, stage3 = (_json(value, name) for value, name in ((stage1_raw, "Stage 1 acceptance"), (stage2_raw, "Stage 2 acceptance"), (stage3_raw, "Stage 3 acceptance")))
    if stage1.get("accepted") is not True or stage1.get("stage") != 1 or stage2.get("accepted") is not True or stage2.get("stage") != 2 or stage3.get("accepted") is not True or stage3.get("stage") != 3:
        raise ValueError("Stage 4 requires accepted Stage 1, Stage 2, and Stage 3 evidence")
    source_png = evidence.stage1_rgba_path.read_bytes()
    validation = stage1.get("validation")
    source_pixel_sha = _rgba_pixel_sha(source_png)
    if (not isinstance(validation, dict) or not isinstance(validation.get("pngFileSha256"), dict)
            or validation["pngFileSha256"].get("automatedRgba") != sha256(source_png).hexdigest()
            or validation.get("automatedRgbaPixelSha256") != source_pixel_sha):
        raise ValueError("accepted Stage 1 RGBA was changed")
    generation = stage2.get("generationEvidence")
    if not isinstance(generation, dict) or generation.get("stage1AcceptanceRawSha256") != sha256(stage1_raw).hexdigest():
        raise ValueError("Stage 2 provenance does not match Stage 1 acceptance")
    stage2_hashes = stage2.get("candidateHashes")
    if not isinstance(stage2_hashes, dict):
        raise ValueError("Stage 2 candidate hashes are invalid")
    # The Stage 2 source is selected by the accepted artifact name, and its hash
    # must bind to the Stage 1 visible PNG, not merely share the same filename.
    source_entry = evidence.stage2_acceptance_path.parent / "stage-2-source-rgba.png"
    if not source_entry.is_file() or stage2_hashes.get(source_entry.name) != sha256(source_entry.read_bytes()).hexdigest():
        raise ValueError("accepted Stage 2 source evidence was changed")
    if generation.get("stage1PixelSha256") != source_pixel_sha or _rgba_pixel_sha(source_entry.read_bytes()) != source_pixel_sha:
        raise ValueError("Stage 2 source does not match accepted Stage 1 RGBA")
    stage3_hashes = stage3.get("candidateHashes")
    if not isinstance(stage3_hashes, dict):
        raise ValueError("Stage 3 candidate hashes are invalid")
    for path in (evidence.stage3_regions_path, evidence.stage3_svg_path):
        if stage3_hashes.get(path.name) != sha256(path.read_bytes()).hexdigest():
            raise ValueError(f"accepted Stage 3 evidence was changed: {path.name}")
    document = _json(evidence.stage3_regions_path.read_bytes(), "Stage 3 regions")
    if document.get("stage2AcceptanceRawSha256") != sha256(stage2_raw).hexdigest():
        raise ValueError("Stage 3 provenance does not match Stage 2 acceptance")
    _validate_stage3_geometry(document, source_png)
    candidate = compose_stage4(source_png, document)
    _validate_stage3_svg(evidence.stage3_svg_path, document, candidate.width, candidate.height)
    return source_png, document, sha256(stage3_raw).hexdigest(), stage3


def _validate_stage3_svg(path: Path, document: Mapping[str, object], width: int, height: int) -> None:
    try:
        root = ET.fromstring(path.read_bytes())
    except ET.ParseError as error:
        raise ValueError("accepted Stage 3 SVG is invalid") from error
    ns = "{http://www.w3.org/2000/svg}"
    if (root.tag != ns + "svg" or root.get("width") != str(width)
            or root.get("height") != str(height)
            or root.get("viewBox") != f"0 0 {width} {height}"):
        raise ValueError("accepted Stage 3 SVG dimensions mismatch")
    paths = root.findall(ns + "path")
    pieces = document.get("pieces")
    regions = document.get("regions")
    if not isinstance(pieces, list) or not isinstance(regions, list) or len(paths) != len(regions) + len(pieces):
        raise ValueError("accepted Stage 3 SVG region count mismatch")
    piece_paths, region_paths = paths[:len(pieces)], paths[len(pieces):]
    owners: dict[int, str] = {}
    for index, (item, element) in enumerate(zip(pieces, piece_paths, strict=True)):
        if (not isinstance(item, dict) or item.get("pieceIndex") != index
                or item.get("id") != f"piece-{index + 1:02d}-silhouette"
                or (element.get("id"), element.get("data-type"), element.get("d"))
                != (item.get("id"), "piece-silhouette", item.get("displayPath"))):
            raise ValueError("accepted Stage 3 SVG piece parity mismatch")
        owners[index] = item["id"]
    for item, element in zip(regions, region_paths, strict=True):
        if (not isinstance(item, dict) or type(item.get("pieceIndex")) is not int
                or item["pieceIndex"] not in owners
                or (element.get("id"), element.get("data-type"), element.get("d"))
                != (item.get("id"), item.get("type"), item.get("displayPath"))):
            raise ValueError("accepted Stage 3 SVG region parity mismatch")


def _validate_stage3_geometry(document: Mapping[str, object], source_png: bytes) -> None:
    """Semantically validate Stage 3 paths and canonical seams without oracle access."""
    rgba = _decode_rgba(source_png)
    height, width = rgba.shape[:2]
    profile_value = document.get("profile")
    if not isinstance(profile_value, dict) or set(profile_value) != set(asdict(VectorizationProfile())):
        raise ValueError("accepted Stage 3 vector profile is invalid")
    try:
        profile = VectorizationProfile(**profile_value)
    except (TypeError, ValueError) as error:
        raise ValueError("accepted Stage 3 vector profile is invalid") from error
    pieces_value, regions_value = document.get("pieces"), document.get("regions")
    if not isinstance(pieces_value, list) or not isinstance(regions_value, list) or not pieces_value:
        raise ValueError("accepted Stage 3 geometry is incomplete")
    raw_pieces = _piece_masks(rgba[..., 3], len(pieces_value))
    pieces: dict[str, DisplayPath] = {}
    piece_rasters: dict[str, np.ndarray] = {}
    for index, (item, raw) in enumerate(zip(pieces_value, raw_pieces, strict=True)):
        if not isinstance(item, dict) or item.get("pieceIndex") != index:
            raise ValueError("accepted Stage 3 piece geometry is invalid")
        identifier = item.get("id")
        path = parse_display_path(item.get("displayPath"), str(identifier), width, height, allow_linear_segments=True)
        if not isinstance(identifier, str) or path is None:
            raise ValueError("accepted Stage 3 piece geometry is invalid")
        basis = float(min(_bbox_size(raw)))
        validate_display_path(path, scale_basis=basis, profile=profile)
        output = rasterize_display_path(path, width, height)
        if (not np.any(output) or item.get("rawMaskSha256") != sha256(raw.tobytes()).hexdigest()
                or item.get("outputMaskSha256") != sha256(output.tobytes()).hexdigest()
                or _iou(raw, output) < .98):
            raise ValueError("accepted Stage 3 piece path does not match source alpha")
        pieces[identifier], piece_rasters[identifier] = path, output
    regions: dict[str, DisplayPath] = {}
    ordered_paths: list[DisplayPath] = []
    for item in regions_value:
        if not isinstance(item, dict) or type(item.get("pieceIndex")) is not int or item["pieceIndex"] not in range(len(pieces_value)):
            raise ValueError("accepted Stage 3 region ownership is invalid")
        identifier = item.get("id")
        path = parse_display_path(item.get("displayPath"), str(identifier), width, height, allow_linear_segments=True)
        if not isinstance(identifier, str) or identifier in regions or path is None:
            raise ValueError("accepted Stage 3 region geometry is invalid")
        independent = rasterize_display_path(path, width, height)
        if not np.any(independent):
            raise ValueError("accepted Stage 3 region path is degenerate")
        validate_display_path(path, scale_basis=float(min(_bbox_size(independent))), profile=profile)
        owner = pieces_value[item["pieceIndex"]]["id"]
        if np.any(independent.astype(bool) & ~piece_rasters[owner].astype(bool)):
            raise ValueError("accepted Stage 3 region leaves its assigned piece")
        regions[identifier] = path
        ordered_paths.append(path)
    owned = rasterize_paths_half_open(tuple(ordered_paths), width, height)
    for item, mask in zip(regions_value, owned, strict=True):
        if item.get("outputMaskSha256") != sha256(mask.tobytes()).hexdigest():
            raise ValueError("accepted Stage 3 region mask identity is invalid")
    _validate_stage3_seams(document, pieces, regions, piece_rasters, width, height)


def _validate_stage3_seams(
    document: Mapping[str, object], pieces: Mapping[str, DisplayPath],
    regions: Mapping[str, DisplayPath], piece_rasters: Mapping[str, np.ndarray],
    width: int, height: int,
) -> None:
    values = document.get("canonicalSeams")
    if not isinstance(values, list):
        raise ValueError("accepted Stage 3 canonical seams are invalid")
    entities = {**pieces, **regions}
    memberships: dict[str, set[str]] = {identifier: set() for identifier in entities}
    declared_pairs: set[frozenset[str]] = set()
    for index, item in enumerate(values, start=1):
        if (not isinstance(item, dict) or item.get("id") != f"seam-{index:03d}"
                or item.get("kind") not in {"piece", "region"}
                or item.get("firstId") not in entities or item.get("secondId") not in entities):
            raise ValueError("accepted Stage 3 canonical seam identity is invalid")
        seam = parse_open_path_data(item.get("path"), width, height)
        if item.get("reversePath") != seam.reversed().data:
            raise ValueError("accepted Stage 3 canonical seam reverse path is invalid")
        raw = item.get("rawCoordinates")
        if not isinstance(raw, list) or len(raw) < 2 or any(not isinstance(point, list) or len(point) != 2 for point in raw):
            raise ValueError("accepted Stage 3 canonical seam coordinates are invalid")
        raw_points = tuple((float(point[0]), float(point[1])) for point in raw)
        raw_edges = {tuple(sorted((first, second))) for first, second in zip(raw_points, raw_points[1:])}
        if raw_points[0] != seam.start or raw_points[-1] != seam.end or _ordered_seam(raw_edges) not in {raw_points, tuple(reversed(raw_points))}:
            raise ValueError("accepted Stage 3 canonical seam path identity is invalid")
        first, second = item["firstId"], item["secondId"]
        if not display_path_contains_open_path(entities[first], seam):
            raise ValueError("accepted Stage 3 seam is absent from its first owner")
        second_seam: OpenPath = seam.reversed() if item["kind"] == "region" else seam
        if not display_path_contains_open_path(entities[second], second_seam):
            raise ValueError("accepted Stage 3 seam is absent from its second owner")
        memberships[first].add(item["id"])
        memberships[second].add(item["id"])
        declared_pairs.add(frozenset((first, second)))
    for collection in (document["pieces"], document["regions"]):
        assert isinstance(collection, list)
        for item in collection:
            assert isinstance(item, dict)
            shared = item.get("sharedSeamIds")
            if not isinstance(shared, list) or len(shared) != len(set(shared)) or set(shared) != memberships[item["id"]]:
                raise ValueError("accepted Stage 3 shared seam membership is invalid")
    expected_pairs = _expected_stage3_seam_pairs(document, pieces, regions, piece_rasters, width, height)
    if declared_pairs != expected_pairs:
        raise ValueError("accepted Stage 3 canonical seam set is incomplete")


def _expected_stage3_seam_pairs(
    document: Mapping[str, object], pieces: Mapping[str, DisplayPath],
    regions: Mapping[str, DisplayPath], piece_rasters: Mapping[str, np.ndarray],
    width: int, height: int,
) -> set[frozenset[str]]:
    scale = 4
    kernel = np.ones((3, 3), dtype=np.uint8)
    region_values = document["regions"]
    assert isinstance(region_values, list)
    surfaces = [item for item in region_values if isinstance(item, dict) and item.get("type") != "pocket"]
    rasters = rasterize_paths_independent(tuple(regions[item["id"]] for item in surfaces), width, height, scale=scale)
    boundaries = {item["id"]: _boundary(mask) for item, mask in zip(surfaces, rasters, strict=True)}
    result: set[frozenset[str]] = set()
    for position, first in enumerate(surfaces):
        for second in surfaces[position + 1:]:
            if first["pieceIndex"] != second["pieceIndex"]:
                continue
            touching = cv2.dilate(boundaries[first["id"]], kernel) & boundaries[second["id"]]
            if np.count_nonzero(touching) >= 4:
                result.add(frozenset((first["id"], second["id"])))
        owner = document["pieces"][first["pieceIndex"]]["id"]
        piece_high = cv2.resize(piece_rasters[owner], (width * scale, height * scale), interpolation=cv2.INTER_NEAREST)
        if np.count_nonzero(boundaries[first["id"]] & _boundary(piece_high)) >= 4:
            result.add(frozenset((first["id"], owner)))
    return result


def _write_candidate(root: Path, candidate: Stage4Candidate) -> None:
    highlights = dict(candidate.highlight_pngs)
    values: dict[str, bytes] = {
        "stage-4-product.svg": candidate.svg,
        "stage-4-manifest.json": candidate.manifest,
        "stage-4-normal.png": candidate.normal_png,
        "stage-4-highlight-jugs.png": highlights["jugs"],
        "stage-4-highlight-slopers.png": highlights["slopers"],
        "stage-4-highlight-symmetric-pockets.png": highlights["symmetric-pockets"],
        "stage-4-highlight-mixed.png": highlights["mixed"],
        "stage-4-highlight-all.png": highlights["all"],
        "stage-4-highlights.json": candidate.highlight_manifest,
    }
    if tuple(values) != _CANDIDATE_NAMES:
        raise ValueError("Stage 4 candidate names are invalid")
    for name, data in values.items():
        (root / name).write_bytes(data)
    _write_json(root / "stage-4-candidate-hashes.json", {"files": {name: sha256(values[name]).hexdigest() for name in _CANDIDATE_NAMES}, "schemaVersion": 1})


def _rgba_pixel_sha(data: bytes) -> str:
    from io import BytesIO
    import numpy as np
    from PIL import Image
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.mode != "RGBA":
                raise ValueError("expected an RGBA PNG")
            return sha256(np.asarray(image).tobytes()).hexdigest()
    except OSError as error:
        raise ValueError("could not decode accepted RGBA PNG") from error


def _decode_rgba(data: bytes) -> np.ndarray:
    from io import BytesIO
    from PIL import Image
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.mode != "RGBA" or getattr(image, "n_frames", 1) != 1:
                raise ValueError("expected a static RGBA PNG")
            return np.asarray(image).copy()
    except OSError as error:
        raise ValueError("could not decode accepted RGBA PNG") from error


def _bbox_size(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("accepted Stage 3 path is degenerate")
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    intersection = int(np.count_nonzero(first.astype(bool) & second.astype(bool)))
    union = int(np.count_nonzero(first.astype(bool) | second.astype(bool)))
    return intersection / union if union else 1.0


def _boundary(mask: np.ndarray) -> np.ndarray:
    value = np.asarray(mask, dtype=np.uint8)
    return value & ~(cv2.erode(value, np.ones((3, 3), dtype=np.uint8)) > 0)


def _json(raw: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
