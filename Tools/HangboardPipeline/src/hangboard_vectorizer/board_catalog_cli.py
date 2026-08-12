"""Command-line entry point for hangboard catalog tooling."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .board_catalog import (
    CatalogEntry,
    CatalogDocument,
    validate_catalog,
)


class _CliError(ValueError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        if arguments.command == "validate":
            catalog = validate_catalog(arguments.catalog)
            print(_status_payload(catalog=catalog, catalog_path=arguments.catalog))
            return 0
        if arguments.command == "status":
            catalog = validate_catalog(arguments.catalog)
            print(_status_payload(catalog=catalog, catalog_path=arguments.catalog))
            return 0
        raise _CliError("unknown command")
    except SystemExit as error:
        return int(error.code or 0)
    except _CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
        print(f"error: {message}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hangboard-catalog")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="validate a catalog and board packages")
    validate.add_argument("--catalog", type=Path, required=True)

    status = subcommands.add_parser("status", help="print catalog metadata and statuses")
    status.add_argument("--catalog", type=Path, required=True)

    return parser


def _status_payload(catalog: CatalogDocument, catalog_path: Path) -> str:
    catalog_root = catalog_path.parent
    payload = {
        "boards": [_board_status(entry, catalog_root / entry.path) for entry in catalog.entries],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _board_status(entry: CatalogEntry, _package_root: Path) -> dict[str, object]:
    return {
        "id": entry.id,
        "path": entry.path,
        "status": entry.status,
    }


if __name__ == "__main__":
    raise SystemExit(main())
