"""The downloadable model set must be the exact, locked repository bytes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import pytest

ROOT = Path(__file__).resolve().parents[3]


def module():
    path = ROOT / "scripts/verify-model-delivery.py"
    assert path.is_file(), "The exact-delivery verifier must exist"
    spec = importlib.util.spec_from_file_location("model_delivery", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def fixture(root):
    p = root / "Hangboards/example/assets"
    p.mkdir(parents=True)
    (p / "primary.usdz").write_bytes(b"test model")
    (p / "primary.model.json").write_text("{}\n")
    (p.parent / "board.json").write_text("{}\n")
    text = module().checksum_manifest(root, ["example"])
    return {"schemaVersion": 1, "modelPackages": ["example"],
            "sha256Manifest": hashlib.sha256(text.encode()).hexdigest()}


def test_committed_models_match_delivery_lock():
    lock = json.loads((ROOT / "docs/source-audits/2026-09-22-model-delivery-lock.json").read_text())
    result = module().verify(ROOT, lock)
    assert result["models"] == 40
    assert result["files"] == 120


def test_changed_bytes_are_rejected(tmp_path):
    lock = fixture(tmp_path)
    (tmp_path / "Hangboards/example/assets/primary.usdz").write_bytes(b"other export")
    with pytest.raises(ValueError, match="checksum"):
        module().verify(tmp_path, lock)


def test_missing_file_is_rejected(tmp_path):
    lock = fixture(tmp_path)
    (tmp_path / "Hangboards/example/board.json").unlink()
    with pytest.raises(ValueError, match="regular file"):
        module().verify(tmp_path, lock)


def test_extra_model_is_rejected(tmp_path):
    lock = fixture(tmp_path)
    p = tmp_path / "Hangboards/extra/assets"
    p.mkdir(parents=True)
    (p / "primary.usdz").write_bytes(b"extra")
    with pytest.raises(ValueError, match="inventory"):
        module().verify(tmp_path, lock)


def test_unsafe_package_name_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="package"):
        module().checksum_manifest(tmp_path, ["../outside"])


def test_duplicate_package_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="package"):
        module().checksum_manifest(tmp_path, ["example", "example"])


def test_symlink_is_rejected(tmp_path):
    lock = fixture(tmp_path)
    p = tmp_path / "Hangboards/example/board.json"
    p.unlink()
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n")
    p.symlink_to(outside)
    with pytest.raises(ValueError, match="regular file"):
        module().verify(tmp_path, lock)
