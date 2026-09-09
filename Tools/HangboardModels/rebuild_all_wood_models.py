#!/usr/bin/env python3
"""Deterministically rebuild every shipped wood display-model package.

Changing ``assets/canonical-neutral-wood.png`` requires this command followed
by the actual-export checks documented in README.md. The script discovers model
media from board packages and rejects a builder map that is incomplete.

  rtk python3 -B Tools/HangboardModels/rebuild_all_wood_models.py
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
OWNER = Path(os.environ.get("PASEO_WORKTREE_PATH", ROOT)).name
CONTEXT = ROOT / ".context"
RECORD_PATH = CONTEXT / f"{OWNER}-canonical-wood-review" / "rebuild-manifest.json"
PACKAGE_FILES = frozenset({"assets/primary.model.json", "assets/primary.usdz"})
BUILDERS = {
    "beastmaker-1000": {
        "blend": CONTEXT / f"{OWNER}-beastmaker-1000/beastmaker-1000-compiler-input.blend",
    },
    "metolius-wood-grips-compact-ii": {
        "blend": CONTEXT / f"{OWNER}-metolius-wood-grips-compact-ii/wood-grips-compact-ii.blend",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_model_packages() -> dict[str, Path]:
    packages: dict[str, Path] = {}
    for board_path in sorted((ROOT / "Hangboards").glob("*/board.json")):
        document = json.loads(board_path.read_text(encoding="utf-8"))
        for presentation in document.get("presentations", []):
            media = presentation.get("media", {})
            if media.get("type") != "model":
                continue
            slug = board_path.parent.name
            if slug in packages:
                raise ValueError(f"board has multiple model media packages: {slug}")
            package = board_path.parent
            expected = package / media["assetPath"]
            if expected != package / "assets/primary.usdz":
                raise ValueError(f"model package does not use canonical asset location: {slug}")
            packages[slug] = package
    if set(packages) != set(BUILDERS):
        raise ValueError(
            f"wood builder coverage mismatch; discovered={sorted(packages)} builders={sorted(BUILDERS)}"
        )
    return packages


def package_tree(package: Path) -> frozenset[str]:
    return frozenset(
        item.relative_to(package).as_posix()
        for item in package.rglob("*")
        if item.is_file() and not item.is_symlink()
    )


def descriptor_geometry(path: Path) -> dict[str, object]:
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    descriptor.pop("modelSHA256")
    return descriptor


def run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print("REBUILD_COMMAND", json.dumps(command), flush=True)
    print(completed.stdout, end="", flush=True)
    if completed.returncode:
        raise subprocess.CalledProcessError(completed.returncode, command)


def rebuild() -> dict[str, object]:
    packages = discover_model_packages()
    before = {
        slug: {
            "modelSHA256": sha256(package / "assets/primary.usdz"),
            "descriptorSHA256": sha256(package / "assets/primary.model.json"),
            "descriptorGeometry": descriptor_geometry(package / "assets/primary.model.json"),
        }
        for slug, package in packages.items()
    }
    work = Path(tempfile.mkdtemp(prefix=f"{OWNER}-canonical-wood-build-", dir=CONTEXT))
    (work / "ownership.json").write_text(
        json.dumps({"owner": OWNER, "resources": [str(work)], "external_resources": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        for slug, builder in BUILDERS.items():
            run([
                "blender", "--background", "--factory-startup", "--python-exit-code", "1",
                "--python", str(ROOT / "Tools/HangboardModels/bind_canonical_wood_to_source.py"), "--",
                "--blend", str(builder["blend"]),
            ])
            run([
                "blender", "--background", "--factory-startup", "--python-exit-code", "1",
                "--python", str(ROOT / "Tools/HangboardModels/compile_model_package.py"), "--",
                "--blend", str(builder["blend"]),
                "--board-json", str(packages[slug] / "board.json"),
                "--output-directory", str(work / slug),
            ])
        after: dict[str, object] = {}
        for slug, package in packages.items():
            compiled = work / slug
            if package_tree(compiled) != PACKAGE_FILES:
                raise ValueError(f"compiler package tree is not exact for {slug}")
            descriptor = compiled / "assets/primary.model.json"
            if descriptor_geometry(descriptor) != before[slug]["descriptorGeometry"]:
                raise ValueError(f"geometry or inventory changed while rebuilding {slug}")
            for relative in PACKAGE_FILES:
                source = compiled / relative
                destination = package / relative
                temporary = destination.with_name(destination.name + ".canonical-wood-tmp")
                shutil.copyfile(source, temporary)
                os.replace(temporary, destination)
            after[slug] = {
                "modelSHA256": sha256(package / "assets/primary.usdz"),
                "descriptorSHA256": sha256(package / "assets/primary.model.json"),
                "descriptorGeometryUnchanged": True,
                "packageTree": sorted(package_tree(package)),
            }
        record = {
            "owner": OWNER,
            "command": "rtk python3 -B Tools/HangboardModels/rebuild_all_wood_models.py",
            "canonicalTexture": "Tools/HangboardModels/assets/canonical-neutral-wood.png",
            "canonicalTextureSHA256": sha256(ROOT / "Tools/HangboardModels/assets/canonical-neutral-wood.png"),
            "before": before,
            "after": after,
            "temporaryBuildDirectory": str(work),
            "temporaryBuildDirectoryCleaned": True,
        }
        RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECORD_PATH.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return record
    finally:
        shutil.rmtree(work, ignore_errors=False)
        if work.exists():
            raise RuntimeError(f"failed to clean owned build directory: {work}")


if __name__ == "__main__":
    print(json.dumps(rebuild(), sort_keys=True))
