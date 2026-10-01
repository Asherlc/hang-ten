"""Bounded pre-generation affine geometry screen; no application adoption."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
from run_native_contact_screen import OwnedCommands

REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / "native_geometry"
CORPUS_SHA256 = "1e5b25f15d18d6af215fa7942dad13addd644267741336856f8838409eee1f14"
FROZEN_SHA256 = "c43720bccda76df9df92c9a155f3d4a5a11195011a9eca17b7ba42b1e27d1f97"
SOLUTION_SHA256 = "7fccac859b66a02def86765143f959407955977e2d0d82c77487ddf1893dc3b0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fixtures", "replay", "render", "tube-fixtures"])
    parser.add_argument("--label", required=True)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--solution", type=Path)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--regions", action="store_true")
    parser.add_argument("--fast-boxes", action="store_true")
    parser.add_argument("--slabs", action="store_true")
    parser.add_argument("--batch", action="store_true")
    args = parser.parse_args()
    if not args.label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.label):
        parser.error("label must use lowercase letters, numbers, hyphen or underscore")
    if args.runs not in (1, 50):
        parser.error("fixed construction checkpoint is one run; final timing screen is 50")
    if args.fast_boxes and not args.regions:
        parser.error("fast boxes requires the region traversal")
    if args.slabs and (not args.fast_boxes or args.mode not in ("fixtures", "replay")):
        parser.error("slabs requires region fast boxes and geometry fixtures/replay")
    if args.batch and not args.slabs:
        parser.error("batch requires the retained-collider slab index")
    workspace = Path(os.environ.get("PASEO_WORKTREE_PATH", REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or os.environ.get("HANGTEN_AFFINE_GEOMETRY_OWNER") != owner:
        parser.error("run through the owned shell launcher in this workspace")
    inputs = []
    if args.mode in ("replay", "render"):
        if not all([args.corpus, args.frozen, args.solution]):
            parser.error("replay requires the fixed corpus, frozen production QP and certified solution")
        for path, expected in [(args.corpus,CORPUS_SHA256),(args.frozen,FROZEN_SHA256),(args.solution,SOLUTION_SHA256)]:
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                parser.error("input differs from retained fixed checkpoint")
        inputs = [args.corpus.resolve(), args.frozen.resolve(), args.solution.resolve()]
    root = REPO / ".context" / f"{owner}-affine-geometry"
    output = root / f"{args.mode}-{args.label}"
    for directory in [REPO / ".context",root,output,output / "source-inputs"]:
        if directory.is_symlink():
            parser.error("owned output directory must not be a symlink")
        directory.mkdir(exist_ok=True)
    snapshot = output / "source-inputs"
    original = REPO / "HangTen/Models/RopeTriangleCollider.swift"
    extension = SOURCE / "AffineGeometry.swift"
    main_source = SOURCE / {"fixtures":"AffineFixtures.swift","replay":"AffineReplay.swift","render":"RenderReplay.swift","tube-fixtures":"TubeFixtures.swift"}[args.mode]
    sources = [REPO / "HangTen/Models/RopePhysicsDescriptor.swift",original,extension,main_source,
               Path(__file__),Path(__file__).with_suffix(".sh"),
               Path(__file__).with_name("run_native_contact_screen.py")]
    if args.mode == "render":
        sources += [REPO / "HangTen/Models/LiveRopeMesh.swift",
                    SOURCE / "RenderReference.swift"]
    if args.mode == "tube-fixtures":
        sources += [REPO / "HangTen/Models/LiveRopeMesh.swift",REPO / "HangTenTests/LiveRopeMeshTests.swift"]
    captured = {}
    for source in sources:
        target = snapshot / source.name
        if target.is_symlink():
            parser.error("source snapshot must not be a symlink")
        target.write_bytes(source.read_bytes())
        captured[str(source.relative_to(REPO))] = str(target.relative_to(REPO))
    combined = output / "ColliderSnapshot.swift"
    main = output / "main.swift"
    binary = output / f"{owner}-affine-geometry-probe"
    for path in [combined,main,binary,output / "module-cache",output / "compile.log",output / "run.log",output / "report.json",output / "provenance.json",root / "resources.jsonl"]:
        if path.is_symlink():
            parser.error("owned output must not be a symlink")
    combined.write_text((snapshot / original.name).read_text()+"\n"+(snapshot / extension.name).read_text())
    main.write_bytes((snapshot / main_source.name).read_bytes())
    argv = ["xcrun","swiftc","-O","-whole-module-optimization","-module-cache-path",str(output / "module-cache"),
            str(snapshot / "RopePhysicsDescriptor.swift"),str(combined),str(main),"-o",str(binary)]
    if args.mode == "render":
        argv[argv.index("-o"):argv.index("-o")] = [str(snapshot / "LiveRopeMesh.swift"),str(snapshot / "RenderReference.swift")]
    if args.mode == "tube-fixtures":
        argv[argv.index("-o"):argv.index("-o")] = [str(snapshot / "LiveRopeMesh.swift"),str(snapshot / "LiveRopeMeshTests.swift")]
        developer = Path("/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer")
        frameworks,libraries = developer / "Library/Frameworks",developer / "usr/lib"
        argv[2:2] = ["-F",str(frameworks),"-I",str(libraries),"-L",str(libraries),
                      "-Xlinker","-rpath","-Xlinker",str(frameworks),
                      "-Xlinker","-rpath","-Xlinker",str(libraries),"-lXCTestSwiftSupport"]
    provenance = {"owner":owner,"runtimeAdoption":False,"thresholdRegions":args.regions,"fastRegionBoxes":args.fast_boxes,"orientedSlabs":args.slabs,"dualTreeBatch":args.batch,"compileCommand":argv,"sourceSnapshots":captured,
        "sourceSHA256":{str(s.relative_to(REPO)):hashlib.sha256((REPO / captured[str(s.relative_to(REPO))]).read_bytes()).hexdigest() for s in sources},
        "inputSHA256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    (output / "provenance.json").write_text(json.dumps(provenance,indent=2,sort_keys=True)+"\n")
    commands = OwnedCommands(owner,root)
    env = dict(os.environ,HANGTEN_AFFINE_GEOMETRY_METHOD="regions" if args.regions else "nearest",
               HANGTEN_AFFINE_FAST_BOXES="1" if args.fast_boxes else "0",
               HANGTEN_AFFINE_SLABS="1" if args.slabs else "0",
               HANGTEN_AFFINE_BATCH="1" if args.batch else "0")
    signal.signal(signal.SIGINT,commands.interrupted)
    signal.signal(signal.SIGTERM,commands.interrupted)
    try:
        status = commands.run("affine-geometry-compile",argv,output / "compile.log",env)
        if status:
            print((output / "compile.log").read_text(),file=sys.stderr)
            return status
        invocation = [str(binary)]
        if args.mode in ("replay", "render"):
            invocation += [*map(str,inputs),str(output / "report.json"),str(args.runs)]
        status = commands.run("affine-geometry-probe",invocation,output / "run.log",env)
        print((output / "run.log").read_text())
        return status
    finally:
        commands.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
