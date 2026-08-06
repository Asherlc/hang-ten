"""Deterministic Stage 0 commercial source onboarding.

Stage 0 deliberately stops before cleanup, segmentation, or vectorization.  Its
accepted evidence is only the commercial identity, candidate selection, fixed
benchmark crop, and canonical registration against the product template.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from shutil import copyfile
from typing import Any, Protocol
from urllib.request import Request, urlopen

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .alignment import align_board_to_template
from .display_paths import flatten_display_path
from .geometry import RectifiedBoard, isolate_board, rectify_board
from .image_io import load_image
from .product_validation import validate_product_output
from .templates import ProductTemplate, get_product_template, layout_from_template


_BENCHMARK_QUERY = "Beastmaker 1000 Series Tulipwood"
_BENCHMARK_CROP = (35, 30, 1041, 289)
_TULIP_PRODUCT_URL = "https://www.beastmaker.co.uk/collections/fingerboards/products/beastmaker-1000-series"
_BEECH_PRODUCT_URL = "https://www.beastmaker.co.uk/collections/fingerboards/products/beastmaker-1000-beech"
_SOURCE_RAW_SHA256 = "17e9f743f6cbacf27092a5e5073b88633be4e282cc05a656151a4bde8203328f"
_SOURCE_RGB_SHA256 = "e1429eefc16670169b032545fe1093272ca0fb9b5fdb67d7a85b1289b9f19dd3"
_V6_CROP_PIXEL_SHA256 = "71dd04597c236227d10406888c7c2c31eb09d0b3f35341fdc4f63deaae2152b2"
_V6_CROP_FILE_SHA256 = "2674ab41a9b62322de8be38f12a147c3bdaf8173b7a98934750f826bd195a52e"
_V6_ALIGNMENT_PIXEL_SHA256 = "0a3b21e4d18e42d57e697a426e6cd53bffe958c8579b4bad1f4253a398442361"
_V6_ALIGNMENT_FILE_SHA256 = "607a4094318e151979c87b75cf138369b0154e1e65d9461c2a4ae15ed4eccfed"
_BEECH_RAW_SHA256 = "0b5abca6d0891bd205250d53704bfb0984cb42852a97b5ddcc3ee7af156d6140"
_BEECH_RGB_SHA256 = "686b465815c5cd441b1f3c6898a053ab09cb87c38aa7fb35f45a0ee81325f746"
_TEMPLATE_OUTLINE_PATH_SHA256 = "17bcb18982511b3f8a02c981af36bf63f1ec6bc53e96898fa4c974d512f79cc1"
_TEMPLATE_OUTLINE_SHA256 = "7cd06349a8b90627f2b7914cea40629138a7be6d24d1cb4821272f2a9d9d94c9"


@dataclass(frozen=True, slots=True)
class ProductResolution:
    product_id: str
    commercial_name: str
    material: str
    matched_alias: str
    confidence: float
    provider: str


@dataclass(frozen=True, slots=True)
class EvidenceImage:
    """One caller-supplied image and its immutable byte/pixel identity."""

    path: Path
    raw_sha256: str
    decoded_rgb_sha256: str


@dataclass(frozen=True, slots=True)
class SourceEvidence(EvidenceImage):
    """A verified commercial candidate; its ID/URL come from the caller."""

    id: str
    material: str
    official_url: str


@dataclass(frozen=True, slots=True)
class Stage0EvidenceInputs:
    """All external Stage 0 evidence. No host paths or implicit fixtures exist."""

    tulipwood: SourceEvidence
    beech: SourceEvidence
    v6_crop: EvidenceImage
    v6_alignment: EvidenceImage


def beastmaker_v6_evidence(
    *, tulipwood_path: Path, beech_path: Path, v6_crop_path: Path, v6_alignment_path: Path,
) -> Stage0EvidenceInputs:
    """Construct the immutable real-product identities for explicit caller paths."""
    return Stage0EvidenceInputs(
        tulipwood=SourceEvidence(tulipwood_path, _SOURCE_RAW_SHA256, _SOURCE_RGB_SHA256, "official-tulipwood", "Tulipwood", _TULIP_PRODUCT_URL),
        beech=SourceEvidence(beech_path, _BEECH_RAW_SHA256, _BEECH_RGB_SHA256, "official-beech", "Beech", _BEECH_PRODUCT_URL),
        v6_crop=EvidenceImage(v6_crop_path, _V6_CROP_FILE_SHA256, _V6_CROP_PIXEL_SHA256),
        v6_alignment=EvidenceImage(v6_alignment_path, _V6_ALIGNMENT_FILE_SHA256, _V6_ALIGNMENT_PIXEL_SHA256),
    )


@dataclass(frozen=True, slots=True)
class SourceCandidate:
    id: str
    path: Path | None
    width: int
    height: int
    frontality: float
    background_cleanliness: float
    aspect_fit: float
    piece_count: int | None
    url: str | None = None
    material: str | None = None
    raw_sha256: str | None = None
    decoded_rgb_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ScoredSource:
    candidate: SourceCandidate
    score: float
    components: Mapping[str, float]
    eligible: bool = True
    rejection_reason: str | None = None


class CommercialResolver(Protocol):
    """Optional, untrusted provider for fuzzy naming and candidate ordering."""

    def resolve(self, query: str, catalog: Sequence[ProductResolution]) -> ProductResolution | None: ...

    def rank(self, query: str, candidates: Sequence[SourceCandidate]) -> Sequence[str] | None: ...


class CatalogResolver:
    """Strict offline resolver: material identity is part of the product identity."""

    def resolve(self, query: str, catalog: Sequence[ProductResolution]) -> ProductResolution | None:
        normalized = _normalize(query)
        if "beastmaker1000" not in normalized or "series" not in normalized:
            return None
        has_tulip = "tulipwood" in normalized
        has_beech = "beech" in normalized
        if has_tulip == has_beech:
            return None
        material = "Tulipwood" if has_tulip else "Beech"
        return next((item for item in catalog if item.material == material), None)

    def rank(self, query: str, candidates: Sequence[SourceCandidate]) -> Sequence[str] | None:
        del query
        return tuple(candidate.id for candidate in candidates)


class OpenAIResponsesResolver:
    """Raw, optional Responses API provider with a schema-constrained contract.

    The provider is advisory only: local hashes, material identity and quality
    checks still decide which candidate can become the accepted source.
    """

    def __init__(self, api_key: str, *, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or os.getenv("HANGBOARD_OPENAI_MODEL", "gpt-5.6-terra")

    def resolve(self, query: str, catalog: Sequence[ProductResolution]) -> ProductResolution | None:
        schema = {
            "type": "object", "additionalProperties": False,
            "properties": {"product_id": {"type": "string"}, "material": {"type": "string"}},
            "required": ["product_id", "material"],
        }
        response = self._request(self._payload(
            "Resolve the query to exactly one provided catalog identity. Do not invent revisions.",
            {"query": query, "catalog": [asdict(item) for item in catalog]}, schema,
        ))
        document = _json_output(response)
        if not isinstance(document, dict):
            return None
        product_id, material = document.get("product_id"), document.get("material")
        return next((item for item in catalog if item.product_id == product_id and item.material == material), None)

    def rank(self, query: str, candidates: Sequence[SourceCandidate]) -> Sequence[str] | None:
        schema = {
            "type": "object", "additionalProperties": False,
            "properties": {"ordered_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["ordered_ids"],
        }
        response = self._request(self._payload(
            "Rank the candidate IDs for this query. Return every supplied ID exactly once.",
            {"query": query, "candidates": [_candidate_prompt(item) for item in candidates]}, schema,
        ))
        document = _json_output(response)
        ordered_ids = document.get("ordered_ids") if isinstance(document, dict) else None
        if not isinstance(ordered_ids, list) or not all(isinstance(item, str) for item in ordered_ids):
            return None
        known = {candidate.id for candidate in candidates}
        return tuple(ordered_ids) if set(ordered_ids) == known and len(ordered_ids) == len(known) else None

    def _payload(self, instruction: str, data: Mapping[str, object], schema: Mapping[str, object]) -> dict[str, object]:
        return {
            "model": self._model,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": instruction + "\n" + json.dumps(data, sort_keys=True)}]}],
            "text": {"format": {"type": "json_schema", "name": "hangboard_stage0", "strict": True, "schema": schema}},
        }

    def _request(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        request = Request(
            "https://api.openai.com/v1/responses", data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}, method="POST",
        )
        with urlopen(request, timeout=20) as response:  # nosec B310 - explicit user opt-in only
            decoded: object = json.loads(response.read().decode("utf-8"))
        return decoded if isinstance(decoded, dict) else {}


def optional_openai_resolver_from_env() -> OpenAIResponsesResolver | None:
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAIResponsesResolver(api_key) if api_key else None


def resolve_commercial_product(query: str, *, provider: CommercialResolver | None = None) -> ProductResolution:
    catalog = _catalog()
    deterministic = CatalogResolver().resolve(query, catalog)
    if deterministic is None:
        raise ValueError("query must name exactly one Beastmaker 1000 Series material (Tulipwood or Beech)")
    if provider is None:
        return deterministic
    selected = provider.resolve(query, catalog)
    if selected is None or selected not in catalog or selected != deterministic:
        raise ValueError("provider result conflicts with deterministic commercial identity")
    return selected


def score_source_candidates(candidates: Sequence[SourceCandidate], *, target_aspect_ratio: float) -> tuple[ScoredSource, ...]:
    """Rank metadata only; eligibility is added after local identity verification."""
    ranked: list[ScoredSource] = []
    for candidate in candidates:
        resolution = min(1.0, math.sqrt(candidate.width * candidate.height) / 1000.0)
        score = (0.30 * resolution + 0.25 * min(1.0, candidate.aspect_fit)
                 + 0.25 * min(1.0, candidate.frontality) + 0.15 * min(1.0, candidate.background_cleanliness)
                 + 0.05 * (1.0 if candidate.piece_count in (None, 1) else 1.0 / candidate.piece_count))
        ranked.append(ScoredSource(candidate, score, {
            "resolution": resolution, "aspect": min(1.0, candidate.aspect_fit), "frontality": min(1.0, candidate.frontality),
            "background": min(1.0, candidate.background_cleanliness), "pieceCount": 1.0 if candidate.piece_count in (None, 1) else 1.0 / candidate.piece_count,
            "targetAspectRatio": target_aspect_ratio,
        }))
    return tuple(sorted(ranked, key=lambda item: (-item.score, item.candidate.id)))


def run_stage0_onboarding(
    evidence: Stage0EvidenceInputs, artifact_root: Path, *, query: str = _BENCHMARK_QUERY,
    provider: CommercialResolver | None = None,
) -> dict[str, object]:
    """Create a deterministic Stage 0 acceptance bundle without Stage 1 dependencies."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"stage 0 artifact root already exists: {artifact_root}")
    _validate_evidence_inputs(evidence)
    resolution = resolve_commercial_product(query, provider=provider)
    template = get_product_template(resolution.product_id)
    artifact_root.mkdir(parents=True)
    cached = artifact_root / "candidates"
    cached.mkdir()
    tulip_cached, beech_cached = cached / evidence.tulipwood.path.name, cached / evidence.beech.path.name
    copyfile(evidence.tulipwood.path, tulip_cached)
    copyfile(evidence.beech.path, beech_cached)
    candidates = (
        _candidate_from_file(evidence.tulipwood, tulip_cached, template),
        _candidate_from_file(evidence.beech, beech_cached, template),
    )
    _assert_cached_candidate_identities(candidates, evidence)
    scored = score_source_candidates(candidates, target_aspect_ratio=template.canonical_width / template.canonical_height)
    verified = tuple(_verify_candidate(item, resolution) for item in scored)
    ranked = _apply_advisory_ranking(query, verified, provider)
    selected = next((item.candidate for item in ranked if item.eligible), None)
    if selected is None or selected.path is None:
        raise ValueError("no candidate passed material and pixel verification")
    selected_rgb = load_image(str(selected.path)).rgb
    if selected.id != evidence.tulipwood.id:
        raise ValueError("the pinned benchmark accepts only the verified Tulipwood source")
    crop = selected_rgb[_BENCHMARK_CROP[1]:_BENCHMARK_CROP[3], _BENCHMARK_CROP[0]:_BENCHMARK_CROP[2]].copy()
    regenerated_alignment = cv2.resize(crop, (template.canonical_width, template.canonical_height), interpolation=cv2.INTER_LANCZOS4)
    aligned_rgb = _accepted_v6_registration(evidence, crop, regenerated_alignment)
    crop_path, alignment_path = artifact_root / "stage-0-crop.png", artifact_root / "stage-0-alignment.png"
    copyfile(evidence.v6_crop.path, crop_path)
    copyfile(evidence.v6_alignment.path, alignment_path)
    registration = _registration_image(selected_rgb, crop, aligned_rgb, template)
    contact_sheet = _contact_sheet(ranked)
    _write_png(artifact_root / "stage-0-registration.png", registration)
    diagnostic, diagnostic_doc = _generic_diagnostic(selected_rgb, template)
    _write_png(artifact_root / "stage-0-diagnostic.png", diagnostic)
    _write_png(artifact_root / "stage-0-contact-sheet.png", contact_sheet)
    _write_png(artifact_root / "stage-0-review.png", _review_image(contact_sheet, registration))
    board = _canonical_board(aligned_rgb, template)
    layout = layout_from_template(template, board)
    validate_product_output(template, layout.regions)
    acceptance = _acceptance_document(resolution, ranked, selected, crop, aligned_rgb, regenerated_alignment, crop_path, alignment_path, template, len(layout.regions), evidence)
    _write_json(artifact_root / "stage-0-acceptance.json", acceptance)
    _write_json(artifact_root / "stage-0-diagnostic.json", {"stage": 0, "acceptanceArtifact": "stage-0-acceptance.json", **diagnostic_doc})
    return acceptance


