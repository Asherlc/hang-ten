"""Export a hash-bound rigid-body mesh and exterior-loop setup for an offline test."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from pxr import Gf, Usd, UsdGeom


@dataclass(frozen=True)
class Loop:
    id: str
    outer_x: float
    inner_x: float
    wrap_side: str
    radius: float
    rest_length: float


@dataclass(frozen=True)
class RopeCase:
    model_sha256: str
    descriptor_sha256: str
    suspension_sha256: str
    body_node_id: str
    vertices: list[tuple[float, float, float]]
    faces: list[tuple[int, int, int]]
    anchor: tuple[float, float, float]
    loops: list[Loop]
    poses: dict[str, dict]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_body_mesh(path: Path, body_id: str) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise ValueError(f"cannot open body USD mesh: {path}")
    bodies = [prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Mesh) and prim.GetName() == body_id]
    if len(bodies) != 1:
        raise ValueError(f"expected one body mesh named {body_id}, found {len(bodies)}")
    prim = bodies[0]
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    if points is None or counts is None or indices is None or not points or not counts:
        raise ValueError("body mesh has no triangles")
    if any(count != 3 for count in counts) or len(indices) != 3 * len(counts):
        raise ValueError("body mesh must contain only triangles")
    if any(index < 0 or index >= len(points) for index in indices):
        raise ValueError("body triangle index outside vertex array")
    transform = UsdGeom.XformCache().GetLocalToWorldTransform(prim)
    vertices = [tuple(float(value) for value in transform.Transform(Gf.Vec3d(*point))) for point in points]
    if not all(math.isfinite(value) for vertex in vertices for value in vertex):
        raise ValueError("body mesh has nonfinite points")
    faces = [tuple(int(index) for index in indices[i : i + 3]) for i in range(0, len(indices), 3)]
    return vertices, faces


def load_case(package: Path) -> RopeCase:
    package = Path(package)
    model_path = package / "assets/primary.usdz"
    descriptor_path = package / "assets/primary.model.json"
    suspension_path = package / "suspension.json"
    descriptor = json.loads(descriptor_path.read_text())
    sidecar = json.loads(suspension_path.read_text())
    model_sha = _sha256(model_path)
    if descriptor.get("modelSHA256") != model_sha or sidecar.get("modelSHA256") != model_sha:
        raise ValueError("USDZ, descriptor, and suspension SHA-256 mismatch")
    if sidecar.get("presentationID") != "primary" or sidecar.get("schemaVersion") != 1:
        raise ValueError("unsupported suspension sidecar")
    body_ids = [node["nodeID"] for node in descriptor["nodes"] if node["role"] == "body"]
    if len(body_ids) != 1:
        raise ValueError("expected one descriptor body node")
    vertices, faces = read_body_mesh(model_path, body_ids[0])
    bounds = descriptor["modelBounds"]
    minimum, maximum = bounds["min"], bounds["max"]
    for axis in range(3):
        if not math.isclose(min(vertex[axis] for vertex in vertices), minimum[axis], abs_tol=2e-6):
            raise ValueError("body mesh bounds differ from descriptor")
        if not math.isclose(max(vertex[axis] for vertex in vertices), maximum[axis], abs_tol=2e-6):
            raise ValueError("body mesh bounds differ from descriptor")

    suspension = sidecar["suspension"]
    if suspension.get("type") != "twoBranchCord":
        raise ValueError("expected exterior two-branch cord")
    if "internalLoop" in suspension:
        raise ValueError("internal-loop suspension is not supported by the exterior-wrap prototype")
    offset = suspension["anchor"]["offsetFromBoardBounds"]
    anchor = (
        (minimum[0] + maximum[0]) / 2 + offset[0],
        maximum[1] + offset[1],
        (minimum[2] + maximum[2]) / 2 + offset[2],
    )
    passages = suspension["passages"]
    passage_by_id = {passage["id"]: passage for side in passages.values() for passage in side}
    loops = []
    for branch in suspension["branches"]:
        first, second = (passage_by_id[passage_id] for passage_id in branch["passageIDs"])
        if first["nodeID"] != body_ids[0] or second["nodeID"] != body_ids[0]:
            raise ValueError("loop passage is not bound to body")
        loops.append(Loop(
            id=branch["id"],
            outer_x=float(first["pointInModel"][0]),
            inner_x=float(second["pointInModel"][0]),
            wrap_side="opposite-anchor",  # Approved exterior Mini Bar topology for this pilot.
            radius=float(branch["radius"]),
            rest_length=float(branch["restLength"]),
        ))
    if len(loops) != 2 or any(not math.isfinite(value) or value <= 0 for loop in loops for value in (loop.radius, loop.rest_length)):
        raise ValueError("expected two finite exterior loops")
    poses = suspension["canonicalPoses"]
    if set(poses) != {"edge-10", "edge-20", "ergonomic-jug", "mini-pinch"}:
        raise ValueError("Mini Bar needs four canonical poses")
    return RopeCase(
        model_sha256=model_sha,
        descriptor_sha256=_sha256(descriptor_path),
        suspension_sha256=_sha256(suspension_path),
        body_node_id=body_ids[0],
        vertices=vertices,
        faces=faces,
        anchor=anchor,
        loops=loops,
        poses={key: {"rotation": poses[key]["rotation"], "translation": poses[key]["translation"]} for key in sorted(poses)},
    )


def write_case(case: RopeCase, path: Path) -> None:
    payload = {
        "schemaVersion": 1,
        "modelSHA256": case.model_sha256,
        "descriptorSHA256": case.descriptor_sha256,
        "suspensionSHA256": case.suspension_sha256,
        "bodyNodeID": case.body_node_id,
        "vertices": case.vertices,
        "faces": case.faces,
        "anchor": case.anchor,
        "loops": [asdict(loop) for loop in case.loops],
        "poses": case.poses,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_case(load_case(args.package), args.output)
