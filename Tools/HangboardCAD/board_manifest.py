"""Generate a CAD-backed board's ``board.json`` from its FreeCAD source.

For a package with a native source (``Hangboards/<slug>/<slug>.FCStd``) the
FCStd is the single source of truth for the board's logical metadata as well as
its geometry. The metadata lives in two document-level string properties:

* ``HangTenBoardID`` -- the board ``id`` (also bound by the compiler);
* ``HangTenBoardManifest`` -- compact JSON of ``board.json`` *minus* ``id``, in
  the key order ``board.json`` is emitted in.

``board.json`` is generated at build time and is **not committed**: the package
validator, ``scripts/stage-board-packages.py`` (iOS and Android), and the
verifiers generate it in memory from the FCStd, and an on-disk ``board.json``
inside a CAD-backed package is rejected as a stale hand edit (``.gitignore``
also lists the current CAD packages' paths). Change the metadata with
``set_board_manifest.py``.

Everything that is derivable from the CAD or the build is left out of the
manifest. Only ``id`` qualifies. ``aspectRatio`` is a stored presentation fact:
five of the seven audited CAD boards match the descriptor ``modelBounds`` x/y
ratio to within 2e-8 relative, ``metolius-wood-grips-compact-ii`` keeps its
pre-migration raster value (0.14% off its face ratio), and
``metolius-rock-rings-3d`` presents two ring instances while its bounds cover
one ring
(``docs/source-audits/2026-09-24-cad-aspect-ratio-audit.md``). Published grip
depths are sourced product facts that ``compile_board.py`` validates the
geometry against. Both stay in the manifest.

The generation code is ``hangboard_packages.cad_source`` (pure host Python,
stdlib only, shared with the package validator); import it from there. This
module adds package lookup, the command line, and the ``git diff`` textconv
rendering. It never imports
FreeCAD, so it runs anywhere, including CI on Linux.

    python3 Tools/HangboardCAD/board_manifest.py --package <slug>          # board.json to stdout
    python3 Tools/HangboardCAD/board_manifest.py --package <slug> --output <path>
    python3 Tools/HangboardCAD/board_manifest.py --all                     # generate every CAD board
    python3 Tools/HangboardCAD/board_manifest.py --all --output-dir <dir>  # <dir>/<slug>/board.json
    python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug>   # manifest
    python3 Tools/HangboardCAD/board_manifest.py --dump-file <path.FCStd>  # textconv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Puts Tools/HangboardPackages/src on sys.path (host python3 and freecadcmd).
import use_hangboard_packages  # noqa: F401
from hangboard_packages import cad_source

REPOSITORY = Path(__file__).resolve().parents[2]


# --- packages ---------------------------------------------------------------


def package_source(root: Path, package: str) -> Path:
    """Return the path to the FCStd authoring source for ``package``."""
    return root / "Hangboards" / package / f"{package}.FCStd"


def source_backed_packages(root: Path) -> list[str]:
    """Return the sorted slugs of packages that carry an FCStd authoring source."""
    return sorted(
        path.parent.name
        for path in (root / "Hangboards").glob("*/*.FCStd")
        if path.stem == path.parent.name
    )


def write_board_json(source: Path, target: Path) -> bool:
    """Write the generated ``board.json`` to ``target``; True when it changed.

    ``target`` must not be the package's own ``board.json``: that file is never
    kept on disk for a CAD-backed package.
    """
    source, target = Path(source), Path(target)
    if target.resolve() == (source.parent / "board.json").resolve():
        raise cad_source.ManifestError(
            f"refusing to write {target}: a CAD-backed package's board.json is generated "
            "at build time and must not exist in the package"
        )
    expected = cad_source.generate_board_json(source)
    if target.is_file() and target.read_bytes() == expected:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(f".{target.name}.staged")
    staged.write_bytes(expected)
    os.replace(staged, target)
    return True


# --- textconv ---------------------------------------------------------------


def _resolve_lfs_pointer(path: Path) -> Path | None:
    """Map an LFS pointer (as git hands a blob to textconv) to its local object."""
    fields = dict(
        line.split(" ", 1)
        for line in path.read_text(errors="replace").splitlines()
        if " " in line
    )
    oid = fields.get("oid", "")
    if not oid.startswith("sha256:"):
        return None
    digest = oid.split(":", 1)[1]
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    candidate = Path(common) / "lfs" / "objects" / digest[:2] / digest[2:4] / digest
    return candidate if candidate.is_file() else None


def describe_source(path: Path) -> str:
    """A stable text rendering of an FCStd for ``git diff`` (textconv).

    HangTen document properties, the pretty-printed board manifest, and one
    ``sha256 size name`` line per archive member, so metadata edits read as JSON
    diffs and geometry edits show up as changed member digests.
    """
    path = Path(path)
    lines: list[str] = []
    if cad_source._is_lfs_pointer(path):
        resolved = _resolve_lfs_pointer(path)
        if resolved is None:
            return "Git LFS pointer (object not available locally):\n" + path.read_text(
                errors="replace"
            )
        path = resolved
    try:
        with zipfile.ZipFile(path) as archive:
            members = [
                (info.filename, archive.read(info.filename)) for info in archive.infolist()
            ]
    except zipfile.BadZipFile as error:
        return f"not an FCStd archive: {error}\n"
    document = dict(members).get("Document.xml", b"")
    try:
        properties = cad_source.document_properties_from_xml(document)
    except (cad_source.ManifestError, ET.ParseError) as error:
        properties = {}
        lines.append(f"# unreadable Document.xml: {error}")
    lines.append("# HangTen document properties")
    for name in sorted(properties):
        if name.startswith("HangTen") and name != cad_source.MANIFEST_PROPERTY:
            lines.append(f"{name} = {properties[name][1]}")
    lines.append("")
    lines.append(f"# {cad_source.MANIFEST_PROPERTY}")
    kind, text = properties.get(cad_source.MANIFEST_PROPERTY, ("", None))
    if text is None:
        lines.append("(absent)")
    else:
        try:
            lines.append(cad_source._encode(cad_source.loads(text), 2))
        except json.JSONDecodeError:
            lines.append(f"(invalid JSON) {text}")
    lines.append("")
    lines.append("# archive members (sha256 size name)")
    for name, data in members:
        lines.append(f"{hashlib.sha256(data).hexdigest()} {len(data):>10} {name}")
    return "\n".join(lines) + "\n"


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: generate board.json from FCStd sources or render textconv."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--package", action="append", default=[], help="Hangboards/<slug>")
    parser.add_argument("--all", action="store_true", help="every source-backed package")
    parser.add_argument("--output", type=Path, help="write one package's board.json here")
    parser.add_argument(
        "--output-dir", type=Path, help="write <dir>/<slug>/board.json for each package"
    )
    parser.add_argument("--dump", action="store_true", help="print the manifest JSON")
    parser.add_argument("--dump-file", type=Path, help="textconv rendering of an FCStd path")
    parser.add_argument("--root", type=Path, default=REPOSITORY, help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()

    if arguments.dump_file is not None:
        sys.stdout.write(describe_source(arguments.dump_file))
        return 0

    if not arguments.package and not arguments.all:
        parser.error("name --package <slug> or --all")
    packages = list(arguments.package)
    if arguments.all:
        packages = source_backed_packages(root)
    for package in packages:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", package):
            parser.error(f"invalid package name: {package!r}")
    if arguments.output is not None and (
        len(packages) != 1 or arguments.all or arguments.output_dir is not None
    ):
        parser.error("--output takes exactly one --package and no --output-dir")

    if arguments.dump:
        for package in packages:
            board = cad_source.load_board(package_source(root, package))
            print(cad_source._encode(cad_source.board_to_manifest(board), 2))
        return 0

    if arguments.output is not None:
        write_board_json(package_source(root, packages[0]), arguments.output)
        return 0
    if arguments.output_dir is not None:
        for package in packages:
            write_board_json(
                package_source(root, package), arguments.output_dir / package / "board.json"
            )
        print(f"generated board.json for {len(packages)} CAD-backed package(s)")
        return 0
    if len(arguments.package) == 1 and not arguments.all:
        sys.stdout.flush()
        sys.stdout.buffer.write(cad_source.generate_board_json(package_source(root, packages[0])))
        sys.stdout.buffer.flush()
        return 0
    for package in packages:
        rendered = cad_source.generate_board_json(package_source(root, package))
        print(f"{package}: sha256 {hashlib.sha256(rendered).hexdigest()} ({len(rendered)} bytes)")
    print(f"generated board.json for {len(packages)} CAD-backed package(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except cad_source.ManifestError as error:
        print(f"MANIFEST ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
