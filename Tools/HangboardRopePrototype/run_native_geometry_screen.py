"""Experimental GPU candidate compaction with current CPU triangle authority.

This fixed healthy corpus screen never builds or modifies the app. Use its
owned shell launcher; numerical equality alone cannot give an exit-zero replay.
"""
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


def collider_snapshot(original: str, extension: str) -> str:
    # Preserve the current production sign, fallback, exact narrowphase and
    # coplanar manifold code verbatim. Replace only candidate gathering.
    start = original.index("    func segmentContacts(")
    end = original.index("    /// Conservative advancement", start)
    method = original[start:end]
    signature = "radius:Double)->[RopeSegmentContact]"
    if method.count(signature) != 1:
        raise ValueError("production contact signature changed; review snapshot adapter")
    method = method.replace(signature, "radius:Double,faces:[Int])->[RopeSegmentContact]", 1)
    first = method.index("        let low=simd_min")
    last = method.index("        for index in faces.sorted()", first)
    method = (method[:first] + "        let squareRadius=radius*radius\n"
              "        var result:[RopeSegmentContact]=[]\n" + method[last:])
    method = method.replace("func segmentContacts(", "func screenSegmentContacts(", 1)
    return original + "\n" + extension + "\nextension RopeTriangleCollider {\n" + method + "}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fixtures", "replay"])
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--label", default="screen")
    args = parser.parse_args()
    if not args.label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.label):
        parser.error("label must use lowercase letters, numbers, hyphen or underscore")
    if args.mode == "replay" and args.corpus is None:
        parser.error("replay requires --corpus pointing to the fixed healthy input")
    workspace = Path(os.environ.get("PASEO_WORKTREE_PATH", REPO)).resolve()
    owner = workspace.name
    if workspace != REPO or os.environ.get("HANGTEN_GEOMETRY_SCREEN_OWNER") != owner:
        parser.error("run through the owned shell launcher in this workspace")
    context = REPO / ".context"
    root = context / f"{owner}-native-geometry"
    output = root / f"{args.mode}-{args.label}"
    for directory in [context, root, output]:
        if directory.is_symlink():
            parser.error("owned output directory must not be a symlink")
        directory.mkdir(exist_ok=True)
    for path in [root / "resources.jsonl", root / "pycache", *[output / n for n in
                 ["ColliderSnapshot.swift", "main.swift", "compile.log", "run.log", "provenance.json",
                  "report.json", "module-cache", f"{owner}-native-geometry-probe"]]]:
        if path.is_symlink():
            parser.error("owned output must not be a symlink")
    if args.corpus:
        args.corpus = args.corpus.resolve()
        if hashlib.sha256(args.corpus.read_bytes()).hexdigest() != CORPUS_SHA256:
            parser.error("corpus differs from the frozen complete healthy geometry input")
    original = REPO / "HangTen/Models/RopeTriangleCollider.swift"
    extension = SOURCE / "ColliderExtension.swift"
    snapshot = output / "ColliderSnapshot.swift"
    snapshot.write_text(collider_snapshot(original.read_text(), extension.read_text()))
    main_source = SOURCE / ("Fixtures.swift" if args.mode == "fixtures" else "Replay.swift")
    main = output / "main.swift"
    main.write_text(main_source.read_text())
    sources = [REPO / "HangTen/Models/RopePhysicsDescriptor.swift", snapshot, SOURCE / "BVHStream.swift", main]
    binary = output / f"{owner}-native-geometry-probe"
    argv = ["xcrun", "swiftc", "-O", "-whole-module-optimization", "-module-cache-path",
            str(output / "module-cache"), *map(str, sources), "-o", str(binary)]
    bound_sources = [*sources, original, extension, main_source, Path(__file__),
                     Path(__file__).with_name("run_native_contact_screen.py")]
    provenance = {"owner": owner, "runtimeAdoption": False, "compileCommand": argv,
                  "sourceSHA256": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in bound_sources}}
    if args.corpus:
        provenance["inputSHA256"] = CORPUS_SHA256
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    env = dict(os.environ, CLANG_MODULE_CACHE_PATH=str(output / "module-cache"))
    commands = OwnedCommands(owner, root)
    signal.signal(signal.SIGINT, commands.interrupted)
    signal.signal(signal.SIGTERM, commands.interrupted)
    try:
        status = commands.run("native-geometry-compile", argv, output / "compile.log", env)
        if status:
            print((output / "compile.log").read_text(), file=sys.stderr)
            return status
        invocation = [str(binary)]
        if args.mode == "replay":
            invocation += [str(args.corpus), str(output / "report.json")]
        status = commands.run("native-geometry-probe", invocation, output / "run.log", env)
        print((output / "run.log").read_text())
        return status
    finally:
        commands.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
