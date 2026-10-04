"""Regression: suspended 3D-model canonical poses must present their own
selected contacts to the camera, not the opposite (occluded) face.

Background: ``tension-flash-board`` shipped with a hand-derived "fix" for a
reported gravity/orientation bug that, on closer inspection, was computed
from a raw-mesh-to-model-space mapping that ignored the root ``Xform``
rotation baked into the USDZ (see ``usd_mesh_chain`` docstring). The mistake
was invisible in that mapping's own self-check because the board's body
happens to have a square cross-section, so a plain translation reproduces
the same overall bounding box as the real rotation while silently scrambling
individual contact positions. Earlier revisions of ``nature-stone-hanger``
and ``yy-baguette-evo`` also had camera declarations inconsistent with their
selected local faces. The direction is model-relative: a pose half-turn
alone does not require changing its sign, because the renderer rotates the
declared direction with the board.

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
from dataclasses import replace
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


def _contact_centroids(usdz_path: Path, descriptor: dict) -> dict[str, tuple[float, float, float]]:
    from hangboard_packages.usd_mesh_chain import extract_world_extents, read_usda_text

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


@pytest.mark.parametrize(
    ("slug", "position_id", "camera_z_sign"),
    [
        ("nature-stone-hanger", "edge-front-15mm-incut", -1),
        ("nature-stone-hanger", "edge-front-15mm-flat", -1),
        ("nature-stone-hanger", "edge-front-20mm-wood-flat", -1),
        ("nature-stone-hanger", "edge-front-20mm-granite", -1),
        ("nature-stone-hanger", "edge-reverse-10mm-incut", 1),
        ("nature-stone-hanger", "edge-reverse-10mm-flat", 1),
        ("nature-stone-hanger", "edge-reverse-06mm-flat", 1),
        ("nature-stone-hanger", "edge-reverse-06mm-incut", 1),
        ("frictitious-nug", "front-25", -1),
        ("frictitious-nug", "front-inverted-20", -1),
        ("frictitious-nug", "reverse-13", 1),
        ("frictitious-nug", "reverse-inverted-8", 1),
        ("frictitious-port-a-board", "front-upright", -1),
        ("frictitious-port-a-board", "front-inverted", -1),
        ("frictitious-port-a-board", "reverse-upright", 1),
        ("frictitious-port-a-board", "reverse-inverted", 1),
        ("yy-baguette", "front-20-25", -1),
        ("yy-baguette", "reverse-10-15-30", 1),
        ("yy-travelboard", "front-25-15", -1),
        ("yy-travelboard", "reverse-10", 1),
    ],
)
def test_native_front_and_reverse_positions_select_the_evidenced_face(
    slug: str, position_id: str, camera_z_sign: int
) -> None:
    """Retained front/reverse evidence is recorded in each remaining-CAD audit.

    These native sources place front mouths at +Z and rear mouths at -Z.
    A deep floor can cross the body center, so its centroid is not a reliable
    substitute for the documented opening side. Keep that semantic regression
    explicit alongside the general centroid check.
    """
    module = load_board_catalog_module()
    package = module.load_board_package(HANGBOARDS_ROOT / slug)
    poses = [
        suspension.canonical_poses[position_id]
        for _, suspension in _iter_suspended_presentations(module, package)
        if position_id in suspension.canonical_poses
    ]
    assert len(poses) == 1
    direction = _normalized(tuple(poses[0].camera["viewDirection"]))
    assert direction is not None
    assert direction[2] * camera_z_sign > _MIN_OPPOSING_DOT



def _stone_reverse_six_bearing_samples(position_id: str):
    """Bind native display normals through the current contact-preservation proof.

    These are deliberately checked CAD face normals, not maker-measured angles.
    The fitted granite revision preserves all seven wood contact surfaces even
    though its recomputed BRep serialization and overall source hash changed.
    """
    audit = REPO_ROOT / "docs/source-audits/2026-09-29-remaining-cad/nature-stone-hanger"
    native_path = audit / "display-and-pose-review/raw/fresh-native-bearing/new-native-bearing.json"
    preserved_path = audit / "granite-seat-review/independent-native-check.json"
    assert hashlib.sha256(native_path.read_bytes()).hexdigest() == (
        "b3f52e79fa12d5a090c92c0c07afb295e18012e139b0996006ddff185a898137"
    )
    assert hashlib.sha256(preserved_path.read_bytes()).hexdigest() == (
        "42875cd202ca7781150275f1f9310dbbed07fa3686d380927b67c9cc4322ab2b"
    )
    native = json.loads(native_path.read_bytes())
    preserved = json.loads(preserved_path.read_bytes())
    runtime = json.loads((audit / "granite-seat-review/runtime-validation.json").read_bytes())
    package = HANGBOARDS_ROOT / "nature-stone-hanger"
    descriptor = json.loads((package / "assets/primary.model.json").read_bytes())
    artifact = json.loads((package / "assets/suspension.json").read_bytes())
    source = load_board_catalog_module().cad_source.package_source_path(package)
    assert preserved["status"] == runtime["status"] == "pass"
    assert preserved["beforeSHA256"] == native["sourceSHA256"]
    # The audit records the source before metadata was consolidated. Its
    # exported model still binds the native bearing proof to current geometry;
    # the compiled suspension separately binds the current flat CAD document.
    assert preserved["sourceSHA256"] == runtime["sourceSHA256"]
    assert artifact["sourceSHA256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert runtime["modelSHA256"] == descriptor["modelSHA256"] == artifact["modelSHA256"] == hashlib.sha256(
        (package / "assets/primary.usdz").read_bytes()
    ).hexdigest()
    assert runtime["descriptorSHA256"] == hashlib.sha256(
        (package / "assets/primary.model.json").read_bytes()
    ).hexdigest()
    preserved_wood = {
        contact_id for contact_id, proof in preserved["contactInventory"].items()
        if proof["oldMinusNewAreaMM2"] == proof["newMinusOldAreaMM2"] == 0
    }
    assert len(preserved_wood) == 7 and position_id in preserved_wood
    return native["poses"][position_id]["samples"]


def _assert_stone_reverse_six_bearing_and_camera(pose, samples) -> None:
    # Native (X,Y,Z) -> importer (X,Z,-Y). The rear opening faces native +Y,
    # hence model -Z. Rotate the opening normal AND camera with the board.
    x, y, z, w = pose.rotation
    norm2 = x*x + y*y + z*z + w*w
    def rotate(v):
        return (
            ((w*w+x*x-y*y-z*z)*v[0] + 2*(x*y-w*z)*v[1] + 2*(x*z+w*y)*v[2])/norm2,
            (2*(x*y+w*z)*v[0] + (w*w-x*x+y*y-z*z)*v[1] + 2*(y*z-w*x)*v[2])/norm2,
            (2*(x*z-w*y)*v[0] + 2*(y*z+w*x)*v[1] + (w*w-x*x-y*y+z*z)*v[2])/norm2,
        )
    opening = rotate((0, 0, -1))
    camera = _normalized(rotate(tuple(pose.camera["viewDirection"])))
    assert camera is not None and _dot(opening, camera) < -_MIN_OPPOSING_DOT, (
        "camera does not face the native rear opening"
    )
    assert samples
    for sample in samples:
        nx, ny, nz = sample["nativeOutwardBearingNormal"]
        native_to_model = (nx, nz, -ny)
        assert native_to_model == pytest.approx(sample["runtimeBearingNormal"], abs=1e-12)
        assert rotate(native_to_model)[1] > .98, "selected native rail does not bear upward"


@pytest.mark.parametrize("position_id", ["edge-reverse-06mm-flat", "edge-reverse-06mm-incut"])
@pytest.mark.parametrize("mutation", [None, "swapped-rotation", "reversed-camera"])
def test_native_stone_reverse_six_retains_upward_bearing_and_rear_camera(
    position_id: str, mutation: str | None
) -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(HANGBOARDS_ROOT / "nature-stone-hanger")
    pose = package.board.presentations[0].media.suspension.canonical_poses[position_id]
    samples = _stone_reverse_six_bearing_samples(position_id)
    if mutation == "swapped-rotation":
        # The maker drawing puts 6 mm flat above incut, opposite the 10 mm pair.
        # Swapping rotations by name turns both actual 6 mm bearings downward.
        other = "edge-reverse-06mm-incut" if position_id.endswith("flat") else "edge-reverse-06mm-flat"
        other_pose = package.board.presentations[0].media.suspension.canonical_poses[other]
        with pytest.raises(AssertionError, match="does not bear upward"):
            _assert_stone_reverse_six_bearing_and_camera(replace(pose, rotation=other_pose.rotation), samples)
    elif mutation == "reversed-camera":
        camera = {**pose.camera, "viewDirection": [0, 0, -1]}
        with pytest.raises(AssertionError, match="does not face the native rear opening"):
            _assert_stone_reverse_six_bearing_and_camera(replace(pose, camera=camera), samples)
    else:
        _assert_stone_reverse_six_bearing_and_camera(pose, samples)


def _assert_native_baguette_central_pose(board, pose) -> None:
    # The reviewed native bearing is rotated upward; the camera is stored
    # in model coordinates. A deep-floor centroid is not its opening normal.
    # yy-baguette-evo/individual-review-2026-10-01/review.md:39 and its
    # orientation-audit/recommendation.json + actual-camera-sidecar-check.json.
    assert board.contact_ids_for_position("central-20-6") == ("edge-central-20",)
    assert pose.rotation == pytest.approx((math.sqrt(.5), 0, 0, math.sqrt(.5)), abs=1e-8)
    assert pose.rotation[0] > 0 and pose.rotation[3] > 0
    camera = tuple(pose.camera["viewDirection"])
    assert camera == pytest.approx((0, -.939692621, .342020143), abs=1e-9)
    x, y, z, w = pose.rotation
    # Quaternion rotation, q * v * inverse(q), normalized for serialized q.
    norm2 = x*x + y*y + z*z + w*w
    world = (
        ((w*w+x*x-y*y-z*z)*camera[0] + 2*(x*y-w*z)*camera[1] + 2*(x*z+w*y)*camera[2])/norm2,
        (2*(x*y+w*z)*camera[0] + (w*w-x*x+y*y-z*z)*camera[1] + 2*(y*z-w*x)*camera[2])/norm2,
        (2*(x*z-w*y)*camera[0] + 2*(y*z+w*x)*camera[1] + (w*w-x*x-y*y+z*z)*camera[2])/norm2,
    )
    assert world == pytest.approx((0, -.342020143, -.939692621), abs=1e-8)
    assert world[1] < 0 and world[2] < -_MIN_OPPOSING_DOT


def test_native_baguette_central_pose_retains_bearing_and_camera_frame() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(HANGBOARDS_ROOT / "yy-baguette-evo")
    pose = package.board.presentations[0].media.suspension.canonical_poses["central-20-6"]
    _assert_native_baguette_central_pose(package.board, pose)


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
                centroids = _contact_centroids(
                    package.root / presentation.media.asset_path, descriptor
                )
            except UsdcatUnavailable as error:
                skip_reason = str(error)
                continue

            for pose_id, pose in suspension.canonical_poses.items():
                contact_ids = package.board.contact_ids_for_position(pose_id)
                if package.board.id == "yy.baguette-evo" and pose_id == "central-20-6":
                    _assert_native_baguette_central_pose(package.board, pose)
                    checked += 1
                    continue
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
