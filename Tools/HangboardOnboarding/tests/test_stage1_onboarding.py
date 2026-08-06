from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

from hangboard_vectorizer.simplification import SimplifiedRaster
import hangboard_vectorizer.stage1_onboarding as stage1
from hangboard_vectorizer.stage1_onboarding import (
    Stage1EvidenceInputs,
    TrustedImageIdentity,
    TrustedStage1Policy,
    beastmaker_stage1_evidence,
    run_stage1_onboarding,
)


@dataclass(frozen=True, slots=True)
class _FixtureProfile:
    rgba: np.ndarray
    review: np.ndarray
    repair_mask: np.ndarray
    profile_id: str = "fixture-stage1-v1"
    product_id: str = "fixture-board"
    material: str = "Fixturewood"
    piece_count: int = 1

    def simplify(self, source_rgb: np.ndarray) -> SimplifiedRaster:
        del source_rgb
        return SimplifiedRaster(self.rgba, self.review, self.repair_mask)


class _NondeterministicProfile:
    def __init__(self, fixture: _FixtureProfile) -> None:
        self._fixture, self._calls = fixture, 0
        self.profile_id = fixture.profile_id
        self.product_id = fixture.product_id
        self.material = fixture.material
        self.piece_count = fixture.piece_count

    def simplify(self, source_rgb: np.ndarray) -> SimplifiedRaster:
        del source_rgb
        self._calls += 1
        rgba = self._fixture.rgba.copy()
        if self._calls == 2:
            rgba[40, 40, 0] ^= 1
        return SimplifiedRaster(rgba, self._fixture.review, self._fixture.repair_mask)


class _MutatingProfile(_FixtureProfile):
    def __init__(self, fixture: _FixtureProfile, target: Path) -> None:
        object.__setattr__(self, "rgba", fixture.rgba)
        object.__setattr__(self, "review", fixture.review)
        object.__setattr__(self, "repair_mask", fixture.repair_mask)
        object.__setattr__(self, "profile_id", fixture.profile_id)
        object.__setattr__(self, "product_id", fixture.product_id)
        object.__setattr__(self, "material", fixture.material)
        object.__setattr__(self, "piece_count", fixture.piece_count)
        object.__setattr__(self, "_target", target)

    def simplify(self, source_rgb: np.ndarray) -> SimplifiedRaster:
        self._target.write_bytes(b"mutated after validation")
        return super().simplify(source_rgb)


def test_stage1_repeat_runs_are_recursively_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    first, second = tmp_path / "first", tmp_path / "second"
    first_document = run_stage1_onboarding(evidence, first, profile=profile)
    second_document = run_stage1_onboarding(evidence, second, profile=profile)

    assert first_document == second_document
    assert _artifact_bytes(first) == _artifact_bytes(second)
    assert first_document["accepted"] is True
    assert all(first_document["validation"]["pngFileEquality"].values())


def test_stage1_rejects_wrong_evidence_before_creating_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    tampered = evidence.manual_rgba_path
    pixels = np.asarray(Image.open(tampered).convert("RGBA")).copy()
    pixels[40, 40, 0] ^= 1
    Image.fromarray(pixels).save(tampered)
    root = tmp_path / "artifact"

    with pytest.raises(ValueError, match="manual RGBA evidence identity mismatch"):
        run_stage1_onboarding(evidence, root, profile=profile)

    assert not root.exists()


def test_stage1_rejects_missing_evidence_before_creating_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    root = tmp_path / "artifact"
    with pytest.raises(FileNotFoundError, match="manual review evidence is missing"):
        run_stage1_onboarding(replace(evidence, manual_review_path=tmp_path / "missing.png"), root, profile=profile)
    assert not root.exists()


def test_stage1_rejects_stage0_identity_tampering_before_creating_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    evidence.stage0_acceptance_path.write_text("{}", encoding="utf-8")
    root = tmp_path / "artifact"
    with pytest.raises(ValueError, match="Stage 0 acceptance identity mismatch"):
        run_stage1_onboarding(evidence, root, profile=profile)
    assert not root.exists()


def test_stage1_rejects_stage0_registration_tampering_before_creating_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    document = json.loads(evidence.stage0_acceptance_path.read_text(encoding="utf-8"))
    document["registration"]["crop"]["left"] = 36
    evidence.stage0_acceptance_path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    monkeypatch.setitem(stage1._TRUSTED_POLICIES, profile.profile_id, _policy_for(evidence, profile))
    root = tmp_path / "artifact"
    with pytest.raises(ValueError, match="registration crop"):
        run_stage1_onboarding(evidence, root, profile=profile)
    assert not root.exists()


