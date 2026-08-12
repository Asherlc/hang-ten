from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from hangboard_vectorizer.generic_stage0 import (
    CommercialIdentityAssertion,
    commercial_identity,
    run_generic_stage0,
)
from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.source_cache import cache_source


def _source(tmp_path: Path, name: str, rgb: np.ndarray):
    path = tmp_path / f"{name}.png"
    Image.fromarray(rgb).save(path)
    return cache_source(str(path), tmp_path / f"{name}-cache")


def _canvas() -> np.ndarray:
    return np.full((600, 900, 3), 245, dtype=np.uint8)


def test_single_piece_registration_is_deterministic_and_transparent_rgb_is_zero(tmp_path: Path):
    rgb = _canvas()
    cv2.rectangle(rgb, (130, 210), (770, 390), (105, 68, 32), -1)
    source = _source(tmp_path, "single", rgb)
    identity = commercial_identity("Example Board")
    first = run_generic_stage0(source, identity, tmp_path / "first")
    second = run_generic_stage0(source, identity, tmp_path / "second")
    pixels = np.asarray(Image.open(first.artifact_root / "stage-0-registered-rgba.png"))

    assert (first.artifact_root / "stage-0-registered-rgba.png").read_bytes() == (second.artifact_root / "stage-0-registered-rgba.png").read_bytes()
    assert pixels.shape[1] == 1000
    assert np.all(pixels[pixels[..., 3] == 0, :3] == 0)


def test_two_piece_registration_preserves_the_gap(tmp_path: Path):
    rgb = _canvas()
    cv2.rectangle(rgb, (130, 210), (420, 390), (105, 68, 32), -1)
    cv2.rectangle(rgb, (480, 210), (770, 390), (105, 68, 32), -1)
    checkpoint = run_generic_stage0(_source(tmp_path, "pieces", rgb), commercial_identity("Two Piece"), tmp_path / "artifacts")
    pixels = np.asarray(Image.open(checkpoint.artifact_root / "stage-0-registered-rgba.png"))

    middle = pixels[:, pixels.shape[1] // 2, 3]
    assert np.all(middle == 0)
    assert pixels[..., 3].max() == 255


def test_registration_preserves_an_irregular_trapezoid_silhouette(tmp_path: Path):
    rgb = _canvas()
    outline = np.array(((90, 180), (810, 180), (750, 420), (150, 420)), dtype=np.int32)
    cv2.fillConvexPoly(rgb, outline, (105, 68, 32))

    checkpoint = run_generic_stage0(
        _source(tmp_path, "trapezoid", rgb),
        commercial_identity("Irregular Board"),
        tmp_path / "artifacts",
    )
    alpha = np.asarray(
        Image.open(checkpoint.artifact_root / "stage-0-registered-rgba.png")
    )[..., 3]
    occupied_rows = np.flatnonzero(alpha.any(axis=1))
    upper = alpha[occupied_rows[len(occupied_rows) // 5]]
    lower = alpha[occupied_rows[-len(occupied_rows) // 5]]

    assert np.count_nonzero(upper) > np.count_nonzero(lower)


def test_registration_rejects_background_coverage_piece_count_and_aspect_failures(tmp_path: Path):
    background = _canvas()
    too_many = _canvas()
    for x in (80, 240, 400, 560, 720):
        cv2.rectangle(too_many, (x, 200), (x + 80, 300), (60, 80, 100), -1)
    square = _canvas()
    cv2.rectangle(square, (280, 150), (620, 490), (60, 80, 100), -1)

    for name, image in (("background", background), ("pieces", too_many), ("square", square)):
        with pytest.raises(ConversionError):
            run_generic_stage0(_source(tmp_path, name, image), commercial_identity(name), tmp_path / f"{name}-artifacts")


def test_identity_is_normalized_without_claiming_verification():
    identity = commercial_identity("  Example   Board  1000 ")

    assert identity.asserted_name == "  Example   Board  1000 "
    assert identity.normalized_name == "Example Board 1000"
    assert identity.product_key == "example-board-1000"
    assert identity.assertion_source == "caller"


@pytest.mark.parametrize(
    ("asserted_name", "product_key"),
    (
        ("Rock/Stone Hangboard", "rock-stone-hangboard"),
        ("AC/DC Board", "ac-dc-board"),
    ),
)
def test_identity_allows_single_slash_commercial_names(asserted_name: str, product_key: str):
    identity = commercial_identity(asserted_name)

    assert identity.normalized_name == asserted_name
    assert identity.product_key == product_key


@pytest.mark.parametrize(
    "asserted_name",
    (
        "/tmp",
        "/tmp/upload-20260805.png",
        "Acme Board /tmp",
        "Acme Board /tmp/upload.png",
        "Acme/tmp/upload.png",
        r"Acme C:\temp\image.png",
        r"Acme C:\\temp\\image.png",
        "Acme Board—/tmp/upload.png",
        "Acme Board]/tmp/upload.png",
        "file:///tmp/upload.png",
        "Board 2026-08-05",
        "Example Board 550e8400-e29b-41d4-a716-446655440000",
        "upload_01J4YQDG4S0QHWCPBXCKDYZJFW",
    ),
)
def test_identity_rejects_paths_dates_and_temporary_identifiers(asserted_name: str):
    with pytest.raises(ValueError, match="stable commercial name"):
        commercial_identity(asserted_name)


def test_stage0_rechecks_a_manually_constructed_identity_before_publishing(tmp_path: Path):
    rgb = _canvas()
    cv2.rectangle(rgb, (130, 210), (770, 390), (105, 68, 32), -1)
    unsafe = CommercialIdentityAssertion(
        asserted_name="/tmp/upload-20260805.png",
        normalized_name="/tmp/upload-20260805.png",
        product_key="tmp-upload-20260805-png",
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(ValueError, match="stable commercial name"):
        run_generic_stage0(_source(tmp_path, "manual-identity", rgb), unsafe, artifact_root)
    assert not artifact_root.exists()


def test_candidate_hashes_bind_every_reviewed_file(tmp_path: Path):
    rgb = _canvas()
    cv2.rectangle(rgb, (130, 210), (770, 390), (105, 68, 32), -1)
    checkpoint = run_generic_stage0(_source(tmp_path, "hashes", rgb), commercial_identity("Hash Board"), tmp_path / "artifacts")
    hashes = json.loads((checkpoint.artifact_root / "candidate-hashes.json").read_text())

    assert set(hashes) == {"stage-0-candidate.json", "stage-0-source-preview.png", "stage-0-isolation.png", "stage-0-registered-rgba.png", "stage-0-review.png"}
    assert hashes == {name: sha256((checkpoint.artifact_root / name).read_bytes()).hexdigest() for name in hashes}


def test_stage0_refuses_an_existing_artifact_root(tmp_path: Path):
    rgb = _canvas()
    cv2.rectangle(rgb, (130, 210), (770, 390), (105, 68, 32), -1)
    root = tmp_path / "artifacts"
    root.mkdir()

    with pytest.raises(FileExistsError):
        run_generic_stage0(_source(tmp_path, "existing", rgb), commercial_identity("Existing Board"), root)
