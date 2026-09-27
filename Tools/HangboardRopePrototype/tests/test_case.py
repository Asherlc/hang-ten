import hashlib
import json
import math
import shutil
from pathlib import Path

import pytest
from pxr import Gf, Usd, UsdGeom

from Tools.HangboardRopePrototype.case import load_case, read_body_mesh, write_case


PACKAGE = Path(__file__).resolve().parents[3] / "Hangboards/lattice-mini-bar"
EXPECTED_SHA = "5f6744d3aeede10cc2b3c5f6f9dc19df1bb985c94991192ec8f2044c32932c46"


def copy_package(tmp_path):
    target = tmp_path / "lattice-mini-bar"
    shutil.copytree(PACKAGE, target, ignore=shutil.ignore_patterns("*.FCStd"))
    return target


def test_real_case_uses_hash_bound_body_and_all_poses(tmp_path):
    case = load_case(PACKAGE)
    assert hashlib.sha256((PACKAGE / "assets/primary.usdz").read_bytes()).hexdigest() == EXPECTED_SHA
    assert case.model_sha256 == EXPECTED_SHA
    assert len(case.vertices) > 100
    assert len(case.faces) > 100
    assert set(case.poses) == {"edge-10", "edge-20", "ergonomic-jug", "mini-pinch"}
    assert case.anchor == pytest.approx((0.0, 0.243020565, 0.036151047), abs=1e-8)
    assert {loop.id for loop in case.loops} == {"left-loop", "right-loop"}
    assert all(loop.wrap_side == "opposite-anchor" for loop in case.loops)
    assert all(loop.radius == pytest.approx(0.002) for loop in case.loops)
    assert all(loop.rest_length == pytest.approx(0.75) for loop in case.loops)
    minimum = tuple(min(v[i] for v in case.vertices) for i in range(3))
    maximum = tuple(max(v[i] for v in case.vertices) for i in range(3))
    assert minimum == pytest.approx((-0.077500001, 0.008, 0.004308133), abs=2e-6)
    assert maximum == pytest.approx((0.077500001, 0.063020565, 0.067993961), abs=2e-6)

    out = tmp_path / "case.json"
    write_case(case, out)
    payload = json.loads(out.read_text())
    assert payload["schemaVersion"] == 1
    assert payload["modelSHA256"] == EXPECTED_SHA
    assert len(payload["faces"]) == len(case.faces)
    assert list(payload["poses"]) == sorted(case.poses)


@pytest.mark.parametrize("file_name", ["assets/primary.model.json", "suspension.json"])
def test_rejects_a_stale_model_hash(tmp_path, file_name):
    package = copy_package(tmp_path)
    path = package / file_name
    data = json.loads(path.read_text())
    data["modelSHA256"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="SHA-256"):
        load_case(package)


def test_rejects_missing_bound_body_node(tmp_path):
    package = copy_package(tmp_path)
    path = package / "assets/primary.model.json"
    data = json.loads(path.read_text())
    next(node for node in data["nodes"] if node["role"] == "body")["nodeID"] = "missing_body"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="body"):
        load_case(package)


def synthetic_usd(path, points, counts):
    stage = Usd.Stage.CreateNew(str(path))
    parent = UsdGeom.Xform.Define(stage, "/root")
    parent.AddTranslateOp().Set(Gf.Vec3d(0.1, 0.2, 0.3))
    mesh = UsdGeom.Mesh.Define(stage, "/root/body")
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr(list(range(sum(counts))))
    stage.GetRootLayer().Save()


def test_mesh_reader_applies_parent_transform(tmp_path):
    path = tmp_path / "shifted.usda"
    synthetic_usd(path, [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [3])
    vertices, faces = read_body_mesh(path, "body")
    assert vertices[0] == pytest.approx((0.1, 0.2, 0.3))
    assert faces == [(0, 1, 2)]


@pytest.mark.parametrize("points,counts", [
    ([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [4]),
    ([(0, 0, 0), (math.nan, 0, 0), (0, 1, 0)], [3]),
])
def test_mesh_reader_rejects_nontriangles_and_nonfinite_points(tmp_path, points, counts):
    path = tmp_path / "bad.usda"
    synthetic_usd(path, points, counts)
    with pytest.raises(ValueError, match="triangle|nonfinite"):
        read_body_mesh(path, "body")