def test_stage1_rejects_rgba_manual_review_before_creating_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    rgba_review = np.dstack((profile.review, np.full(profile.review.shape[:2], 255, dtype=np.uint8)))
    path = tmp_path / "rgba-review.png"
    Image.fromarray(rgba_review).save(path)
    policy = _policy_for(evidence, profile, review_path=path, review_mode="RGB")
    monkeypatch.setitem(stage1._TRUSTED_POLICIES, profile.profile_id, policy)
    bad = replace(evidence, manual_review_path=path)
    root = tmp_path / "artifact"

    with pytest.raises(ValueError, match="manual review must use RGB PNG mode"):
        run_stage1_onboarding(bad, root, profile=profile)

    assert not root.exists()


def test_stage1_rejects_pixel_equal_differently_encoded_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    package = tmp_path / "differently-encoded-package.png"
    Image.fromarray(profile.rgba).save(package, compress_level=1)
    policy = _policy_for(evidence, profile, package_path=package)
    monkeypatch.setitem(stage1._TRUSTED_POLICIES, profile.profile_id, policy)
    root = tmp_path / "artifact"

    with pytest.raises(ValueError, match="PNG bytes differ"):
        run_stage1_onboarding(replace(evidence, packaged_render_path=package), root, profile=profile)

    assert not root.exists()


def test_stage1_uses_validated_snapshots_when_an_input_mutates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, fixture = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    root = tmp_path / "artifact"
    document = run_stage1_onboarding(
        evidence, root, profile=_MutatingProfile(fixture, evidence.manual_rgba_path)
    )

    assert document["accepted"] is True
    assert (root / "stage-1-auto-rgba.png").read_bytes() != evidence.manual_rgba_path.read_bytes()


def test_stage1_discards_temporary_output_when_publication_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    root = tmp_path / "artifact"
    monkeypatch.setattr(stage1, "_write_json", lambda path, document: (_ for _ in ()).throw(RuntimeError("write failed")))

    with pytest.raises(RuntimeError, match="write failed"):
        run_stage1_onboarding(evidence, root, profile=profile)

    assert not root.exists()
    assert not list(tmp_path.glob(".artifact.*"))


@pytest.mark.parametrize(
    ("profile_change", "message"),
    (({"material": "Beech"}, "unsupported Stage 1 cleanup profile"), ({"piece_count": 2}, "unsupported Stage 1 cleanup profile"), ({"profile_id": "unknown"}, "unsupported Stage 1 cleanup profile")),
)
def test_stage1_rejects_unsupported_profiles_before_creating_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile_change: dict[str, object], message: str,
) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    root = tmp_path / "artifact"
    with pytest.raises(ValueError, match=message):
        run_stage1_onboarding(evidence, root, profile=replace(profile, **profile_change))
    assert not root.exists()


def test_stage1_rejects_deterministic_non_exact_output_before_creating_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    altered = profile.rgba.copy(); altered[40, 40, 0] ^= 1
    root = tmp_path / "artifact"
    with pytest.raises(ValueError, match="not pixel-exact to the accepted manual output"):
        run_stage1_onboarding(evidence, root, profile=replace(profile, rgba=altered))
    assert not root.exists()


def test_stage1_rejects_existing_root_and_nondeterminism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evidence, profile = _fixture_evidence(tmp_path / "fixtures", monkeypatch)
    existing = tmp_path / "existing"; existing.mkdir()
    with pytest.raises(FileExistsError): run_stage1_onboarding(evidence, existing, profile=profile)
    root = tmp_path / "artifact"
    with pytest.raises(ValueError, match="nondeterministic"):
        run_stage1_onboarding(evidence, root, profile=_NondeterministicProfile(profile))
    assert not root.exists()


def test_simplified_raster_uses_bytes_backed_immutable_buffers() -> None:
    source = np.zeros((2, 2, 4), dtype=np.uint8)
    result = SimplifiedRaster(source, source[..., :3], source[..., 0])
    source[:] = 255
    assert int(result.rgba.max()) == 0
    with pytest.raises(ValueError): result.rgba.setflags(write=True)
    with pytest.raises(ValueError): result.rgba[0, 0] = 1


