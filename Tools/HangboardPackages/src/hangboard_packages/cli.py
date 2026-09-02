"""Command-line entry point for hangboard package discovery."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from .board_catalog import BoardInventory, BoardPackage, discover_board_packages
from .cord_render_assets import (
    _PathRole,
    _load_json,
    _snapshot_image,
    build_lossless_atlases_with_report,
    freeze_source_manifest,
    inspect_transparency_with_report,
    load_chroma_config,
    load_locked_sources,
    preflight_path_roles,
    remove_chroma_with_report,
    source_lock_artifact,
    verify_atlas_round_trip,
)
from .metadata_audit import load_metadata_ledger, validate_metadata_ledger
from .presentation_remediation_audit import (
    PresentationValidationMode,
    load_presentation_remediation_manifest,
    validate_presentation_remediation_manifest,
)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        if arguments.command == "cord-assets":
            return _cord_assets(arguments)
        inventory = discover_board_packages(
            arguments.root,
            require_complete_inventory=(
                arguments.command in {"audit-metadata", "audit-presentations"}
                or arguments.final_inventory
            ),
        )
        if arguments.command == "audit-metadata":
            report = validate_metadata_ledger(
                load_metadata_ledger(arguments.ledger), inventory
            )
            print(json.dumps(report.to_json(), indent=2, sort_keys=True))
            return 0
        if arguments.command == "audit-presentations":
            validation_mode = PresentationValidationMode.SOURCE_RECLASSIFICATION
            if arguments.phase2_preflight:
                validation_mode = PresentationValidationMode.PHASE2_PREFLIGHT
            elif arguments.phase2_partial:
                validation_mode = PresentationValidationMode.PHASE2_PARTIAL
            elif arguments.phase2_final:
                validation_mode = PresentationValidationMode.PHASE2_FINAL
            source_files = _transient_file_mapping(arguments.source_file, "source-file")
            candidate_files = _transient_file_mapping(
                arguments.candidate_file, "candidate-file"
            )
            if (
                arguments.batch_id is not None
                and validation_mode != PresentationValidationMode.PHASE2_PARTIAL
            ):
                raise ValueError("--batch-id is legal only with --phase2-partial")
            if validation_mode == PresentationValidationMode.PHASE2_FINAL and (
                source_files or candidate_files
            ):
                raise ValueError("final Phase 2 validation rejects transient files")
            if (
                validation_mode == PresentationValidationMode.SOURCE_RECLASSIFICATION
                and (source_files or candidate_files or arguments.batch_id)
            ):
                raise ValueError(
                    "Phase 1 validation rejects Phase 2 lifecycle arguments"
                )
            report = validate_presentation_remediation_manifest(
                load_presentation_remediation_manifest(arguments.manifest),
                inventory,
                hangboards_root=arguments.root,
                selected_package_ids=frozenset(arguments.package_id),
                final_validation=arguments.final_validation,
                validation_mode=validation_mode,
                selected_batch_id=arguments.batch_id,
                transient_source_files=source_files,
                transient_candidate_files=candidate_files,
            )
            print(json.dumps(report.to_json(), indent=2, sort_keys=True))
            return 0
        print(_status_payload(inventory))
        return 0
    except SystemExit as error:
        return int(error.code or 0)
    except (OSError, ValueError) as error:
        message = str(error).splitlines()[0] if str(error) else error.__class__.__name__
        print(f"error: {message}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hangboard-packages")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("validate", "validate discovered board packages"),
        ("status", "print discovered package metadata"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument(
            "--final-inventory",
            action="store_true",
            help="reject primary-only draft directories",
        )
    audit_metadata = subcommands.add_parser(
        "audit-metadata", help="validate a source-audited metadata ledger"
    )
    audit_metadata.add_argument("--root", type=Path, required=True)
    audit_metadata.add_argument("--ledger", type=Path, required=True)
    audit_presentations = subcommands.add_parser(
        "audit-presentations", help="validate a presentation remediation manifest"
    )
    audit_presentations.add_argument("--root", type=Path, required=True)
    audit_presentations.add_argument("--manifest", type=Path, required=True)
    audit_presentations.add_argument(
        "--package-id", action="append", default=[], help="validate one package lane"
    )
    lifecycle = audit_presentations.add_mutually_exclusive_group()
    lifecycle.add_argument(
        "--final-validation",
        action="store_true",
        help="require full-catalog coverage and all Phase 1 root checks passed",
    )
    lifecycle.add_argument(
        "--phase2-preflight",
        action="store_true",
        help="validate disposable exact-canvas capability preflight state",
    )
    lifecycle.add_argument(
        "--phase2-partial",
        action="store_true",
        help="validate an intermediate Phase 2 production state",
    )
    lifecycle.add_argument(
        "--phase2-final",
        action="store_true",
        help="validate the final accepted Phase 2 catalog",
    )
    audit_presentations.add_argument("--batch-id")
    audit_presentations.add_argument(
        "--source-file",
        action="append",
        nargs=2,
        metavar=("SHA256", "PATH"),
        default=[],
    )
    audit_presentations.add_argument(
        "--candidate-file",
        action="append",
        nargs=2,
        metavar=("SHA256", "PATH"),
        default=[],
    )
    cord_assets = subcommands.add_parser(
        "cord-assets", help="lock evidence and gate cord-render transparency"
    )
    cord_commands = cord_assets.add_subparsers(dest="cord_command", required=True)
    lock = cord_commands.add_parser("lock", help="freeze immutable source metadata")
    lock.add_argument("--manifest", type=Path, required=True)
    lock.add_argument("--report", type=Path)
    atlas = cord_commands.add_parser(
        "atlas", help="build and verify lossless source atlases"
    )
    atlas.add_argument("--manifest", type=Path, required=True)
    atlas.add_argument("--output-root", type=Path, required=True)
    atlas.add_argument("--report", type=Path)
    atlas.add_argument("--max-pages", type=int, default=5)
    key = cord_commands.add_parser(
        "key", help="remove the recorded chroma key to alpha"
    )
    key.add_argument("--input", type=Path, required=True)
    key.add_argument("--output", type=Path, required=True)
    key.add_argument("--config", type=Path, required=True)
    key.add_argument("--report", type=Path, required=True)
    inspect = cord_commands.add_parser(
        "inspect", help="enforce the focused RGBA transparency contract"
    )
    inspect.add_argument("--image", type=Path, required=True)
    inspect.add_argument("--expected-from", required=True)
    inspect.add_argument("--config", type=Path, required=True)
    inspect.add_argument("--report", type=Path, required=True)
    return parser


def _cord_assets(arguments: argparse.Namespace) -> int:
    if arguments.cord_command == "lock":
        sources = freeze_source_manifest(
            arguments.manifest, report_path=arguments.report
        )
        payload = source_lock_artifact(sources)
    elif arguments.cord_command == "atlas":
        roles = [
            _PathRole("manifest", arguments.manifest, "input"),
            _PathRole("output root", arguments.output_root, "directory"),
        ]
        if arguments.report is not None:
            roles.append(_PathRole("report", arguments.report, "output"))
        preflight_path_roles(roles)
        sources = load_locked_sources(arguments.manifest)
        index = build_lossless_atlases_with_report(
            sources,
            arguments.output_root,
            max_pages=arguments.max_pages,
            report_path=arguments.report,
        )
        verification = verify_atlas_round_trip(index)
        payload = {
            "index": index.to_json(),
            "verification": {
                "valid": verification.valid,
                "verified_panels": verification.verified_panels,
            },
        }
    elif arguments.cord_command == "key":
        config = load_chroma_config(arguments.config)
        report = remove_chroma_with_report(
            arguments.input,
            arguments.output,
            config,
            arguments.report,
            config_path=arguments.config,
        )
        payload = report.to_json()
    else:
        (
            expected_width,
            expected_height,
            board_path,
            expected_asset,
        ) = _presentation_dimensions_and_paths(arguments.expected_from)
        preflight_path_roles(
            [
                _PathRole("image", arguments.image, "input"),
                _PathRole("expected board", board_path, "input"),
                _PathRole("expected asset", expected_asset, "input"),
                _PathRole("config", arguments.config, "input"),
                _PathRole("report", arguments.report, "output"),
            ]
        )
        config = load_chroma_config(arguments.config)
        report = inspect_transparency_with_report(
            arguments.image,
            expected_width,
            expected_height,
            config,
            arguments.report,
            config_path=arguments.config,
        )
        payload = report.to_json()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _presentation_dimensions(reference: str) -> tuple[int, int]:
    width, height, _, _ = _presentation_dimensions_and_paths(reference)
    return width, height


def _presentation_dimensions_and_paths(
    reference: str,
) -> tuple[int, int, Path, Path]:
    if not isinstance(reference, str) or ":" not in reference:
        raise ValueError("--expected-from requires board.json:presentationID")
    board_text, presentation_id = reference.rsplit(":", 1)
    if not board_text or not presentation_id:
        raise ValueError("--expected-from requires board.json:presentationID")
    board_path = Path(board_text)
    payload = _load_json(board_path, "--expected-from board.json")
    if not isinstance(payload, dict) or not isinstance(
        payload.get("presentations"), list
    ):
        raise ValueError("--expected-from board.json requires a presentations array")
    matches = []
    for index, record in enumerate(payload["presentations"]):
        if not isinstance(record, dict):
            raise ValueError(f"board.json.presentations[{index}] must be an object")
        if record.get("id") == presentation_id:
            matches.append((index, record))
    if len(matches) != 1:
        raise ValueError(
            f"--expected-from must identify exactly one presentation: {presentation_id}"
        )
    index, presentation = matches[0]
    asset_path = presentation.get("assetPath")
    if not isinstance(asset_path, str) or not asset_path:
        raise ValueError(
            f"board.json.presentations[{index}].assetPath must be a non-empty string"
        )
    relative = Path(asset_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(
            f"board.json.presentations[{index}].assetPath escapes its package"
        )
    package_root = Path(os.path.abspath(os.fspath(board_path))).parent
    asset = Path(os.path.abspath(os.fspath(package_root / relative)))
    if package_root not in asset.parents:
        raise ValueError(
            f"board.json.presentations[{index}].assetPath escapes its package"
        )
    snapshot = _snapshot_image(asset)
    if snapshot.format != "PNG":
        raise ValueError(f"presentation asset is not a PNG: {asset}")
    return snapshot.image.width, snapshot.image.height, board_path, asset


def _transient_file_mapping(
    pairs: Sequence[Sequence[str]],
    label: str,
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for digest, path in pairs:
        if digest in result:
            raise ValueError(f"duplicate --{label} SHA-256 key: {digest}")
        result[digest] = Path(path)
    return result


def _status_payload(inventory: BoardInventory) -> str:
    payload = {
        "boards": [_board_status(package) for package in inventory.packages],
        "drafts": [path.name for path in inventory.drafts],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _board_status(package: BoardPackage) -> dict[str, object]:
    return {
        "id": package.board.id,
        "path": package.root.name,
    }


if __name__ == "__main__":
    raise SystemExit(main())
