#!/usr/bin/env python3
"""Copy frozen review evidence only after the root cleanup gate; preserve every byte."""
import argparse, datetime, hashlib, json, shutil
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot(base):
    included, excluded = {}, []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(base)
        if any(part.startswith("DerivedData") or part.startswith("Products-placid-badger-cad-second-half") or part.endswith(".xcresult") for part in relative.parts):
            excluded.append(relative.as_posix())
        else:
            included[relative.as_posix()] = {"sha256": sha(path), "bytes": path.stat().st_size}
    return included, excluded

parser = argparse.ArgumentParser()
parser.add_argument("--execute", action="store_true", help="Root explicitly released the cleanup gate")
parser.add_argument("--cleanup-proof", type=Path, action="append", required=True,
                    help="Repeat for the 26.5 and 26.4 cleanup records")
args = parser.parse_args()
if not args.execute:
    parser.error("No copy without explicit --execute after root cleanup gate")
assert len(args.cleanup_proof) == 2, "Both runtime cleanup records are required"
assert len({p.resolve() for p in args.cleanup_proof}) == 2, "Cleanup records must be distinct"
owner = Path(".context/placid-badger-cad-second-half/zlagboard-evo")
cleanup_by_uuid = {}
for proof_path in args.cleanup_proof:
    proof = json.loads(proof_path.read_bytes())
    assert proof.get("simulatorDeleted") is True, f"Simulator cleanup is not confirmed: {proof_path}"
    assert all(value is True for key, value in proof.items() if key.endswith("Deleted")), "Cleanup has an incomplete deletion"
    assert proof.get("uuid") and proof["uuid"] not in cleanup_by_uuid, "Missing or duplicate cleanup UUID"
    cleanup_by_uuid[proof["uuid"]] = proof
for run, resources in [
    ("ios-resume-2026-10-02", {"derivedData": "derivedDataDeleted", "resultBundle": "resultBundleDeleted", "testResultBundle": "testResultBundleDeleted"}),
    ("ios-26-4", {"preservedProducts": "preservedProductsDeleted"}),
]:
    ownership = json.loads((owner / run / "ownership.json").read_bytes())
    assert ownership["owner"] == "placid-badger-cad-second-half"
    cleanup = cleanup_by_uuid[ownership["simulator"]]
    for resource, deletion_flag in resources.items():
        assert cleanup.get(deletion_flag) is True, f"Owned resource cleanup unconfirmed: {run}/{resource}"
        resource_path = Path(ownership[resource])
        assert resource_path.resolve().is_relative_to((owner / run).resolve()), resource_path
        assert not resource_path.exists(), f"Owned resource still exists: {resource_path}"
    if run == "ios-26-4":
        assert "derivedData" not in ownership and "resultBundle" not in ownership
        assert cleanup.get("derivedDataCreated") is False and cleanup.get("resultBundleCreated") is False
target = Path("docs/source-audits/2026-09-29-remaining-cad/zlagboard-evo/app-review-2026-10-02")
report = {"timestampUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "cleanupProofs": [{"path": str(p), "sha256": sha(p)} for p in args.cleanup_proof], "groups": {}}
aggregate = []
for name, source in [("ios", owner / "ios-resume-2026-10-02"),
                     ("independent", owner / "ios-resume-2026-10-02-independent"),
                     ("ios-26-4", owner / "ios-26-4"),
                     ("runtime-inventory", owner / "ios-baseline-26-4")]:
    before, excluded = snapshot(source)
    assert before, f"Empty evidence source: {source}"
    destination = target / name
    for relative, evidence in before.items():
        original, copied = source / relative, destination / relative
        if copied.exists():
            assert sha(copied) == evidence["sha256"], f"Refusing to overwrite different retained proof: {copied}"
        else:
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, copied)
        assert sha(copied) == evidence["sha256"] and copied.stat().st_size == evidence["bytes"], copied
        aggregate.append((f"{name}/{relative}", f'{evidence["sha256"]}  {name}/{relative}\n'))
    after, after_excluded = snapshot(source)
    assert before == after and excluded == after_excluded, f"Source evidence changed during copy: {source}"
    actual, unexpected_exclusions = snapshot(destination)
    assert actual == before and not unexpected_exclusions, f"Destination differs or includes extras: {destination}"
    report["groups"][name] = {"source": str(source), "destination": str(destination),
                             "files": before, "fileCount": len(before),
                             "bytes": sum(v["bytes"] for v in before.values()),
                             "excludedResourcePaths": excluded, "sourceStable": True, "copyExact": True}
# Explicitly retain the harness inventory and this copy recipe as proof provenance.
script_inventory = owner / "packet-copy-2026-10-02/support-scripts.json"
script_paths = json.loads(script_inventory.read_bytes())["paths"]
assert len(script_paths) == len(set(script_paths)), "Duplicate support script"
expected_harnesses = {p.relative_to(owner).as_posix() for p in (owner / "prep").iterdir()
                      if p.is_file() and (p.name.startswith(("resume-", "highlight-", "baseline26-"))
                      or p.name in ("all-code-parity.py", "baseline-restored-build.zsh"))}
assert expected_harnesses == {p for p in script_paths if p.startswith("prep/")}, "Refresh explicit harness inventory after the worker freezes scripts"
script_files = {}
for relative in sorted(script_paths):
    original = owner / relative
    assert original.is_file() and original.resolve().is_relative_to(owner.resolve()), original
    evidence = {"sha256": sha(original), "bytes": original.stat().st_size}
    copied = target / "scripts" / relative
    if copied.exists():
        assert sha(copied) == evidence["sha256"], f"Refusing to overwrite support evidence: {copied}"
    else:
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, copied)
    assert sha(original) == sha(copied) == evidence["sha256"] and copied.stat().st_size == evidence["bytes"], copied
    script_files[relative] = evidence
    aggregate.append((f"scripts/{relative}", f'{evidence["sha256"]}  scripts/{relative}\n'))
actual_scripts, excluded_scripts = snapshot(target / "scripts")
assert actual_scripts == script_files and not excluded_scripts
report["groups"]["scripts"] = {"source": "explicit support-scripts.json inventory", "destination": str(target / "scripts"),
    "files": script_files, "fileCount": len(script_files), "bytes": sum(v["bytes"] for v in script_files.values()),
    "excludedResourcePaths": [], "sourceStable": True, "copyExact": True}
report["fileCount"] = sum(group["fileCount"] for group in report["groups"].values())
report["aggregateSHA256"] = hashlib.sha256("".join(line for _, line in sorted(aggregate)).encode()).hexdigest()
report["aggregateFormat"] = "SHA256 of UTF8 <fileSHA256><two spaces><relative path><LF> lines sorted by relative path"
report["pass"] = True
output = owner / "packet-copy-2026-10-02/copy-verification.json"
assert not output.exists(), "Keep historical copy verification immutable"
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"pass": True, "fileCount": report["fileCount"], "aggregateSHA256": report["aggregateSHA256"],
                  "groups": {k: {f: v[f] for f in ["fileCount", "bytes", "copyExact", "sourceStable"]} for k, v in report["groups"].items()},
                  "report": str(output)}, indent=2))
