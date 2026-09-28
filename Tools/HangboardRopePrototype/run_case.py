"""Run each Mini Bar pose and length condition in a fresh Bullet process."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run_all(case_path: Path, solver: Path, output_dir: Path, *, bullet_revision: str) -> dict:
    case_path = Path(case_path).resolve()
    solver = Path(solver).resolve()
    output_dir = Path(output_dir)
    case = json.loads(case_path.read_text())
    if case.get("schemaVersion") != 1:
        raise ValueError("unsupported rope case schema")
    manifest = {
        "sources": {key: case[key] for key in ("modelSHA256", "descriptorSHA256", "suspensionSHA256")},
        "bulletRevision": bullet_revision,
        "solver": str(solver),
        "case": str(case_path),
        "runs": [],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for pose_id in sorted(case["poses"]):
        results = {}
        for mode in ("taut", "original"):
            result_path = output_dir / pose_id / f"{mode}.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(
                [str(solver), "--case", str(case_path), "--pose", pose_id,
                 "--length-mode", mode, "--output", str(result_path)],
                capture_output=True, text=True,
            )
            if result_path.exists():
                result = json.loads(result_path.read_text())
            else:
                result = {"status": "error", "reason": "solver produced no output", "stderr": completed.stderr}
                result_path.write_text(json.dumps(result, indent=2) + "\n")
            results[mode] = result
            run = {
                "pose": pose_id, "lengthMode": mode, "path": str(result_path),
                "status": result.get("status", "error"), "exitCode": completed.returncode,
                "accepted": completed.returncode == 0 and result.get("status") == "settled",
                "reason": result.get("reason", ""),
                "steps": result.get("steps"), "convergenceResidual": result.get("convergenceResidual"),
            }
            manifest["runs"].append(run)
        taut_lengths = [route["targetLength"] for route in results["taut"].get("loops", {}).values()]
        original = next(run for run in manifest["runs"] if run["pose"] == pose_id and run["lengthMode"] == "original")
        original_lengths = [loop["rest_length"] for loop in case["loops"]]
        if (original["accepted"] and taut_lengths and
                len(taut_lengths) == len(original_lengths) and
                all(rest > taut + 0.01 for rest, taut in zip(original_lengths, taut_lengths))):
            original["accepted"] = False
            original["reason"] = "0.75 m estimate is slack relative to derived taut length"
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("solver", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--bullet-revision", required=True)
    args = parser.parse_args()
    summary = run_all(args.case, args.solver, args.output_dir, bullet_revision=args.bullet_revision)
    print(json.dumps({"runs": len(summary["runs"]), "accepted": sum(run["accepted"] for run in summary["runs"]) }))
