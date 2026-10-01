"""Build and replay the experimental coupled contact solver, never the app.

Use run_native_contact_screen.sh so the driver itself also has an owned exit
trap. Child sessions below belong only to this invocation; cleanup never reads
historical process records or targets shared Simulator/device resources.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / "native_contact"


class OwnedCommands:
    def __init__(self, owner, root):
        self.owner, self.root = owner, root
        self.active = {}
        self.registering = False
        self.cleaning = False
        self.pending_signal = None
        self.manifest = root / "resources.jsonl"
        if root.is_symlink() or self.manifest.is_symlink():
            raise ValueError("owned lifecycle output must not be a symlink")

    def record(self, **entry):
        with self.manifest.open("a") as stream:
            stream.write(json.dumps({"owner": self.owner, **entry}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def group_members(group):
        result = subprocess.run(["rtk", "proxy", "ps", "-axo", "pid=,pgid=,stat="],
                                check=True, capture_output=True, text=True)
        return [(int(pid), state) for pid, pgid, state in
                (line.split() for line in result.stdout.splitlines()) if int(pgid) == group]

    def signal_group(self, group, signum):
        try:
            os.killpg(group, signum)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Darwin can return EPERM for a group containing only unreaped
            # zombies. Verify that state explicitly; never suppress a signal
            # failure while a live member remains.
            if any(not state.startswith("Z") for _, state in self.group_members(group)):
                raise

    def release(self, process, label):
        self.cleaning = True
        try:
            self.release_reserved(process, label)
        finally:
            self.cleaning = False

    def release_reserved(self, process, label):
        if process.pid not in self.active:
            return
        # The leader is deliberately still waitable, even on normal exit.
        # Keeping it unreaped reserves its PID and the private group identity
        # until all descendants have been signalled. Never poll()/wait() first.
        if process.returncode is not None:
            raise RuntimeError("Owned leader was reaped before group cleanup")
        self.signal_group(process.pid, signal.SIGTERM)
        time.sleep(.1)
        self.signal_group(process.pid, signal.SIGKILL)
        process.wait(timeout=2)
        deadline = time.monotonic() + 2
        while True:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                self.active.pop(process.pid, None)
                self.record(name=f"{self.owner}-{label}", pid=process.pid,
                            group=process.pid, status="deleted-and-verified")
                return
            except PermissionError:
                if not self.group_members(process.pid):
                    self.active.pop(process.pid, None)
                    self.record(name=f"{self.owner}-{label}", pid=process.pid,
                                group=process.pid, status="deleted-and-verified")
                    return
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Owned child group has surviving members: {process.pid}")
            time.sleep(.01)

    @staticmethod
    def wait_without_reaping(process):
        if hasattr(os, "waitid"):
            os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT)
            return
        # macOS Python omits os.waitid although Darwin provides it. The SDK
        # declares P_PID=1 and WNOWAIT preserves the waitable leader. No
        # siginfo fields are read; this aligned buffer exceeds siginfo_t.
        if sys.platform != "darwin":
            raise RuntimeError("This platform lacks waitid without reaping")
        libc = ctypes.CDLL(None, use_errno=True)
        waitid = libc.waitid
        waitid.argtypes = [ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_int]
        waitid.restype = ctypes.c_int
        info = (ctypes.c_long * 128)()
        while waitid(1, process.pid, ctypes.byref(info), os.WEXITED | os.WNOWAIT):
            error = ctypes.get_errno()
            if error != errno.EINTR:
                raise OSError(error, os.strerror(error))

    def run(self, label, command, log, environment):
        with log.open("w") as output:
            process = None
            self.registering = True
            try:
                process = subprocess.Popen(["rtk", "proxy", *command], cwd=REPO,
                                           env=environment, stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                self.active[process.pid] = (process, label)
                self.record(name=f"{self.owner}-{label}", pid=process.pid,
                            group=process.pid, status="owned", argv=command)
                self.registering = False
                if self.pending_signal is not None:
                    raise SystemExit(128 + self.pending_signal)
                self.wait_without_reaping(process)
            finally:
                self.registering = False
                if process is not None:
                    self.release(process, label)
            if self.pending_signal is not None:
                raise SystemExit(128 + self.pending_signal)
            return process.returncode

    def interrupted(self, signum, _frame):
        # Defer exceptions across Popen/ownership registration. Signals remain
        # unblocked in children and cannot strand a newly created session.
        if self.registering or self.cleaning:
            self.pending_signal = signum
        else:
            raise SystemExit(128 + signum)

    def cleanup(self):
        for process, label in list(self.active.values()):
            self.release(process, label)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fixtures", "replay"])
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--oracle", type=Path)
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--label", default="screen")
    parser.add_argument("--packed", action="store_true",
                        help="capture/validate each frozen row once inside the clock, then scan packed arrays")
    parser.add_argument("--complementarity", action="store_true",
                        help="experimental globalized Fischer-Burmeister solve of the original coupled KKT")
    parser.add_argument("--regions", action="store_true",
                        help="experimental outward-rounded affine region certificates; implies packed source")
    parser.add_argument("--region-checks", action="store_true",
                        help="cross-check every region query against every original packed row inside the cold clock")
    parser.add_argument("--global-schur", action="store_true",
                        help="experimental simultaneous contact solve with exact coupled chain/height responses")
    parser.add_argument("--schur-fb", action="store_true",
                        help="reproduce the rejected condensed Fischer-Burmeister globalization; requires --global-schur")
    parser.add_argument("--blas-product", action="store_true",
                        help="isolated BLAS original-band residual product; default scalar path retained")
    parser.add_argument("--batch-responses", action="store_true",
                        help="isolated bounded multi-RHS global contact responses; requires --global-schur")
    parser.add_argument("--profile-responses", action="store_true",
                        help="split bounded batch response costs; requires --batch-responses")
    parser.add_argument("--primal-parity", action="store_true",
                        help="isolated primal Schur-parity convergence and original-factor recovery")
    parser.add_argument("--profile-primal", action="store_true",
                        help="split existing primal CSC solve costs; default primal backend only")
    parser.add_argument("--end-cluster-order", action="store_true",
                        help="isolated interior-first symbolic ordering; requires --primal-parity")
    args = parser.parse_args()
    if not args.label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.label):
        parser.error("label must use lowercase letters, numbers, hyphen or underscore")
    if not 1 <= args.runs <= 50:
        parser.error("cold replay count must be between 1 and 50")
    if args.mode == "replay" and args.frozen is None:
        parser.error("replay requires --frozen")
    if args.region_checks and not args.regions:
        parser.error("--region-checks requires --regions")
    if args.global_schur and args.complementarity:
        parser.error("select either --global-schur or --complementarity")
    if args.schur_fb and not args.global_schur:
        parser.error("--schur-fb requires --global-schur")
    if args.batch_responses and not args.global_schur:
        parser.error("--batch-responses requires --global-schur")
    if args.profile_responses and not args.batch_responses:
        parser.error("--profile-responses requires --batch-responses")
    if args.primal_parity and (args.global_schur or args.complementarity):
        parser.error("--primal-parity requires the default primal backend")
    if args.profile_primal and (args.global_schur or args.complementarity):
        parser.error("--profile-primal requires the default primal backend")
    if args.end_cluster_order and not args.primal_parity:
        parser.error("--end-cluster-order requires --primal-parity")
    workspace = Path(os.environ.get("PASEO_WORKTREE_PATH", REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or os.environ.get("HANGTEN_CONTACT_SCREEN_OWNER") != owner:
        parser.error("run through the owned shell launcher in this workspace")
    context = REPO / ".context"
    if context.is_symlink():
        parser.error("workspace context must not be a symlink")
    root = context / f"{owner}-native-contact"
    output = root / f"{args.mode}-{args.label}"
    for directory in [root, output]:
        if directory.is_symlink():
            parser.error("owned output directory must not be a symlink")
        directory.mkdir(parents=True, exist_ok=True)
    files = {
        "BandSnapshot.swift": Path("HangTen/Models/RopeBandedSystem.swift"),
        "main.swift": SOURCE / (("RegionFixtures.swift" if args.regions else "Fixtures.swift") if args.mode == "fixtures" else "FrozenReplay.swift"),
    }
    targets = [*files, "compile.log", "run.log", "provenance.json", "replay.json", "validation.json",
               "schur-failure.json", "source-inputs", "module-cache", f"{owner}-native-contact-probe"]
    for target in targets:
        if (output / target).is_symlink():
            parser.error("owned output must not be a symlink")
    if (root / "resources.jsonl").is_symlink() or (root / "pycache").is_symlink():
        parser.error("owned lifecycle output must not be a symlink")
    band = REPO / files["BandSnapshot.swift"]
    # Main's contact solver now calls the authoritative blocking-step helper
    # defined alongside dynamics. Capture that declaration for this pure native
    # tool; compiling the whole app dynamics file would add unrelated services.
    working_set_source = REPO / "HangTen/Models/RopeDynamicsSolver.swift"
    dynamics = working_set_source.read_text()
    beginning = dynamics.index("struct RopeContactWorkingSet {")
    cursor, depth = dynamics.index("{", beginning), 0
    for end in range(cursor, len(dynamics)):
        depth += (dynamics[end] == "{") - (dynamics[end] == "}")
        if depth == 0:
            break
    else:
        raise ValueError("Unterminated authoritative contact working-set declaration")
    working_set = dynamics[beginning:end+1]
    (output / "BandSnapshot.swift").write_text(band.read_text() + "\n" + (SOURCE / "BandSnapshot.swift").read_text() + "\n" + working_set + "\n")
    (output / "main.swift").write_text(files["main.swift"].read_text())
    core = [REPO / "HangTen/Models/RopePhysicsDescriptor.swift", REPO / "HangTen/Models/RopeContactSystem.swift"]
    backend = "GlobalSchurComplementarity.swift" if args.global_schur else ("ContactComplementarity.swift" if args.complementarity else "ContactInteriorPoint.swift")
    native = [SOURCE / name for name in [backend, "SparseNewtonPattern.swift", "FrozenContactStream.swift", "PackedFrozenRows.swift", "AffineRegionCertificate.swift"]]
    sources = [*core, output / "BandSnapshot.swift", *native, output / "main.swift"]
    # Compile exactly the retained bytes rather than mutable repository paths.
    # Later experiments can change the tool without orphaning past provenance.
    captured = output / "source-inputs"
    captured.mkdir(exist_ok=True)
    source_hashes, source_snapshots, compile_sources = {}, {}, []
    validator = SOURCE.parent / "sparse_contact_screen.py"
    for source in [*sources, working_set_source, Path(__file__), Path(__file__).with_suffix(".sh"), validator]:
        snapshot = captured / source.name
        if snapshot.is_symlink():
            parser.error("owned source snapshot must not be a symlink")
        data = source.read_bytes()
        snapshot.write_bytes(data)
        relative = str(source.relative_to(REPO))
        source_hashes[relative] = hashlib.sha256(data).hexdigest()
        source_snapshots[relative] = str(snapshot.relative_to(REPO))
        if source in sources:
            compile_sources.append(snapshot)
    binary = output / f"{owner}-native-contact-probe"
    compile_command = ["xcrun", "swiftc", "-O", "-whole-module-optimization", "-Xcc", "-DACCELERATE_NEW_LAPACK",
                       "-module-cache-path", str(output / "module-cache")]
    if args.global_schur:
        compile_command += ["-D", "SCREEN_GLOBAL_SCHUR"]
    if args.mode == "fixtures":
        developer = Path("/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer")
        frameworks, libraries = developer / "Library/Frameworks", developer / "usr/lib"
        compile_command += ["-F", str(frameworks), "-I", str(libraries), "-L", str(libraries),
                            "-Xlinker", "-rpath", "-Xlinker", str(frameworks),
                            "-Xlinker", "-rpath", "-Xlinker", str(libraries), "-lXCTestSwiftSupport"]
    compile_command += [*[str(p) for p in compile_sources], "-o", str(binary)]
    environment = dict(os.environ, CLANG_MODULE_CACHE_PATH=str(output / "module-cache"),
                       PYTHONPYCACHEPREFIX=str(root / "pycache"),
                       HANGTEN_PACKED_CONTACT_SOURCE="1" if args.packed or args.regions else "0",
                       HANGTEN_BLAS_RESPONSE_PRODUCT="1" if args.blas_product else "0",
                       HANGTEN_BATCH_CONTACT_RESPONSES="1" if args.batch_responses else "0",
                       HANGTEN_PROFILE_CONTACT_RESPONSES="1" if args.profile_responses else "0",
                       HANGTEN_PRIMAL_PARITY="1" if args.primal_parity else "0",
                       HANGTEN_PROFILE_PRIMAL="1" if args.profile_primal else "0",
                       HANGTEN_END_CLUSTER_ORDER="1" if args.end_cluster_order else "0",
                       HANGTEN_AFFINE_REGION_CERTIFICATES="1" if args.regions else "0",
                       HANGTEN_AFFINE_REGION_CROSS_CHECK="1" if args.region_checks else "0",
                       HANGTEN_SCHUR_METHOD="fischer-burmeister" if args.schur_fb else "interior-point",
                       HANGTEN_SCHUR_FAILURE_OUTPUT=str(output / "schur-failure.json"))
    provenance = {"owner": owner, "runtimeAdoption": False, "sourceSHA256": source_hashes,
                  "blasResponseProduct": args.blas_product,
                  "batchedContactResponses": args.batch_responses,
                  "profileContactResponses": args.profile_responses,
                  "primalParity": args.primal_parity,
                  "profilePrimal": args.profile_primal,
                  "endClusterOrder": args.end_cluster_order,
                  "sourceSnapshots": source_snapshots,
                  "compileCommand": compile_command, "mode": args.mode, "packedSource": args.packed or args.regions,
                  "complementarityBackend": args.complementarity, "affineRegionCertificates": args.regions,
                  "globalSchurBackend": args.global_schur,
                  "globalSchurMethod": ("fischer-burmeister" if args.schur_fb else "interior-point") if args.global_schur else None,
                  "fullScanRegionChecks": args.region_checks}
    if args.frozen:
        args.frozen = args.frozen.resolve()
        provenance["frozenSHA256"] = digest(args.frozen)
    if args.oracle:
        args.oracle = args.oracle.resolve()
        provenance["oracleSHA256"] = digest(args.oracle)
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    commands = OwnedCommands(owner, root)
    signal.signal(signal.SIGINT, commands.interrupted)
    signal.signal(signal.SIGTERM, commands.interrupted)
    try:
        status = commands.run("native-contact-compile", compile_command, output / "compile.log", environment)
        if status:
            print((output / "compile.log").read_text(), file=sys.stderr)
            return status
        invocation = [str(binary)]
        if args.mode == "replay":
            invocation += [str(args.frozen), str(output / "replay.json"), str(args.runs)]
        status = commands.run("native-contact-probe", invocation, output / "run.log", environment)
        if status:
            print((output / "run.log").read_text(), file=sys.stderr)
            return status
        if args.mode == "fixtures":
            print((output / "run.log").read_text())
            return 0
        import numpy as np
        spec = importlib.util.spec_from_file_location("captured_sparse_contact_screen", captured / validator.name)
        validation_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = validation_module
        spec.loader.exec_module(validation_module)
        load_frozen, residuals = validation_module.load_frozen, validation_module.residuals
        raw = json.loads((output / "replay.json").read_text())
        p = load_frozen(args.frozen)
        answer = raw["last"]
        if raw["failure"] is not None or len(raw["solutions"]) != len(raw["times"]) or not raw["solutions"]:
            raise ValueError("nonfinite or rejected replay")
        limits = {"stationarity": 1e-10, "regularizedEquality": 1e-10, "regularizedContact": 1e-10,
                  "regularizedComplementarity": 1e-14, "dualViolation": 1e-12,
                  "slackViolation": 0, "allRowFeasibility": 1e-8}
        numerical, measured = True, {}
        difference = None
        expected = np.asarray(json.loads(args.oracle.read_text())) if args.oracle else None
        for cold in raw["solutions"]:
            x, lam = np.asarray(cold["x"]), np.asarray(cold["lambda"])
            mu, seen = np.zeros(len(p.cc)), set()
            for raw_id, force in cold["forceEntries"]:
                index = int(raw_id)
                if index != raw_id or not 0 <= index < len(mu) or index in seen:
                    raise ValueError("invalid sparse source force evidence")
                seen.add(index)
                mu[index] = force
            if not all(np.all(np.isfinite(v)) for v in [x, lam, mu]):
                raise ValueError("nonfinite replay solution")
            slack = np.maximum(0, p.a @ x + p.cc + p.epsilon * mu)
            current = residuals(p, x, lam, mu, slack)
            numerical = numerical and all(current[key] <= limit for key, limit in limits.items())
            for key, value in current.items():
                measured[key] = max(measured.get(key, value), value)
            if expected is not None:
                if expected.shape != x.shape or not np.all(np.isfinite(expected)):
                    raise ValueError("invalid oracle dimensions or values")
                error = float(np.max(abs(x - expected)))
                difference = max(difference or 0, error)
                numerical = numerical and error <= 1e-6
        times = raw["times"]
        p95 = float(np.quantile(times, .95, method="higher")) if len(times) == 50 else None
        result = {"owner": owner, "runtimeAdoption": False, "coldRuns": len(times), "numericalAccepted": bool(numerical),
                  "independentlyCertifiedRuns": len(raw["solutions"]),
                  "packedSource": args.packed or args.regions,
                  "complementarityBackend": args.complementarity,
                  "globalSchurBackend": args.global_schur,
                  "globalSchurMethod": ("fischer-burmeister" if args.schur_fb else "interior-point") if args.global_schur else None,
                  "affineRegionCertificates": args.regions,
                  "fullScanRegionChecks": args.region_checks,
                  "regionRuns": raw["regionRuns"],
                  "solverRuns": raw["solverRuns"],
                  "residuals": measured, "primalDifference": difference, "p95Seconds": p95,
                  "singleRunSeconds": times[0] if len(times) == 1 else None,
                  "coldQPPerformanceAccepted": numerical and p95 is not None and p95 <= .002,
                  "trace": answer["trace"], "scope": raw["scope"]}
        (output / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        displayed = {**result, "regionRuns": result["regionRuns"][:1], "solverRuns": result["solverRuns"][:1]}
        displayed["profileRunsRetained"] = len(times)
        print(json.dumps(displayed, indent=2))
        # A numerical pass with a failed/unverified runtime gate is explicitly
        # nonzero, so this cannot accidentally become a green product gate.
        return 0 if result["coldQPPerformanceAccepted"] else (3 if numerical else 1)
    finally:
        commands.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
