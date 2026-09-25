#!/usr/bin/env python3
"""Strip all materials and textures from every Hangboards USDZ.

Meshes are left unbound so the renderer uses its default appearance.
Updates each primary.model.json SHA-256 to match the rewritten USDZ.

Run with:
    /tmp/usd-venv/bin/python3 Tools/set_clay_materials.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdShade, UsdUtils

REPOSITORY = Path(__file__).resolve().parents[1]
HANGBOARDS = REPOSITORY / "Hangboards"

_DOS_TIME = 0
_DOS_DATE = 33  # 1980-01-01


def _normalise_package_timestamps(path: Path) -> None:
    """Zero archive timestamps for deterministic output."""
    data = bytearray(path.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    if end < 0:
        raise ValueError("no end-of-central-directory record")
    count = int.from_bytes(data[end + 10 : end + 12], "little")
    offset = int.from_bytes(data[end + 16 : end + 20], "little")
    for _ in range(count):
        if data[offset : offset + 4] != b"PK\x01\x02":
            raise ValueError("malformed central directory")
        local = int.from_bytes(data[offset + 42 : offset + 46], "little")
        if data[local : local + 4] != b"PK\x03\x04":
            raise ValueError("malformed local header")
        for base, time_field, date_field, name_field in (
            (local, 10, 12, 26),
            (offset, 12, 14, 28),
        ):
            data[base + time_field : base + time_field + 2] = _DOS_TIME.to_bytes(2, "little")
            data[base + date_field : base + date_field + 2] = _DOS_DATE.to_bytes(2, "little")
            name_length = int.from_bytes(data[base + name_field : base + name_field + 2], "little")
            extra_length = int.from_bytes(data[base + name_field + 2 : base + name_field + 4], "little")
            cursor = base + 30 + name_length
            limit = cursor + extra_length
            while cursor + 4 <= limit:
                field_id = int.from_bytes(data[cursor : cursor + 2], "little")
                field_size = int.from_bytes(data[cursor + 2 : cursor + 4], "little")
                if field_id == 0x5455 and field_size >= 5:
                    flags = data[cursor + 4]
                    if flags & 0x01:
                        data[cursor + 5 : cursor + 9] = (0).to_bytes(4, "little")
                cursor += 4 + field_size
        name_length = int.from_bytes(data[offset + 28 : offset + 30], "little")
        extra = int.from_bytes(data[offset + 30 : offset + 32], "little")
        comment = int.from_bytes(data[offset + 32 : offset + 34], "little")
        offset += 46 + name_length + extra + comment
    path.write_bytes(bytes(data))


def strip_materials_from_usdz(usdz_path: Path) -> bool:
    """Strip all materials and textures from a USDZ. Returns True if modified."""
    staging = Path(tempfile.mkdtemp(prefix=".strip-", dir=usdz_path.parent))
    try:
        with zipfile.ZipFile(usdz_path) as archive:
            members = archive.namelist()
            for name in members:
                dest = staging / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(name))

        layers = [
            n for n in members
            if Path(n).suffix in {".usd", ".usda", ".usdc"}
        ]
        if len(layers) != 1:
            print(f"  SKIP: expected 1 USD layer, found {len(layers)}")
            return False

        stage = Usd.Stage.Open(str(staging / layers[0]))
        if stage is None:
            print(f"  SKIP: cannot open stage")
            return False

        # Unbind materials from all meshes
        mesh_count = 0
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                binding = UsdShade.MaterialBindingAPI(prim)
                binding.UnbindAllBindings()
                mesh_count += 1

        if mesh_count == 0:
            print(f"  SKIP: no meshes found")
            return False

        # Remove the entire _materials subtree
        stage.RemovePrim("/root/_materials")

        stage.GetRootLayer().Save()
        stage = None

        # Remove texture image files
        for name in list(staging.rglob("*")):
            if name.is_file() and name.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".hdr"}:
                name.unlink()

        # Rebuild USDZ
        package = staging / "new.usdz"
        UsdUtils.CreateNewUsdzPackage(str(staging / layers[0]), str(package))

        if not package.is_file() or package.stat().st_size == 0:
            print(f"  SKIP: packaging produced no output")
            return False

        _normalise_package_timestamps(package)
        os.replace(package, usdz_path)
        return True
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def update_descriptor_hash(usdz_path: Path) -> None:
    """Update the modelSHA256 in primary.model.json to match the new USDZ."""
    descriptor_path = usdz_path.parent / "primary.model.json"
    if not descriptor_path.is_file():
        return

    descriptor = json.loads(descriptor_path.read_text())
    new_hash = hashlib.sha256(usdz_path.read_bytes()).hexdigest()
    old_hash = descriptor.get("modelSHA256")

    if old_hash == new_hash:
        return

    descriptor["modelSHA256"] = new_hash
    descriptor_path.write_text(json.dumps(descriptor, indent=2, sort_keys=False) + "\n")
    print(f"  descriptor hash: {old_hash[:12]}... -> {new_hash[:12]}...")


def main() -> None:
    usdz_files = sorted(HANGBOARDS.rglob("primary.usdz"))
    print(f"Found {len(usdz_files)} USDZ models\n")

    modified = 0
    skipped = 0
    errors = 0

    for usdz in usdz_files:
        package = usdz.parent.parent.name
        print(f"[{package}]")
        try:
            if strip_materials_from_usdz(usdz):
                update_descriptor_hash(usdz)
                modified += 1
                print(f"  OK: materials stripped")
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR: {e}")

    print(f"\nDone: {modified} modified, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()