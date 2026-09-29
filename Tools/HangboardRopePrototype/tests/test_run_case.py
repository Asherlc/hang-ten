"""The runner must retain every independent simulation and its provenance."""

import json
from pathlib import Path

import pytest

from Tools.HangboardRopePrototype.run_case import run_all


def test_eight_runs_and_slack_failure(tmp_path: Path):
    fixture = {
        "schemaVersion": 1,
        "modelSHA256": "a" * 64,
        "descriptorSHA256": "b" * 64,
        "suspensionSHA256": "c" * 64,
        "anchor": [0, 0.2, 0],
        "loops": [{"id": side, "rest_length": 0.75} for side in ("left-loop", "right-loop")],
        "poses": {pose: {} for pose in ("edge-10", "edge-20", "ergonomic-jug", "mini-pinch")},
    }
    case = tmp_path / "case.json"
    case.write_text(json.dumps(fixture))
    solver = tmp_path / "fake_solver.py"
    solver.write_text("""#!/usr/bin/env python3
import argparse, json
p=argparse.ArgumentParser()
for key in ('case','pose','length-mode','output'): p.add_argument('--'+key)
a=p.parse_args()
loops={side:{'targetLength':0.49,'centerline':[[0,.2,0],[0,0,0],[0,.2,0]]}
       for side in ('left-loop','right-loop')}
open(a.output,'w').write(json.dumps({'status':'settled','loops':loops,'steps':480}))
""")
    solver.chmod(0o755)
    manifest = run_all(case, solver, tmp_path / "results", bullet_revision="test-revision")
    assert len(manifest["runs"]) == 8
    assert len(list((tmp_path / "results").glob("*/*.json"))) == 8
    assert manifest["sources"]["modelSHA256"] == "a" * 64
    assert manifest["bulletRevision"] == "test-revision"
    assert all(run["reason"] == "0.75 m estimate is slack relative to derived taut length"
               for run in manifest["runs"] if run["lengthMode"] == "original")
    assert all(run["status"] == "settled" for run in manifest["runs"] if run["lengthMode"] == "taut")


def test_failed_solver_output_is_retained(tmp_path: Path):
    case = tmp_path / "case.json"
    case.write_text(json.dumps({"schemaVersion": 1, "modelSHA256": "a", "descriptorSHA256": "b",
                                "suspensionSHA256": "c", "poses": {"edge-20": {}},
                                "loops": [{"id": "left-loop", "rest_length": .75}]}))
    solver = tmp_path / "fail.py"
    solver.write_text("""#!/usr/bin/env python3
import sys, json
open(sys.argv[sys.argv.index('--output')+1], 'w').write(json.dumps({'status':'nonconverged','reason':'limit'}))
sys.exit(2)
""")
    solver.chmod(0o755)
    manifest = run_all(case, solver, tmp_path / "results", bullet_revision="test-revision")
    assert len(manifest["runs"]) == 2
    assert all(run["status"] == "nonconverged" for run in manifest["runs"])
    assert (tmp_path / "results/edge-20/taut.json").exists()
