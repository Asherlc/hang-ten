"""A delivery lock covers the full model inventory, even without CAD caches."""
from pathlib import Path
import hashlib
import importlib.util
import json

import pytest

from conftest import write_cad_source


def delivery_module():
    path = Path(__file__).resolve().parents[3] / "scripts/verify-model-delivery.py"
    spec = importlib.util.spec_from_file_location("model_delivery_lock", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cad_package(root, slug, *, model=True, cached=False, configured=False):
    package = root / "Hangboards" / slug
    assets = package / "assets"
    assets.mkdir(parents=True)
    names = ["primary", "configured"] if configured else ["primary"]
    presentations = []
    locked = []
    for name in names:
        media = {"type": "raster", "assetPath": f"assets/{name}.png"}
        if model:
            media = {"type": "model", "assetPath": f"assets/{name}.usdz",
                     "descriptorPath": f"assets/{name}.model.json"}
            descriptor = assets / f"{name}.model.json"
            descriptor.write_text(json.dumps({"modelSHA256": "a" * 64}))
            locked.append(descriptor)
            if cached:
                (assets / f"{name}.usdz").write_bytes(b"local compiled cache")
        presentations.append({"id": name, "media": media})
    (package / "board.json").write_text(json.dumps({
        "schemaVersion": 3, "id": f"fixture.{slug}", "presentations": presentations,
    }))
    locked.append(write_cad_source(package))
    return locked


def lock(root, packages, files):
    # Independent checksum fixture: the caller explicitly lists locked inputs.
    text = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
        for path in sorted(files)
    )
    return {"schemaVersion": 1, "modelPackages": packages,
            "sha256Manifest": hashlib.sha256(text.encode()).hexdigest()}


@pytest.mark.parametrize("cached", [False, True])
def test_cad_model_missing_from_lock_is_rejected_even_without_compiled_cache(tmp_path, cached):
    files = cad_package(tmp_path, "listed")
    cad_package(tmp_path, "omitted", cached=cached)
    with pytest.raises(ValueError, match="inventory"):
        delivery_module().verify(tmp_path, lock(tmp_path, ["listed"], files))


def test_lock_cannot_list_a_cad_package_without_a_model_presentation(tmp_path):
    files = cad_package(tmp_path, "model") + cad_package(tmp_path, "raster", model=False)
    with pytest.raises(ValueError, match="inventory"):
        delivery_module().verify(tmp_path, lock(tmp_path, ["model", "raster"], files))


def test_complete_cad_inventory_uses_all_descriptors_and_needs_no_compiled_cache(tmp_path):
    files = cad_package(tmp_path, "configured", configured=True)
    cad_package(tmp_path, "raster", model=False)
    document = lock(tmp_path, ["configured"], files)
    result = delivery_module().verify(tmp_path, document)
    assert result["passed"] and result["files"] == 3
    assert result["sourceBacked"] == ["configured"]
    assert not tuple(tmp_path.rglob("*.usdz"))
    (tmp_path / "Hangboards/configured/assets/configured.model.json").write_text(
        json.dumps({"modelSHA256": "b" * 64})
    )
    with pytest.raises(ValueError, match="checksum"):
        delivery_module().verify(tmp_path, document)


def test_delivery_lock_rejects_a_missing_listed_package(tmp_path):
    files = cad_package(tmp_path, "present")
    with pytest.raises(ValueError):
        delivery_module().verify(tmp_path, lock(tmp_path, ["present", "missing"], files))


@pytest.mark.parametrize("member", ["source", "descriptor"])
def test_locked_native_inputs_cannot_be_symlinks(tmp_path, member):
    files = cad_package(tmp_path, "model")
    document = lock(tmp_path, ["model"], files)
    path = files[-1] if member == "source" else files[0]
    target = tmp_path / "original"
    path.rename(target)
    path.symlink_to(target)
    with pytest.raises(ValueError, match="regular|symlink"):
        delivery_module().verify(tmp_path, document)