def test_stage1_import_is_boundary_neutral_in_a_fresh_interpreter() -> None:
    root = Path(__file__).parents[1]
    environment = {**os.environ, "PYTHONPATH": str(root / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", "import sys, hangboard_vectorizer.stage1_onboarding; print(sorted(k for k in sys.modules if k.startswith('hangboard_vectorizer.')))"],
        cwd=root, env=environment, check=True, capture_output=True, text=True,
    )
    modules = completed.stdout
    for forbidden in ("regions", "templates", "product_validation", "beastmaker_replay", "product_render", "display_paths"):
        assert f"hangboard_vectorizer.{forbidden}" not in modules


def test_stage1_real_evidence_replay_when_explicit_root_is_supplied(tmp_path: Path) -> None:
    root_text = os.environ.get("HANGBOARD_STAGE1_REAL_EVIDENCE_ROOT")
    if root_text is None: return
    root = Path(root_text)
    from hangboard_vectorizer.simplification import BeastmakerTulipwoodCleanupProfile
    evidence = beastmaker_stage1_evidence(
        stage0_acceptance_path=root / "stage0-onboarding-v7/stage-0-acceptance.json",
        source_path=root / "stage0-onboarding-v7/candidates/source.jpg",
        manual_rgba_path=root / "photo-proof-fix1-v3.png",
        manual_review_path=root / "photo-proof-fix1-v3-review.png",
        packaged_render_path=Path("src/hangboard_vectorizer/products/beastmaker-1000-render.png").resolve(),
    )
    assert run_stage1_onboarding(evidence, tmp_path / "real-stage-1", profile=BeastmakerTulipwoodCleanupProfile())["accepted"] is True


def _fixture_evidence(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Stage1EvidenceInputs, _FixtureProfile]:
    root.mkdir(); source = np.full((318, 1080, 3), (244, 241, 235), dtype=np.uint8)
    source_path = root / "source.png"; Image.fromarray(source).save(source_path)
    rgba = np.zeros((259, 1000, 4), dtype=np.uint8); rgba[30:225, 20:980, :3] = (201, 171, 118); rgba[30:225, 20:980, 3] = 255
    review = np.full((459, 1200, 3), (248, 247, 244), dtype=np.uint8); review[100:359, 100:1100] = rgba[..., :3]
    repair_mask = np.zeros((259, 1000), dtype=np.uint8); repair_mask[70:100, 200:320] = 255
    manual, review_path, package = root / "manual.png", root / "review.png", root / "package.png"
    Image.fromarray(rgba).save(manual); Image.fromarray(review).save(review_path); Image.fromarray(rgba).save(package)
    fixture = _FixtureProfile(rgba, review, repair_mask)
    stage0 = {"preflight": {"passed": True, "productId": fixture.product_id}, "registration": {"canonicalShape": [259, 1000, 3], "crop": {"left": 35, "top": 30, "right": 1041, "bottom": 289}, "v6CropExact": True}, "resolution": {"material": fixture.material, "product_id": fixture.product_id}, "selectedSource": {"decodedRgbSha256": _pixel_sha(source), "id": "fixture-source", "material": fixture.material, "rawJpegSha256": _file_sha(source_path)}}
    stage0_path = root / "stage-0-acceptance.json"; stage0_path.write_text(json.dumps(stage0, sort_keys=True), encoding="utf-8")
    evidence = Stage1EvidenceInputs(stage0_path, source_path, manual, review_path, package)
    monkeypatch.setitem(stage1._TRUSTED_POLICIES, fixture.profile_id, _policy_for(evidence, fixture))
    return evidence, fixture


def _policy_for(evidence: Stage1EvidenceInputs, profile: _FixtureProfile, *, review_path: Path | None = None, review_mode: str = "RGB", package_path: Path | None = None) -> TrustedStage1Policy:
    review = review_path or evidence.manual_review_path; package = package_path or evidence.packaged_render_path
    return TrustedStage1Policy(profile.profile_id, profile.product_id, profile.material, profile.piece_count, ((profile.product_id, 0, profile.material),), "fixture-source", _identity(evidence.source_path, "RGB"), _identity(evidence.manual_rgba_path, "RGBA"), _identity(review, review_mode), _identity(package, "RGBA"), _file_sha(evidence.stage0_acceptance_path), (259, 1000, 3), (35, 30, 1041, 289))


def _identity(path: Path, mode: str) -> TrustedImageIdentity:
    with Image.open(path) as image:
        pixels = np.asarray(image.convert(mode)).copy(); image_format = image.format
    return TrustedImageIdentity(_file_sha(path), _pixel_sha(pixels), tuple(pixels.shape), mode, str(image_format))


def _file_sha(path: Path) -> str: return sha256(path.read_bytes()).hexdigest()
def _pixel_sha(pixels: np.ndarray) -> str: return sha256(pixels.tobytes()).hexdigest()
def _artifact_bytes(root: Path) -> dict[str, bytes]: return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
