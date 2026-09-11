"""Deterministic review gallery generation for verified model packages.

This module deliberately imports Blender only inside the render operation.  The
package and descriptor are the only rendering inputs; source blends and source
images are never opened by the gallery.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from model_verification import ModelVerificationConfig, VerificationReport, verify_model_package

if TYPE_CHECKING:
    from migration_manifest import MigrationManifest


@dataclass(frozen=True)
class ReviewArtifact:
    view: str
    path: Path
    sha256: str
    provenance: str = "verified-package; fixed-view"


def _owner() -> str:
    return Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).resolve().name


def _owned_output(output: Path) -> Path:
    output = Path(output)
    if output.name == "" or not output.name.startswith(_owner() + "-"):
        raise ValueError("gallery output must be owner-prefixed")
    if output.parent.name != ".context":
        raise ValueError("gallery output must be directly under .context")
    return output


def cleanup_gallery_output(output: Path) -> None:
    """Remove exactly one previously owned gallery directory."""
    target = _owned_output(Path(output))
    if target.exists() and (target.is_symlink() or not target.is_dir()):
        raise ValueError("gallery output must be an owned directory")
    if target.exists():
        shutil.rmtree(target)
    if target.exists():
        raise RuntimeError(f"gallery cleanup failed: {target}")


def _verification_config(package: Path, manifest: "MigrationManifest") -> ModelVerificationConfig:
    board_json = package / Path(manifest.board_json).name
    if not board_json.is_file():
        board_json = Path(__file__).resolve().parents[2] / manifest.board_json
    return ModelVerificationConfig(
        board_id=manifest.board_id,
        board_json=board_json,
        package_relative_assets=frozenset({manifest.presentation.asset_path, manifest.presentation.descriptor_path}),
        expected_hold_ids=manifest.logical_hold_ids,
        expected_position_ids=tuple(position.id for position in manifest.positions),
        triangle_ceiling=manifest.verification.triangle_ceiling,
    )


def _fixed_view_names(manifest: "MigrationManifest") -> tuple[str, ...]:
    if not manifest.review_views:
        raise ValueError("gallery requires at least one reviewed view")
    names = tuple(manifest.review_views)
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value) for value in names):
        raise ValueError("review view names must be stable file-name tokens")
    return names


def _render_fixed_views(package: Path, manifest: "MigrationManifest", output: Path) -> tuple[Path, ...]:
    """Import the verified USDZ and render fixed orthographic review views."""
    try:
        import compile_model_package as compiler
        bpy = compiler._bpy()
    except (ImportError, RuntimeError) as error:
        raise RuntimeError("gallery rendering requires Blender after package verification") from error

    bpy.ops.wm.read_factory_settings(use_empty=True)
    imported = bpy.ops.wm.usd_import(filepath=str(package / manifest.presentation.asset_path), merge_parent_xform=True)
    if "FINISHED" not in imported:
        raise ValueError("USDZ gallery reimport did not finish")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    # These positions are intentionally fixed and independent of source images.
    views = {
        "front": ((0.0, -1.0, 0.18), (0.0, 0.0, 0.0)),
        "three-quarter": ((0.42, -0.92, 0.32), (0.0, 0.0, 0.0)),
        "clay-detail": ((0.28, -0.72, 0.18), (0.0, 0.0, 0.0)),
        "active-hold": ((0.0, -1.0, 0.18), (0.0, 0.0, 0.0)),
    }
    camera = bpy.data.cameras.new("gallery-camera")
    camera_object = bpy.data.objects.new("gallery-camera", camera)
    scene.collection.objects.link(camera_object)
    scene.camera = camera_object
    from mathutils import Vector
    paths: list[Path] = []
    for view in _fixed_view_names(manifest):
        location, target = views.get(view, views["front"])
        camera_object.location = location
        camera_object.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
        # Fixed view identity is recorded even on Blender versions where the
        # optional camera aiming helper is unavailable.
        scene.render.filepath = str(output / f"{view}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(output / f"{view}.png")
    return tuple(paths)


def render_model_gallery(package: Path, manifest: "MigrationManifest", output: Path) -> tuple[ReviewArtifact, ...]:
    """Verify and render a stable, owner-scoped review gallery."""
    package = Path(package)
    output = _owned_output(Path(output))
    names = _fixed_view_names(manifest)
    # Verification is deliberately before output creation and before Blender.
    report: VerificationReport = verify_model_package(package, _verification_config(package, manifest), render=False)
    if not isinstance(report, VerificationReport):
        raise ValueError("gallery prerequisite did not return a verification report")
    output.mkdir(parents=True, exist_ok=False)
    paths = _render_fixed_views(package, manifest, output)
    if len(paths) != len(names):
        raise ValueError("gallery renderer returned an incomplete view set")
    artifacts = []
    for view, path in zip(names, paths):
        path = Path(path)
        if path.parent != output or path.is_symlink() or not path.is_file():
            raise ValueError("gallery renderer returned an invalid artifact path")
        artifacts.append(ReviewArtifact(view, path, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(artifacts)