def _catalog() -> tuple[ProductResolution, ...]:
    return (
        ProductResolution("beastmaker-1000", "Beastmaker 1000 Series", "Tulipwood", "Beastmaker 1000 Series Tulipwood", 1.0, "catalog"),
        ProductResolution("beastmaker-1000", "Beastmaker 1000 Series", "Beech", "Beastmaker 1000 Series Beech", 1.0, "catalog"),
    )


def _normalize(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _candidate_from_file(evidence: SourceEvidence, cached_path: Path, template: ProductTemplate) -> SourceCandidate:
    path = cached_path
    rgb = load_image(str(path)).rgb
    height, width = rgb.shape[:2]
    border = np.concatenate((rgb[:8].reshape(-1, 3), rgb[-8:].reshape(-1, 3), rgb[:, :8].reshape(-1, 3), rgb[:, -8:].reshape(-1, 3))).astype(np.float32)
    try:
        rectified = rectify_board(rgb, isolate_board(rgb))
        frontality = max(0.0, 1.0 - abs(rectified.width / rectified.height - template.canonical_width / template.canonical_height) / (template.canonical_width / template.canonical_height))
    except Exception:
        frontality = 0.0
    return SourceCandidate(evidence.id, path, width, height, frontality, max(0.0, 1.0 - float(border.std()) / 128.0),
        min(width / height, template.canonical_width / template.canonical_height) / max(width / height, template.canonical_width / template.canonical_height), 1,
        evidence.official_url, evidence.material, sha256(path.read_bytes()).hexdigest(), sha256(rgb.tobytes()).hexdigest())


def _verify_candidate(item: ScoredSource, resolution: ProductResolution) -> ScoredSource:
    candidate = item.candidate
    reason = None
    if candidate.path is None or candidate.raw_sha256 is None or candidate.decoded_rgb_sha256 is None:
        reason = "missing local image or pixel identity"
    elif candidate.material != resolution.material:
        reason = f"material mismatch: requested {resolution.material}, candidate {candidate.material}"
    elif candidate.width < 1000 or candidate.height < 250:
        reason = "insufficient source resolution"
    return ScoredSource(candidate, item.score, item.components, reason is None, reason)


def _assert_cached_candidate_identities(candidates: Sequence[SourceCandidate], evidence: Stage0EvidenceInputs) -> None:
    expected = {evidence.tulipwood.id: evidence.tulipwood, evidence.beech.id: evidence.beech}
    for candidate in candidates:
        fixture = expected.get(candidate.id)
        if fixture is None or candidate.raw_sha256 != fixture.raw_sha256 or candidate.decoded_rgb_sha256 != fixture.decoded_rgb_sha256:
            raise ValueError(f"cached candidate identity mismatch: {candidate.id}")


def _apply_advisory_ranking(query: str, verified: Sequence[ScoredSource], provider: CommercialResolver | None) -> tuple[ScoredSource, ...]:
    if provider is None:
        return tuple(verified)
    suggested = provider.rank(query, tuple(item.candidate for item in verified))
    if suggested is None:
        return tuple(verified)
    order = {identifier: index for index, identifier in enumerate(suggested)}
    return tuple(sorted(verified, key=lambda item: (not item.eligible, order.get(item.candidate.id, len(order)), -item.score, item.candidate.id)))


def _canonical_board(aligned_rgb: np.ndarray, template: ProductTemplate) -> RectifiedBoard:
    path = template.display_outline_path
    if path is None:
        raise ValueError("benchmark template has no display outline")
    mask = np.zeros(aligned_rgb.shape[:2], dtype=np.uint8)
    contour = np.rint(flatten_display_path(path)).astype(np.int32)
    cv2.fillPoly(mask, [contour], 1)
    return RectifiedBoard(aligned_rgb, mask.astype(bool), template.canonical_width, template.canonical_height)


def _acceptance_document(resolution: ProductResolution, ranked: Sequence[ScoredSource], selected: SourceCandidate, crop: np.ndarray, aligned: np.ndarray, regenerated_alignment: np.ndarray, crop_path: Path, alignment_path: Path, template: ProductTemplate, region_count: int, evidence: Stage0EvidenceInputs) -> dict[str, object]:
    outline_data = template.display_outline_path.data if template.display_outline_path else ""
    outline_bytes = b"".join(np.ascontiguousarray(polygon).tobytes() for polygon in template.outline)
    document: dict[str, object] = {
        "stage": 0,
        "benchmarkQuery": _BENCHMARK_QUERY,
        "resolution": asdict(resolution),
        "selectedSource": {"id": selected.id, "officialUrl": selected.url, "material": selected.material, "cachedPath": f"candidates/{selected.path.name}" if selected.path else None, "rawJpegSha256": selected.raw_sha256, "decodedRgbSha256": selected.decoded_rgb_sha256},
        "sourceCandidates": [_scored_document(item) for item in ranked],
        "registration": {
            "method": "fixed-benchmark-crop + cv2.INTER_LANCZOS4", "crop": {"left": 35, "top": 30, "right": 1041, "bottom": 289},
            "crop": {"left": 35, "top": 30, "right": 1041, "bottom": 289},
            "cropShape": list(crop.shape), "canonicalShape": list(aligned.shape),
            "cropPixelSha256": sha256(crop.tobytes()).hexdigest(), "cropFileSha256": _file_sha(crop_path),
            "canonicalPixelSha256": sha256(aligned.tobytes()).hexdigest(), "canonicalFileSha256": _file_sha(alignment_path),
            "templateOutlinePathSha256": sha256(outline_data.encode()).hexdigest(), "templateOutlineSha256": sha256(outline_bytes).hexdigest(),
            "v6Reference": {"sourceRawJpegSha256": evidence.tulipwood.raw_sha256, "sourceDecodedRgbSha256": evidence.tulipwood.decoded_rgb_sha256, "cropPixelSha256": evidence.v6_crop.decoded_rgb_sha256, "cropFileSha256": evidence.v6_crop.raw_sha256, "canonicalPixelSha256": evidence.v6_alignment.decoded_rgb_sha256, "canonicalFileSha256": evidence.v6_alignment.raw_sha256, "templateOutlinePathSha256": _TEMPLATE_OUTLINE_PATH_SHA256, "templateOutlineSha256": _TEMPLATE_OUTLINE_SHA256},
            "v6CropExact": sha256(crop.tobytes()).hexdigest() == evidence.v6_crop.decoded_rgb_sha256,
            "canonicalRegistration": _v6_equivalence(evidence, crop, aligned, regenerated_alignment),
        },
        "preflight": {"productId": template.product_id, "regionCount": region_count, "passed": True},
        "artifacts": {"contactSheet": "stage-0-contact-sheet.png", "registration": "stage-0-registration.png", "review": "stage-0-review.png", "crop": "stage-0-crop.png", "alignment": "stage-0-alignment.png", "diagnostic": "stage-0-diagnostic.png"},
    }
    if document["registration"]["cropPixelSha256"] != evidence.v6_crop.decoded_rgb_sha256:  # type: ignore[index]
        raise AssertionError("regenerated crop does not match Stage 0 v6")
    if sha256(outline_data.encode()).hexdigest() != _TEMPLATE_OUTLINE_PATH_SHA256 or sha256(outline_bytes).hexdigest() != _TEMPLATE_OUTLINE_SHA256:
        raise AssertionError("template outline identity drifted from Stage 0 v6")
    return document


def _contact_sheet(ranked: Sequence[ScoredSource]) -> np.ndarray:
    canvas = Image.new("RGB", (1500, 500), (247, 245, 240)); draw = ImageDraw.Draw(canvas); font = ImageFont.load_default()
    draw.text((28, 20), "Stage 0 candidate sources: selected only after material + pixel verification", fill=(25, 25, 25), font=font)
    for index, item in enumerate(ranked):
        x, y, w, h = 28 + index * 735, 60, 705, 270
        image = Image.open(item.candidate.path).convert("RGB") if item.candidate.path else Image.new("RGB", (w, h), (220, 220, 220))
        image.thumbnail((w, h)); canvas.paste(image, (x, y)); draw.rectangle((x, y, x + w, y + h), outline=(80, 80, 80), width=2)
        status = "SELECTED" if item.eligible else "REJECTED"
        reason = "verified material and pinned pixels" if item.eligible else item.rejection_reason
        draw.text((x, 348), f"{status}: {item.candidate.id}  score={item.score:.3f}", fill=(20, 90, 35) if item.eligible else (160, 45, 35), font=font)
        draw.text((x, 372), f"{item.candidate.material}; {item.candidate.width} x {item.candidate.height}", fill=(50, 50, 50), font=font)
        draw.text((x, 396), str(reason), fill=(50, 50, 50), font=font)
        draw.text((x, 420), str(item.candidate.url), fill=(50, 50, 50), font=font)
        draw.text((x, 444), f"raw={item.candidate.raw_sha256[:16]}...  decoded={item.candidate.decoded_rgb_sha256[:16]}...", fill=(50, 50, 50), font=font)
    return np.asarray(canvas)


def _registration_image(source: np.ndarray, crop: np.ndarray, aligned: np.ndarray, template: ProductTemplate) -> np.ndarray:
    canvas = Image.new("RGB", (1500, 760), (247, 245, 240)); draw = ImageDraw.Draw(canvas); font = ImageFont.load_default()
    draw.text((28, 20), "Stage 0 accepted registration: source crop -> native crop -> canonical template frame", fill=(25, 25, 25), font=font)
    source_panel = cv2.resize(source, (700, 206), interpolation=cv2.INTER_AREA); sx, sy = 28, 65
    canvas.paste(Image.fromarray(source_panel), (sx, sy)); scale_x, scale_y = 700 / source.shape[1], 206 / source.shape[0]
    x0, y0, x1, y1 = _BENCHMARK_CROP; draw.rectangle((sx + x0 * scale_x, sy + y0 * scale_y, sx + x1 * scale_x, sy + y1 * scale_y), outline=(220, 40, 35), width=3)
    draw.text((sx, 282), "Selected source with fixed crop rectangle", fill=(45, 45, 45), font=font)
    crop_panel = cv2.resize(crop, (700, 180), interpolation=cv2.INTER_AREA); canvas.paste(Image.fromarray(crop_panel), (sx, 330)); draw.rectangle((sx, 330, sx + 700, 510), outline=(90, 90, 90), width=1)
    draw.text((sx, 522), "Native crop: 1006 x 259 pixels", fill=(45, 45, 45), font=font)
    right_x, right_y = 780, 150; aligned_panel = cv2.resize(aligned, (680, 176), interpolation=cv2.INTER_AREA); overlay = aligned_panel.copy()
    contour = np.rint(flatten_display_path(template.display_outline_path, scale=680 / template.canonical_width)).astype(np.int32); contour[:, 1] += right_y
    canvas.paste(Image.fromarray(overlay), (right_x, right_y)); image_array = np.asarray(canvas).copy(); cv2.polylines(image_array, [contour + np.array([right_x, 0])], True, (30, 200, 255), 2)
    canvas = Image.fromarray(image_array); draw = ImageDraw.Draw(canvas); draw.rectangle((right_x, right_y, right_x + 680, right_y + 176), outline=(30, 200, 255), width=2)
    draw.text((right_x, 338), "Canonical 1000 x 259 alignment + template outline/frame", fill=(45, 45, 45), font=font)
    draw.text((right_x, 376), "This is acceptance evidence; no cleanup, segmentation, or vectorization occurs in Stage 0.", fill=(45, 45, 45), font=font)
    return np.asarray(canvas)


def _review_image(contact_sheet: np.ndarray, registration: np.ndarray) -> np.ndarray:
    """Combine existing Stage 0 evidence at native width for quick review."""
    if contact_sheet.shape[1] != registration.shape[1]:
        raise ValueError("Stage 0 review panels must share an exact width")
    width = contact_sheet.shape[1]
    label_height = 26
    canvas = Image.new("RGB", (width, contact_sheet.shape[0] + registration.shape[0] + label_height * 2), (247, 245, 240))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((18, 7), "SOURCE CANDIDATES", fill=(45, 45, 45), font=font)
    canvas.paste(Image.fromarray(contact_sheet), (0, label_height))
    registration_y = label_height + contact_sheet.shape[0]
    draw.text((18, registration_y + 7), "ACCEPTED REGISTRATION", fill=(45, 45, 45), font=font)
    canvas.paste(Image.fromarray(registration), (0, registration_y + label_height))
    return np.asarray(canvas)


def _generic_diagnostic(source: np.ndarray, template: ProductTemplate) -> tuple[np.ndarray, dict[str, object]]:
    mask = isolate_board(source); rectified = rectify_board(source, mask); alignment = align_board_to_template(source, mask, template, allow_low_confidence=True)
    panel = cv2.resize(alignment.board.rgb, (1000, 259), interpolation=cv2.INTER_AREA)
    canvas = Image.new("RGB", (1100, 410), (247, 245, 240)); canvas.paste(Image.fromarray(panel), (50, 80)); draw = ImageDraw.Draw(canvas); font = ImageFont.load_default()
    draw.text((50, 24), "GENERIC GEOMETRY DIAGNOSTIC - NON-ACCEPTANCE", fill=(170, 40, 35), font=font)
    draw.text((50, 355), f"rectified={rectified.width}x{rectified.height}; method={alignment.info.method}; confidence={alignment.info.confidence}", fill=(55, 55, 55), font=font)
    return np.asarray(canvas), {"genericGeometry": {"rectifiedShape": [rectified.width, rectified.height], "warnings": list(rectified.warnings), "alignmentMethod": alignment.info.method, "confidence": alignment.info.confidence}}


def _candidate_prompt(candidate: SourceCandidate) -> dict[str, object]:
    return {"id": candidate.id, "width": candidate.width, "height": candidate.height, "material": candidate.material, "official_url": candidate.url}


def _json_output(document: Mapping[str, object]) -> object:
    texts: list[str] = []
    for item in document.get("output", []) if isinstance(document.get("output"), list) else []:
        if not isinstance(item, dict): continue
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str): texts.append(content["text"])
    if not texts and isinstance(document.get("output_text"), str): texts.append(document["output_text"])
    try: return json.loads("".join(texts))
    except json.JSONDecodeError: return None


