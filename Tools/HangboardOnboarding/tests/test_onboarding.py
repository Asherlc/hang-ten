from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytest

from hangboard_vectorizer.onboarding import (
    EvidenceImage,
    OpenAIResponsesResolver,
    SourceCandidate,
    SourceEvidence,
    Stage0EvidenceInputs,
    beastmaker_v6_evidence,
    resolve_commercial_product,
    run_stage0_onboarding,
    score_source_candidates,
)


def test_real_benchmark_factory_pins_both_candidate_identities_with_explicit_paths() -> None:
    evidence = beastmaker_v6_evidence(
        tulipwood_path=Path("tulip.jpg"), beech_path=Path("beech.jpg"),
        v6_crop_path=Path("v6-crop.png"), v6_alignment_path=Path("v6-alignment.png"),
    )

    assert evidence.beech.raw_sha256 == "0b5abca6d0891bd205250d53704bfb0984cb42852a97b5ddcc3ee7af156d6140"
    assert evidence.beech.decoded_rgb_sha256 == "686b465815c5cd441b1f3c6898a053ab09cb87c38aa7fb35f45a0ee81325f746"
    assert evidence.tulipwood.path == Path("tulip.jpg")


def test_catalog_requires_explicit_series_and_material_without_fake_mk2() -> None:
    resolution = resolve_commercial_product("Beastmaker 1000 Series Tulipwood")

    assert resolution.product_id == "beastmaker-1000"
    assert resolution.commercial_name == "Beastmaker 1000 Series"
    assert resolution.material == "Tulipwood"
    with pytest.raises(ValueError, match="exactly one"):
        resolve_commercial_product("Beastmaker 1000 Series")
    with pytest.raises(ValueError, match="exactly one"):
        resolve_commercial_product("Beastmaker 1000 Series Tulipwood Beech")
    with pytest.raises(ValueError, match="exactly one"):
        resolve_commercial_product("Beastmaker 1000 Mk2 Tulipwood")


def test_source_scoring_prefers_high_resolution_front_facing_clean_candidate() -> None:
    candidates = (
        SourceCandidate("small", Path("small.jpg"), 800, 400, 0.6, 0.7, 0.9, 1),
        SourceCandidate("best", Path("best.jpg"), 2400, 620, 0.96, 0.98, 0.98, 1),
    )

    ranked = score_source_candidates(candidates, target_aspect_ratio=1000 / 259)

    assert [item.candidate.id for item in ranked] == ["best", "small"]
    assert ranked[0].score > ranked[1].score


def test_raw_responses_provider_parses_output_items_and_returns_valid_ranking(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver = OpenAIResponsesResolver("not-a-real-key", model="fixture")
    fixture = {"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"product_id":"beastmaker-1000","material":"Tulipwood"}'}]}]}
    monkeypatch.setattr(resolver, "_request", lambda payload: fixture)

    resolved = resolve_commercial_product("Beastmaker 1000 Series Tulipwood", provider=resolver)

    assert resolved.material == "Tulipwood"
    assert resolver._payload("x", {}, {"type": "object"})["text"]["format"]["type"] == "json_schema"  # type: ignore[index]
    rank_fixture = {"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"ordered_ids":["a","b"]}'}]}]}
    monkeypatch.setattr(resolver, "_request", lambda payload: rank_fixture)
    assert resolver.rank("q", (SourceCandidate("a", None, 1, 1, 1, 1, 1, 1), SourceCandidate("b", None, 1, 1, 1, 1, 1, 1))) == ("a", "b")


def test_stage0_acceptance_bundle_is_repeatable_with_all_explicit_evidence(tmp_path: Path) -> None:
    evidence = _synthetic_evidence(tmp_path / "fixtures")
    first, second = tmp_path / "first", tmp_path / "second"

    first_bundle = run_stage0_onboarding(evidence, first)
    second_bundle = run_stage0_onboarding(evidence, second)

    assert first_bundle == second_bundle
    first_artifacts = _artifact_bytes(first)
    assert first_artifacts == _artifact_bytes(second)
    assert "stage-0-review.png" in first_artifacts
    assert "elapsedMs" not in (first / "stage-0-diagnostic.json").read_text(encoding="utf-8")
    candidates = {item["id"]: item for item in first_bundle["sourceCandidates"]}
    assert first_bundle["selectedSource"]["id"] == "fixture-tulipwood"
    assert candidates["fixture-beech"]["eligible"] is False
    assert "material mismatch" in candidates["fixture-beech"]["rejectionReason"]


def test_stage0_fails_closed_when_v6_fixture_is_missing(tmp_path: Path) -> None:
    evidence = _synthetic_evidence(tmp_path / "fixtures")
    missing = replace(evidence, v6_alignment=replace(evidence.v6_alignment, path=tmp_path / "missing.png"))

    with pytest.raises(FileNotFoundError, match="required Stage 0 evidence fixture"):
        run_stage0_onboarding(missing, tmp_path / "artifact")


def test_stage0_rejects_an_arbitrary_file_claimed_as_tulipwood(tmp_path: Path) -> None:
    evidence = _synthetic_evidence(tmp_path / "fixtures")
    wrong = replace(evidence, tulipwood=replace(evidence.tulipwood, path=evidence.beech.path))

    with pytest.raises(ValueError, match="evidence identity mismatch"):
        run_stage0_onboarding(wrong, tmp_path / "artifact")


def _synthetic_evidence(root: Path) -> Stage0EvidenceInputs:
    root.mkdir()
    tulip, beech = root / "fixture-tulipwood.png", root / "fixture-beech.png"
    _write_board(tulip, (209, 183, 122))
    _write_board(beech, (170, 113, 67))
    tulip_rgb = _rgb(tulip)
    crop = tulip_rgb[30:289, 35:1041]
    crop_path, alignment_path = root / "v6-crop.png", root / "v6-alignment.png"
    Image.fromarray(crop).save(crop_path)
    Image.fromarray(cv2.resize(crop, (1000, 259), interpolation=cv2.INTER_LANCZOS4)).save(alignment_path)
    return Stage0EvidenceInputs(
        tulipwood=_source_evidence("fixture-tulipwood", "Tulipwood", tulip),
        beech=_source_evidence("fixture-beech", "Beech", beech),
        v6_crop=_image_evidence(crop_path),
        v6_alignment=_image_evidence(alignment_path),
    )


def _write_board(path: Path, color: tuple[int, int, int]) -> None:
    rgb = np.full((318, 1080, 3), 250, dtype=np.uint8)
    cv2.rectangle(rgb, (35, 30), (1040, 288), color, thickness=-1)
    for x in range(120, 960, 150):
        cv2.ellipse(rgb, (x, 150), (52, 26), 0, 0, 360, (40, 30, 22), thickness=-1)
    Image.fromarray(rgb).save(path)


def _source_evidence(identifier: str, material: str, path: Path) -> SourceEvidence:
    image = _image_evidence(path)
    return SourceEvidence(image.path, image.raw_sha256, image.decoded_rgb_sha256, identifier, material, f"https://fixtures.invalid/{identifier}")


def _image_evidence(path: Path) -> EvidenceImage:
    return EvidenceImage(path, sha256(path.read_bytes()).hexdigest(), sha256(_rgb(path).tobytes()).hexdigest())


def _rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def _artifact_bytes(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
