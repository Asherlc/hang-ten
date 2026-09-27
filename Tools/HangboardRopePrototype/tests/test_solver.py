"""Integration checks against a real Bullet executable and a synthetic bar."""

import json
import math
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SOLVER = ROOT / ".context/frantic-kiwi/rope-build/rope_solver"


def round_bar_case():
    radius = 0.02
    center_y, center_z = 0.04, 0.04
    steps = 32
    vertices = []
    for x in (-0.08, 0.08):
        for i in range(steps):
            theta = 2 * math.pi * i / steps
            vertices.append([x, center_y + radius * math.cos(theta), center_z + radius * math.sin(theta)])
    faces = []
    for i in range(steps):
        next_i = (i + 1) % steps
        faces.extend([[i, next_i, steps + next_i], [i, steps + next_i, steps + i]])
    for i in range(1, steps - 1):
        faces.extend([[0, i + 1, i], [steps, steps + i, steps + i + 1]])
    return {
        "schemaVersion": 1,
        "modelSHA256": "0" * 64,
        "descriptorSHA256": "1" * 64,
        "suspensionSHA256": "2" * 64,
        "bodyNodeID": "body",
        "vertices": vertices,
        "faces": faces,
        "anchor": [0, 0.24, center_z],
        "loops": [
            {"id": "left-loop", "outer_x": -0.073, "inner_x": -0.061,
             "wrap_side": "opposite-anchor", "radius": 0.002, "rest_length": 0.75},
            {"id": "right-loop", "outer_x": 0.073, "inner_x": 0.061,
             "wrap_side": "opposite-anchor", "radius": 0.002, "rest_length": 0.75},
        ],
        "poses": {"edge-20": {"rotation": [0, 0, 0, 1], "translation": [0, 0, 0]}},
    }


def run_solver(tmp_path, data, name):
    source = tmp_path / f"{name}-case.json"
    result = tmp_path / f"{name}-result.json"
    source.write_text(json.dumps(data))
    completed = subprocess.run(
        [str(SOLVER), "--case", str(source), "--pose", "edge-20",
         "--length-mode", "taut", "--output", str(result)],
        capture_output=True, text=True,
    )
    return completed, json.loads(result.read_text()) if result.exists() else None


def test_rope_settles_around_outside_of_round_bar(tmp_path):
    completed, result = run_solver(tmp_path, round_bar_case(), "normal")
    assert completed.returncode == 0, completed.stderr
    assert result["status"] == "settled"
    assert set(result["loops"]) == {"left-loop", "right-loop"}
    assert result["steps"] > 0
    assert result["iterations"] > 0
    assert result["collisionMargin"] >= 0
    for route in result["loops"].values():
        centers = route["centerline"]
        assert len(centers) >= 32
        assert centers[0] == pytest.approx((0, 0.24, 0.04), abs=1e-5)
        assert centers[-1] == pytest.approx((0, 0.24, 0.04), abs=1e-5)
        assert min(point[1] for point in centers) < 0.02
        inside_span = [point for point in centers if abs(point[0]) < 0.079]
        assert all(math.hypot(point[1] - 0.04, point[2] - 0.04) >= 0.0215
                   for point in inside_span)
        assert min(math.hypot(point[1] - 0.04, point[2] - 0.04) for point in inside_span) < 0.023
    left = result["loops"]["left-loop"]["centerline"]
    right = result["loops"]["right-loop"]["centerline"]
    assert min(point[0] for point in left) < -0.06
    assert max(point[0] for point in right) > 0.06
    assert min(math.dist(a, b) for a in left[40:-40] for b in right[40:-40]) > 0.02


def test_wrong_wrap_topology_is_rejected(tmp_path):
    data = round_bar_case()
    data["loops"][0]["wrap_side"] = "through-body"
    completed, result = run_solver(tmp_path, data, "wrong-side")
    assert completed.returncode != 0
    assert result["status"] == "invalid_topology"


def test_fresh_simulations_are_repeatable(tmp_path):
    first, first_result = run_solver(tmp_path, round_bar_case(), "first")
    second, second_result = run_solver(tmp_path, round_bar_case(), "second")
    assert first.returncode == second.returncode == 0
    for loop_id in ("left-loop", "right-loop"):
        a = first_result["loops"][loop_id]["centerline"]
        b = second_result["loops"][loop_id]["centerline"]
        assert len(a) == len(b)
        assert max(math.dist(p, q) for p, q in zip(a, b)) < 1e-6