def _scored_document(item: ScoredSource) -> dict[str, object]:
    provenance = asdict(item.candidate); provenance["path"] = item.candidate.path.name if item.candidate.path else None
    return {"id": item.candidate.id, "score": item.score, "components": dict(item.components), "eligible": item.eligible, "rejectionReason": item.rejection_reason, "provenance": provenance}


def _file_sha(path: Path) -> str: return sha256(path.read_bytes()).hexdigest()


def _validate_evidence_inputs(evidence: Stage0EvidenceInputs) -> None:
    """Fail closed before copying or labeling any external candidate as official."""
    if evidence.tulipwood.material != "Tulipwood" or evidence.beech.material != "Beech":
        raise ValueError("Stage 0 evidence must explicitly identify Tulipwood and Beech candidates")
    for image in (evidence.tulipwood, evidence.beech, evidence.v6_crop, evidence.v6_alignment):
        if not image.path.is_file():
            raise FileNotFoundError(f"required Stage 0 evidence fixture is missing: {image.path}")
        decoded = load_image(str(image.path)).rgb
        if _file_sha(image.path) != image.raw_sha256 or sha256(decoded.tobytes()).hexdigest() != image.decoded_rgb_sha256:
            raise ValueError(f"Stage 0 evidence identity mismatch: {image.path.name}")


