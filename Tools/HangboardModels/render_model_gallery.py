"""Deterministic review gallery generation for verified model packages.

This module deliberately imports Blender only inside the render operation.  The
package and descriptor are the only rendering inputs; source blends and source
images are never opened by the gallery.
"""

from __future__ import annotations

import hashlib
import math
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


@dataclass(frozen=True)
class OrthographicFrame:
    target: tuple[float, float, float]
    location: tuple[float, float, float]
    ortho_scale: float
    clip_start: float
    clip_end: float
    camera_type: str = "ORTHO"
    sensor_fit: str = "VERTICAL"


def _orthographic_frame(points, direction, *, aspect_ratio: float, margin: float = 1.1) -> OrthographicFrame:
    """Fit world-space imported mesh bounds with fixed direction and Z-up.

    With vertical sensor fit, ``ortho_scale`` is the image's world-space height.
    Projecting every bound corner also accounts for depth in oblique views.
    """
    points = tuple(tuple(point) for point in points)
    if not points or any(len(point) != 3 or not all(math.isfinite(v) for v in point) for point in points):
        raise ValueError("gallery requires finite imported mesh bounds")
    if not math.isfinite(aspect_ratio) or aspect_ratio <= 0 or not math.isfinite(margin) or margin < 1:
        raise ValueError("gallery aspect ratio must be positive and margin at least one")
    if len(direction) != 3 or not all(math.isfinite(v) for v in direction) or math.hypot(*direction[:2]) == 0:
        raise ValueError("gallery direction must be finite and nonvertical")
    target = tuple((min(p[i] for p in points) + max(p[i] for p in points)) / 2 for i in range(3))
    offsets = [tuple(p[i] - target[i] for i in range(3)) for p in points]
    radius = max(math.hypot(*offset) for offset in offsets)
    if radius <= 0:
        raise ValueError("gallery requires nondegenerate imported mesh bounds")
    back = tuple(v / math.hypot(*direction) for v in direction)
    horizontal = math.hypot(*back[:2])
    right = (-back[1] / horizontal, back[0] / horizontal, 0.0)
    up = (-back[2] * right[1], back[2] * right[0], back[0] * right[1] - back[1] * right[0])
    width = 2 * max(abs(sum(v * axis for v, axis in zip(offset, right))) for offset in offsets)
    height = 2 * max(abs(sum(v * axis for v, axis in zip(offset, up))) for offset in offsets)
    return OrthographicFrame(
        target=target,
        location=tuple(target[i] + 3 * radius * back[i] for i in range(3)),
        ortho_scale=max(height, width / aspect_ratio) * margin,
        clip_start=radius / 100,
        clip_end=5 * radius,
    )


def _owner() -> str:
    return _workspace_root().name


def _workspace_root() -> Path:
    """Return the configured, canonical workspace root.

    Gallery output is intentionally restricted to this workspace's real
    ``.context`` directory.  Resolving and then comparing the paths prevents
    a symlinked workspace or context directory from escaping that boundary.
    """
    configured = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).absolute()
    canonical = configured.resolve()
    if not configured.is_dir() or configured.is_symlink() or canonical != configured:
        raise ValueError("gallery workspace root must be canonical and existing")
    return configured


def _workspace_context() -> Path:
    workspace = _workspace_root()
    context = workspace / ".context"
    canonical = context.resolve()
    if not context.is_dir() or context.is_symlink() or canonical != context:
        raise ValueError("gallery .context root must be canonical and existing")
    return context


def _owned_output(output: Path) -> Path:
    output = Path(output).absolute()
    if output.name == "" or not output.name.startswith(_owner() + "-"):
        raise ValueError("gallery output must be owner-prefixed")
    context = _workspace_context()
    if output.parent != context:
        raise ValueError("gallery output must be workspace-owned and directly under .context")
    if output.exists() and output.is_symlink():
        raise ValueError("gallery output must not be a symlink")
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
        triangle_ceiling=manifest.verification.triangle_ceiling,
    )


def _fixed_view_names(manifest: "MigrationManifest") -> tuple[str, ...]:
    if not manifest.review_views:
        raise ValueError("gallery requires at least one reviewed view")
    names = tuple(manifest.review_views)
    allowed = {"front", "three-quarter", "clay-detail", "active-hold"}
    if any(value not in allowed for value in names):
        raise ValueError("unsupported gallery review view name")
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
    from mathutils import Vector
    bounds = [tuple(obj.matrix_world @ Vector(corner))
              for obj in scene.objects if obj.type == "MESH" for corner in obj.bound_box]
    # Directions are fixed; imported package bounds determine center and scale.
    views = {
        "front": (0.0, -1.0, 0.18),
        "three-quarter": (0.42, -0.92, 0.32),
        "clay-detail": (0.28, -0.72, 0.18),
        "active-hold": (0.0, -1.0, 0.18),
    }
    camera = bpy.data.cameras.new("gallery-camera")
    camera_object = bpy.data.objects.new("gallery-camera", camera)
    scene.collection.objects.link(camera_object)
    scene.camera = camera_object
    paths: list[Path] = []
    for view in _fixed_view_names(manifest):
        frame = _orthographic_frame(bounds, views[view], aspect_ratio=scene.render.resolution_x / scene.render.resolution_y)
        camera.type = frame.camera_type
        camera.sensor_fit = frame.sensor_fit
        camera.ortho_scale = frame.ortho_scale
        camera.clip_start = frame.clip_start
        camera.clip_end = frame.clip_end
        camera_object.location = frame.location
        camera_object.rotation_euler = (Vector(frame.target) - Vector(frame.location)).to_track_quat("-Z", "Y").to_euler()
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
