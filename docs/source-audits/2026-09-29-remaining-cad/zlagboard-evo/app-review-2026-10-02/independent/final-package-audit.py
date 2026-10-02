#!/usr/bin/env python3
"""Read-only audit. Invoke with rtk proxy python3. Only report output is written.
Default does not run Simulator commands or claim live cleanup. After runtime exit,
use --live-cleanup --ownership <exact ownership.json> (repeatable). A later explicit
request may additionally enable --allow-simulator-list for read-only simctl list.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

BASELINE = "1f5a5865050c96bf89e67b1929099205dcbd6827"
AUDIT = "docs/source-audits/2026-09-29-remaining-cad/"
BOARD = AUDIT + "zlagboard-evo/"
QUEUE = AUDIT + "review-queue.json"
LOCK = "docs/model-delivery-lock.json"
OWNERSHIP = AUDIT + "second-half-ownership.md"
PACKETS = {"individual-review-2026-10-01": 199, "runtime-recovery-2026-10-02": 38}


def command(*args, data=None):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f"{args!r}: {result.returncode}: {result.stderr.decode(errors='replace')}")
    return result.stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pointer(data):
    if not data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        return None
    oid = re.search(rb"^oid sha256:([0-9a-f]{64})$", data, re.M)
    size = re.search(rb"^size ([0-9]+)$", data, re.M)
    return (oid[1].decode(), int(size[1])) if oid and size else None


def raw_object_values(text):
    decoder = json.JSONDecoder()
    i = text.index("{") + 1
    values = {}
    while True:
        while text[i].isspace() or text[i] == ",":
            i += 1
        if text[i] == "}":
            return values
        key, i = decoder.raw_decode(text, i)
        while text[i].isspace():
            i += 1
        assert text[i] == ":"
        i += 1
        while text[i].isspace():
            i += 1
        start = i
        _, i = decoder.raw_decode(text, i)
        values[key] = text[start:i]


def raw_array_values(text):
    decoder = json.JSONDecoder()
    i = text.index("[") + 1
    values = []
    while True:
        while text[i].isspace() or text[i] == ",":
            i += 1
        if text[i] == "]":
            return values
        start = i
        _, i = decoder.raw_decode(text, i)
        values.append(text[start:i])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("final-package-audit-report.json"))
    parser.add_argument("--packet", default=BOARD + "app-review-2026-10-02")
    parser.add_argument("--require-final-packet", action="store_true")
    parser.add_argument("--coordination", type=Path, default=Path(__file__).with_name("shared-code-coordination.json"))
    parser.add_argument("--live-cleanup", action="store_true")
    parser.add_argument("--ownership", type=Path, action="append", default=[])
    parser.add_argument("--allow-simulator-list", action="store_true")
    args = parser.parse_args()
    root = Path(command("git", "rev-parse", "--show-toplevel").decode().strip())
    os.chdir(root)
    scratch = root / ".context/placid-badger-cad-second-half/zlagboard-evo"
    output = args.output.resolve()
    if not output.is_relative_to(scratch.resolve()):
        parser.error("Report output must remain under this board's owned scratch directory")
    if args.allow_simulator_list and not args.live_cleanup:
        parser.error("--allow-simulator-list requires --live-cleanup and later explicit authorization")
    report = {"timestampUTC": datetime.now(timezone.utc).isoformat(),
              "baseline": args.baseline, "head": command("git", "rev-parse", "HEAD").decode().strip(),
              "readOnly": True, "humanAcceptance": False}
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)

    baseline_paths = command("git", "ls-tree", "-r", "--name-only", "-z", args.baseline).decode().split("\0")[:-1]
    tracked_paths = command("git", "ls-files", "-z").decode().split("\0")[:-1]
    untracked = command("git", "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")[:-1]
    attrs = command("git", "check-attr", "-z", "--stdin", "filter",
                    data="\0".join(baseline_paths).encode() + b"\0").decode().split("\0")[:-1]
    filters = {attrs[i]: attrs[i + 2] for i in range(0, len(attrs), 3)}
    lfs_env = command("git", "lfs", "env").decode()
    media_line = next(line for line in lfs_env.splitlines() if line.startswith("LocalMediaDir="))
    media = Path(media_line.split("=", 1)[1])
    blob_cache = {}
    def blob(path):
        if path not in blob_cache:
            blob_cache[path] = command("git", "show", f"{args.baseline}:{path}")
        return blob_cache[path]
    def compare(path, verify_object=False):
        expected = blob(path)
        actual_path = Path(path)
        actual = actual_path.read_bytes() if actual_path.is_file() else None
        managed = filters.get(path) == "lfs"
        info = pointer(expected) if managed else None
        row = {"path": path, "lfsManaged": managed}
        if info:
            oid, size = info
            row.update(expectedSHA256=oid, expectedBytes=size,
                       workingTreeReal=actual is not None and pointer(actual) is None,
                       actualSHA256=sha(actual) if actual is not None else None,
                       byteExact=actual is not None and len(actual) == size and sha(actual) == oid)
            if verify_object:
                obj = media / oid[:2] / oid[2:4] / oid
                data = obj.read_bytes() if obj.is_file() else None
                row.update(lfsObject=str(obj), lfsObjectMatches=data is not None and len(data) == size and sha(data) == oid)
        else:
            row.update(expectedSHA256=sha(expected), actualSHA256=sha(actual) if actual is not None else None,
                       byteExact=actual == expected)
            if pointer(expected):
                row["literalPointerTextComparedAsOrdinaryEvidence"] = True
        return row

    packages = sorted(p for p in baseline_paths if p.startswith("Hangboards/"))
    now_packages = sorted(p for p in tracked_paths if p.startswith("Hangboards/"))
    check(packages == now_packages, "Tracked Hangboards file inventory differs from baseline")
    package_rows = [compare(p, verify_object=True) for p in packages]
    package_bad = [r for r in package_rows if not r["byteExact"] or r.get("workingTreeReal") is False or r.get("lfsObjectMatches") is False]
    check(not package_bad, "Hangboards bytes, real LFS content or local LFS object integrity failed")
    report["allPackages"] = {"filesCompared": len(packages), "trackedInventoryExact": packages == now_packages,
                             "mismatches": package_bad, "files": package_rows}

    q_old_text, q_now_text = blob(QUEUE).decode(), Path(QUEUE).read_text()
    q_old, q_now = json.loads(q_old_text), json.loads(q_now_text)
    q_old_rows = raw_array_values(raw_object_values(q_old_text)["boards"])
    q_now_rows = raw_array_values(raw_object_values(q_now_text)["boards"])
    old_rows = {json.loads(s)["number"]: s for s in q_old_rows}
    now_rows = {json.loads(s)["number"]: s for s in q_now_rows}
    q_bad = [n for n in set(old_rows) | set(now_rows) if n != 20 and old_rows.get(n) != now_rows.get(n)]
    q_order = [json.loads(s)["number"] for s in q_old_rows] == [json.loads(s)["number"] for s in q_now_rows]
    q_other = {k:v for k,v in q_old.items() if k != "boards"} == {k:v for k,v in q_now.items() if k != "boards"}
    check(not q_bad and q_order and q_other, "Queue content outside row20 changed")
    evo_row = json.loads(now_rows.get(20, "{}"))
    check(evo_row.get("package") == "zlagboard-evo", "Queue row20 identity changed")
    report["queue"] = {"otherRowsByteExact": not q_bad, "changedOtherRowNumbers": q_bad,
                       "rowOrderExact": q_order, "otherTopLevelFieldsExact": q_other}

    l_old_text, l_now_text = blob(LOCK).decode(), Path(LOCK).read_text()
    l_old, l_now = json.loads(l_old_text), json.loads(l_now_text)
    mp_old = raw_object_values(raw_object_values(l_old_text)["migratedPackages"])
    mp_now = raw_object_values(raw_object_values(l_now_text)["migratedPackages"])
    lock_bad = [k for k in set(mp_old) | set(mp_now) if k != "zlagboard-evo" and mp_old.get(k) != mp_now.get(k)]
    check(not lock_bad, "Delivery lock migratedPackages outside zlagboard-evo changed")
    other_lock_changes = sorted(k for k in set(l_old) | set(l_now) if k != "migratedPackages" and l_old.get(k) != l_now.get(k))
    check(not other_lock_changes, "Delivery lock top-level content outside migratedPackages changed")
    report["deliveryLock"] = {"otherMigratedPackagesByteExact": not lock_bad, "changedOtherPackages": lock_bad,
                              "otherTopLevelKeysChanged": other_lock_changes}

    def packet_check(directory, expected_count=None, historic=False):
        directory = Path(directory)
        manifest = directory / "proof-sha256.json"
        if not manifest.is_file():
            return {"present": False, "pass": False, "error": "Missing proof-sha256.json"}
        hashes = json.loads(manifest.read_text())["files"]
        present = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
        declared = set(hashes) | {"proof-sha256.json"}
        bad = []
        for rel, digest in hashes.items():
            target = directory / rel
            if not target.resolve().is_relative_to(directory.resolve()):
                bad.append(rel + ": unsafe relative manifest path")
            elif not target.is_file() or sha(target.read_bytes()) != digest:
                bad.append(rel)
        historical_bad = []
        if historic:
            paths = [p for p in baseline_paths if p.startswith(str(directory) + "/")]
            historical_bad = [p for p in paths if not compare(p)["byteExact"]]
            check(len(paths) == len(hashes) + 1, f"Historical tracked inventory mismatch: {directory}")
        good = not bad and present == declared and not historical_bad and (expected_count is None or len(hashes) == expected_count)
        return {"present": True, "declaredFiles": len(hashes), "manifestSHA256": sha(manifest.read_bytes()),
                "hashMismatches": bad, "baselineByteMismatches": historical_bad,
                "unlistedFiles": sorted(present - declared), "missingFiles": sorted(declared - present), "pass": good}
    report["retainedPackets"] = {}
    for name, count in PACKETS.items():
        row = packet_check(BOARD + name, count, historic=True)
        report["retainedPackets"][name] = row
        check(row["pass"], f"Historical packet retention failed: {name}")
    final_packet = packet_check(args.packet)
    report["finalPacket"] = final_packet
    if args.require_final_packet or final_packet.get("present"):
        check(final_packet["pass"], "Final app packet manifest integrity failed")

    coordination = json.loads(args.coordination.read_text())
    # Final parent scope: experiments did not fix the visible runtime failure.
    # All app and test code must remain exact; only review documents may change.
    shared = set()
    production_frozen = sorted(path for path in baseline_paths
                               if path.startswith(("HangTen/", "HangTenTests/")))
    now_production = sorted(path for path in tracked_paths
                            if path.startswith(("HangTen/", "HangTenTests/")))
    check(production_frozen == now_production,
          "App/test tracked file inventory differs from baseline")
    production_rows = [compare(path) for path in production_frozen]
    check(all(row["byteExact"] for row in production_rows),
          "All app and test files must remain byte-exact to baseline")
    report["frozenProductionFiles"] = production_rows
    permitted_exact = shared | {QUEUE, LOCK, OWNERSHIP}
    changed = command("git", "diff", "--name-only", "-z", args.baseline).decode().split("\0")[:-1]
    out_of_scope = sorted(p for p in set(changed) | set(untracked) if p not in permitted_exact and not p.startswith(BOARD))
    check(not out_of_scope, "Uncoordinated tracked/untracked changes detected")
    report["changeScope"] = {"coordinationPath": str(args.coordination), "allowedSharedFiles": sorted(shared),
                             "scopeAuthority": "Final parent instruction: documentation/proof-only delivery; all app and test files restored to baseline",
                             "changedTrackedFiles": changed, "untrackedFiles": untracked, "outOfScope": out_of_scope}

    cleanup = {"requested": args.live_cleanup, "verified": False}
    if args.live_cleanup:
        check(bool(args.ownership), "Live cleanup requires explicit exact ownership records")
        resources, simulator_ids = [], set()
        allowed_keys = {"derivedData", "resultBundle", "testResultBundle", "exactResultBundle", "deviceSetPath", "temporaryDeviceSet", "preservedProducts"}
        for ownership_path in args.ownership:
            data = json.loads(ownership_path.read_text())
            for key in allowed_keys:
                if key in data and isinstance(data[key], str):
                    resources.append({"ownershipRecord": str(ownership_path), "key": key,
                                      "path": data[key], "exists": Path(data[key]).exists()})
            for key in ["simulator", "udid", "simulatorUDID"]:
                value = data.get(key)
                if isinstance(value, str) and re.fullmatch(r"[0-9A-Fa-f-]{36}", value):
                    simulator_ids.add(value)
                    devices = Path(data.get("deviceSetPath", Path.home() / "Library/Developer/CoreSimulator/Devices"))
                    path = devices / value
                    resources.append({"ownershipRecord": str(ownership_path), "key": "simulatorDeviceDirectory", "path": str(path), "exists": path.exists()})
        ps = command("ps", "-axo", "pid=,ppid=,command=").decode(errors="replace")
        process_rows = [line.strip().split(None, 2) for line in ps.splitlines() if line.strip()]
        parent_by_pid = {int(row[0]): int(row[1]) for row in process_rows}
        own_ancestry = set()
        ancestor = os.getpid()
        while ancestor > 0 and ancestor not in own_ancestry:
            own_ancestry.add(ancestor)
            ancestor = parent_by_pid.get(ancestor, 0)
        tokens = [r["path"] for r in resources] + sorted(simulator_ids)
        matches = [line for line in ps.splitlines() if int(line.strip().split(None, 1)[0]) not in own_ancestry and any(token in line for token in tokens)]
        sim_listed = None
        if args.allow_simulator_list:
            devices = json.loads(command("xcrun", "simctl", "list", "devices", "--json"))["devices"]
            sim_listed = [d for group in devices.values() for d in group if d.get("udid") in simulator_ids]
        clean = bool(args.ownership) and bool(resources) and not any(r["exists"] for r in resources) and not matches and not sim_listed
        cleanup.update(verified=clean, exactResources=resources, matchingLiveProcesses=matches,
                       excludedCurrentProcessAncestry=sorted(own_ancestry),
                       simulatorListCommandRun=args.allow_simulator_list, ownedSimulatorsStillListed=sim_listed)
        check(clean, "Independent live cleanup check failed")
    report["liveCleanup"] = cleanup
    report["failures"] = failures
    report["pass"] = not failures
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(output), "pass": report["pass"], "failures": failures,
                      "liveCleanupVerified": cleanup["verified"]}, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
