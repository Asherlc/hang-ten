"""Edit a native board's authored suspension and rope-physics configuration.

Dump current metadata with ``board_manifest.py --package <slug>
--dump-authoring suspension`` (or ``rope-physics``), edit that JSON, then use
``set_cad_authoring.py --package <slug> --suspension <file.json>`` or
``--rope-physics <file.json>``. Remove a configuration with
``--remove-suspension`` or ``--remove-rope-physics``. The untargeted property
is preserved. The archive rewrite changes only document metadata, retaining
all geometry members byte for byte.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import use_hangboard_packages  # noqa: F401
from hangboard_packages import cad_source

import board_manifest


def read_input(path: Path) -> dict:
    value = cad_source.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise cad_source.ManifestError("authoring input must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--package", help="Hangboards/<slug>.FCStd")
    target.add_argument("--source", type=Path, help="an explicit native FCStd path")
    suspension = parser.add_mutually_exclusive_group()
    suspension.add_argument("--suspension", type=Path, help="authored suspension JSON")
    suspension.add_argument("--remove-suspension", action="store_true")
    physics = parser.add_mutually_exclusive_group()
    physics.add_argument("--rope-physics", type=Path, help="authored rope-physics JSON")
    physics.add_argument("--remove-rope-physics", action="store_true")
    arguments = parser.parse_args(argv)
    if not any((arguments.suspension, arguments.remove_suspension,
                arguments.rope_physics, arguments.remove_rope_physics)):
        parser.error("specify a metadata input or removal")
    if arguments.package is not None and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", arguments.package):
        parser.error(f"invalid package name: {arguments.package!r}")
    source = (
        board_manifest.package_source(board_manifest.REPOSITORY, arguments.package)
        if arguments.package is not None else arguments.source
    )
    if arguments.suspension is not None:
        authored_suspension = read_input(arguments.suspension)
    elif arguments.remove_suspension:
        authored_suspension = None
    else:
        authored_suspension = cad_source.load_suspension_authoring(source)
    if arguments.rope_physics is not None:
        authored_physics = read_input(arguments.rope_physics)
    elif arguments.remove_rope_physics:
        authored_physics = None
    else:
        authored_physics = cad_source.load_rope_physics_authoring(source)
    changed = cad_source.embed_authoring(
        source, suspension=authored_suspension, rope_physics=authored_physics,
    )
    print(f"{source}: authoring {'updated' if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (cad_source.ManifestError, ValueError, OSError) as error:
        print(f"AUTHORING ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