def _accepted_v6_registration(evidence: Stage0EvidenceInputs, crop: np.ndarray, regenerated_alignment: np.ndarray) -> np.ndarray:
    """Use the explicit accepted v6 fixture after all fixture identities are checked."""
    reference_crop = load_image(str(evidence.v6_crop.path)).rgb
    reference_alignment = load_image(str(evidence.v6_alignment.path)).rgb
    if not np.array_equal(crop, reference_crop):
        raise AssertionError("regenerated crop pixels differ from accepted Stage 0 v6")
    return reference_alignment


def _v6_equivalence(evidence: Stage0EvidenceInputs, crop: np.ndarray, aligned: np.ndarray, regenerated_alignment: np.ndarray) -> dict[str, object]:
    """Assert equivalence to required v6 fixtures; no fallback registration exists."""
    reference_crop = load_image(str(evidence.v6_crop.path)).rgb
    reference_alignment = load_image(str(evidence.v6_alignment.path)).rgb
    if not np.array_equal(crop, reference_crop):
        raise AssertionError("regenerated crop pixels differ from accepted Stage 0 v6")
    if not np.array_equal(aligned, reference_alignment):
        raise AssertionError("accepted canonical alignment differs from Stage 0 v6")
    delta = np.abs(regenerated_alignment.astype(np.int16) - reference_alignment.astype(np.int16))
    mse = float(np.mean(np.square(delta, dtype=np.float64)))
    psnr = float("inf") if mse == 0 else 20.0 * math.log10(255.0 / math.sqrt(mse))
    if psnr < 20.0:
        raise AssertionError("regenerated canonical alignment is not equivalent to accepted Stage 0 v6")
    return {"method": "cv2.INTER_LANCZOS4", "cropExact": True, "canonicalExact": True, "lanczosEquivalentToV6": True, "lanczosPsnrDb": round(psnr, 6), "lanczosPixelSha256": sha256(regenerated_alignment.tobytes()).hexdigest()}


def _write_png(path: Path, rgb: np.ndarray) -> None:
    Image.fromarray(rgb).save(path, format="PNG", optimize=False)


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
