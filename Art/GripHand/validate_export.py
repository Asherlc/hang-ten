"""Validate the baked surface contract independently of Blender."""
import json
import math
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "HangTen/Resources/GripHand/hand-mesh.json"

def validate(data):
    assert data.get("schemaVersion") == 2, "Expected evaluated surface schema 2"
    required = {"Neutral", "OpenHand", "HalfCrimp", "FullCrimp", "Sloper"} | {f"Pocket{i}" for i in range(16)}
    assert required <= data["poses"].keys(), "Missing grip or finger combination"
    count = len(data["digitIndices"])
    assert count > 1000
    assert set(data["digitIndices"]) == set(range(6)), "Missing digit regions"
    assert len(data["highlightWeights"]) == count
    assert all(math.isfinite(x) and 0 <= x <= 1 for x in data["highlightWeights"])
    assert len(data["indices"]) % 3 == 0
    assert all(type(x) is int and 0 <= x < count for x in data["indices"])
    for name, pose in data["poses"].items():
        assert len(pose["positions"]) == len(pose["normals"]) == count * 3, name
        assert all(math.isfinite(x) for key in ("positions", "normals") for x in pose[key]), name
        lengths = [sum(x*x for x in pose["normals"][i:i+3]) for i in range(0,count*3,3)]
        assert all(.98 < x < 1.02 for x in lengths), f"Invalid normals: {name}"
    assert data["poses"]["Pocket0"] == data["poses"]["Pocket15"], "Unknown fingers should use the all-open surface"
    for bit, digit in enumerate(range(2,6)):
        sample = [i for i,d in enumerate(data["digitIndices"]) if d == digit and data["highlightWeights"][i] > .999]
        # Check distal segment interiors; webbing and shared MCP skin may
        # legitimately move slightly when a neighboring finger tucks.
        rest = data["poses"]["Neutral"]["positions"]
        tip_y = max(rest[i*3+1] for i in sample)
        sample = [i for i in sample if rest[i*3+1] > tip_y - .5]
        assert sample
        base = data["poses"]["Pocket15"]["positions"]
        for mask in range(1,16):
            posed = data["poses"][f"Pocket{mask}"]["positions"]
            movement = max(abs(posed[i*3+j]-base[i*3+j]) for i in sample for j in range(3))
            assert movement < .001 if mask & (1 << bit) else movement > .2, (mask,digit,movement)
    print(f"Validated {count:,} vertices, {len(data['indices'])//3:,} triangles, {len(data['poses'])} evaluated poses")

if __name__ == "__main__":
    validate(json.loads(PATH.read_text()))
