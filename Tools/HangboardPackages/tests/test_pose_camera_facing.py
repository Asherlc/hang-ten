"""Regression: suspended 3D-model canonical poses must present their own
selected contacts to the camera, not the opposite (occluded) face.

Background: ``tension-flash-board`` shipped with a hand-derived "fix" for a
reported gravity/orientation bug that, on closer inspection, was computed
from a raw-mesh-to-model-space mapping that ignored the root ``Xform``
rotation baked into the USDZ (see ``usd_mesh_chain`` docstring). The mistake
was invisible in that mapping's own self-check because the board's body
happens to have a square cross-section, so a plain translation reproduces
the same overall bounding box as the real rotation while silently scrambling
individual contact positions. Two *other* boards (``nature-stone-hanger``
and ``yy-baguette-evo``) turned out to have a real, simpler instance of the
same failure family: a canonical pose rotates the board 180 degrees but
keeps the unposed ``camera.viewDirection``, so the camera ends up looking at
the board from behind the newly-presented face.

This test catches that family mechanically. A pose's rotation is applied
identically to both the declared camera direction and every contact
position (``SuspendedBoardPresentation.boardTransform`` /
``makeCameraFraming`` in ``HangTen/Views/SuspendedBoardPresentation.swift``),
and rotations preserve dot products, so whether the declared direction
opposes a contact's local outward offset is *invariant* under the pose's own
rotation. Checking it against the unrotated model geometry is therefore both
correct and independent of whichever rotation the pose author chose -- no
disputed mesh-to-model mapping games can hide behind "but the rotation fixes
it".

Scope: this only checks poses whose selected contacts sit strongly toward
one of the board's own +Z/-Z extremes (a plain "front face" vs. "back face"
convention). Several evidenced designs deliberately look at a contact from
an oblique or top-on angle instead (Captain Fingerfood's top-rail "jug"
positions, Lattice MXEdge's recess-lip work positions, Baguette Evo's
30-degree "keep the cord V visible" views) -- those are real manufacturer-
evidenced camera choices, not bugs, and a plain "declared direction opposes
contact offset" rule misfires on them because their contacts aren't
Z-dominant to begin with. Restricting to Z-dominant contact groups isolates
exactly the front/back-flip convention where the bug family lives.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from conftest import load_board_catalog_module

REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"

# A contact group's local offset from the body center must be at least this
# close to a pure +/-Z axis before it's treated as a front/back-style face
# (see module docstring "Scope"). Chosen from the real data: legitimate
# non-front/back conventions top out at 0.79 (baguette-evo/central-20-6's
# 60-degree tilt); every genuine front/back pair sits at 0.90+.
_Z_DOMINANCE_THRESHOLD = 0.85

# Required margin by which the declared camera direction must oppose (not
# just fail to align with) the contact offset.
_MIN_OPPOSING_DOT = 0.5


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _normalized(vector: tuple[float, ...]) -> tuple[float, ...] | None:
    length = math.sqrt(_dot(vector, vector))
    if not math.isfinite(length) or length < 1e-9:
        return None
    return tuple(component / length for component in vector)


def _contact_centroids(package_root: Path, descriptor: dict) -> dict[str, tuple[float, float, float]]:
    from hangboard_packages.usd_mesh_chain import extract_world_extents, read_usda_text

    usdz_path = package_root / "assets" / "primary.usdz"
    digest = hashlib.sha256(usdz_path.read_bytes()).hexdigest()
    assert digest == descriptor["modelSHA256"], (
        f"{usdz_path} sha256 does not match descriptor (asset drifted underneath the test)"
    )
    text = read_usda_text(usdz_path)
    _, meshes, _ = extract_world_extents(text)

    node_to_contact = {
        node["nodeID"]: node["contactID"]
        for node in descriptor["nodes"]
        if node.get("role") == "contact"
    }
    per_contact_points: dict[str, list[tuple[float, float, float]]] = {}
    for node_id, contact_id in node_to_contact.items():
        mn, mx = meshes[node_id]
        centroid = tuple((mn[axis] + mx[axis]) / 2 for axis in range(3))
        per_contact_points.setdefault(contact_id, []).append(centroid)
    return {
        contact_id: tuple(
            sum(p[axis] for p in points) / len(points) for axis in range(3)
        )
        for contact_id, points in per_contact_points.items()
    }


def _iter_suspended_presentations(module, package):
    for presentation in package.board.presentations:
        media = presentation.media
        if isinstance(media, module.PresentationMediaModel) and media.suspension is not None:
            yield presentation, media.suspension


def test_suspended_canonical_poses_face_the_camera() -> None:
    from hangboard_packages.usd_mesh_chain import UsdcatUnavailable

    module = load_board_catalog_module()
    inventory = module.discover_board_packages(HANGBOARDS_ROOT, require_complete_inventory=True)

    failures: list[str] = []
    skip_reason: str | None = None
    checked = 0
    for package in inventory.packages:
        for presentation, suspension in _iter_suspended_presentations(module, package):
            descriptor_path = package.root / presentation.media.descriptor_path
            descriptor = json.loads(descriptor_path.read_text())
            body_min = descriptor["modelBounds"]["min"]
            body_max = descriptor["modelBounds"]["max"]
            body_center = tuple((body_min[axis] + body_max[axis]) / 2 for axis in range(3))
            try:
                centroids = _contact_centroids(package.root, descriptor)
            except UsdcatUnavailable as error:
                skip_reason = str(error)
                continue

            for pose_id, pose in suspension.canonical_poses.items():
                contact_ids = package.board.contact_ids_for_position(pose_id)
                offsets = [
                    tuple(centroids[cid][axis] - body_center[axis] for axis in range(3))
                    for cid in contact_ids
                    if cid in centroids
                ]
                normalized_offsets = [o for o in (_normalized(v) for v in offsets) if o is not None]
                if not normalized_offsets:
                    continue
                average_offset = tuple(
                    sum(o[axis] for o in normalized_offsets) / len(normalized_offsets)
                    for axis in range(3)
                )
                direction = _normalized(average_offset)
                if direction is None:
                    # Selected contacts straddle the body center (no net
                    # outward side) -- this check can't say anything useful.
                    continue
                if abs(direction[2]) < _Z_DOMINANCE_THRESHOLD:
                    # Not a front/back-style contact group (top-rail, side,
                    # or a deliberate oblique view) -- out of scope, see
                    # module docstring.
                    continue
                declared = _normalized(tuple(pose.camera["viewDirection"]))
                assert declared is not None, f"{package.board.id}/{pose_id}: non-finite camera.viewDirection"
                checked += 1
                facing = _dot(declared, direction)
                if facing >= -_MIN_OPPOSING_DOT:
                    failures.append(
                        f"{package.board.id}/{pose_id}: camera.viewDirection {pose.camera['viewDirection']} "
                        f"does not oppose its selected contacts' local offset {tuple(round(v, 3) for v in direction)} "
                        f"(dot={facing:+.3f} >= {-_MIN_OPPOSING_DOT:+.2f}); the posed camera would look at the "
                        f"back of the selected face, not the front"
                    )

    assert checked > 0 or skip_reason is not None, (
        "expected at least one suspended canonical pose to check"
    )
    if checked == 0 and skip_reason is not None:
        pytest.skip(skip_reason)
    assert not failures, "pose-camera-facing regressions:\n" + "\n".join(failures)
