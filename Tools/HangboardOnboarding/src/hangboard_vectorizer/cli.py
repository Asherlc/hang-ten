from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import math
from pathlib import Path
import sys
import tempfile

import cv2
import numpy as np

from .alignment import AlignmentInfo, align_board_to_template
from .export import build_manifest, render_preview, render_svg
from .geometry import detect_openings, isolate_board, rectify_board
from .image_io import load_image
from .models import ConversionError
from .overrides import apply_overrides
from .product_validation import validate_product_output
from .regions import build_regions
from .templates import (
    get_product_template,
    layout_from_template,
    list_product_templates,
)
from .workspace_paths import default_workspace_root, resolve_workspace_path


class _CliError(ValueError):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CliError(message)


def main(argv: Sequence[str] | None = None) -> int:
    """Convert one hangboard photo and return a process-style exit code."""
    try:
        arguments = _parser().parse_args(argv)
        _validate_arguments(arguments)
        if arguments.list_products:
            for product_id, display_name in list_product_templates():
                print(f"{product_id}\t{display_name}")
            return 0
        _convert(arguments)
    except SystemExit as exc:
        return int(exc.code or 0)
    except (ConversionError, OSError, ValueError, cv2.error) as exc:
        message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
        print(f"error: {message}", file=sys.stderr)
        return 2
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="hangboard-to-svg",
        description="Convert a clean hangboard product photo to interactive SVG.",
    )
    parser.add_argument(
        "source", nargs="?", help="local image path or HTTP(S) image URL"
    )
    parser.add_argument("--output", type=Path, help="output SVG path")
    parser.add_argument("--manifest", type=Path, help="output JSON manifest path")
    parser.add_argument("--preview", type=Path, help="optional diagnostic PNG path")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=default_workspace_root(),
        help=(
            "owned root for generated artifacts "
            "(default: $HANGBOARD_WORKSPACE_ROOT or .context/hangboard-onboarding)"
        ),
    )
    parser.add_argument("--overrides", type=Path, help="optional override JSON path")
    parser.add_argument(
        "--width", type=float, default=1_000, help="normalized SVG width"
    )
    parser.add_argument("--background-tolerance", type=float, default=18.0)
    parser.add_argument("--contrast-threshold", type=float, default=25.0)
    parser.add_argument("--min-area-ratio", type=float, default=0.0005)
    parser.add_argument("--rail-aspect-ratio", type=float, default=3.0)
    parser.add_argument("--rail-width-ratio", type=float, default=0.18)
    parser.add_argument("--row-tolerance-ratio", type=float, default=0.06)
    parser.add_argument("--product", help="built-in commercial product ID")
    parser.add_argument(
        "--experimental-recess-detection",
        action="store_true",
        help="detect only visible dark recess candidates",
    )
    parser.add_argument(
        "--allow-low-confidence",
        action="store_true",
        help="allow a product alignment with more than 15%% aspect error",
    )
    parser.add_argument(
        "--list-products",
        action="store_true",
        help="list supported commercial products and exit",
    )
    return parser


def _validate_arguments(arguments: argparse.Namespace) -> None:
    if arguments.list_products:
        return
    if (
        arguments.source is None
        or arguments.output is None
        or arguments.manifest is None
    ):
        raise _CliError("source, --output, and --manifest are required for conversion")
    if (arguments.product is not None) == arguments.experimental_recess_detection:
        raise _CliError(
            "exactly one of --product or --experimental-recess-detection is required"
        )
    if arguments.allow_low_confidence and arguments.product is None:
        raise _CliError("--allow-low-confidence requires --product")

    arguments.workspace_root = arguments.workspace_root.resolve(strict=False)
    for name in ("output", "manifest", "preview"):
        destination = getattr(arguments, name)
        if destination is not None:
            setattr(
                arguments,
                name,
                resolve_workspace_path(destination, arguments.workspace_root),
            )

    destinations = [arguments.output, arguments.manifest]
    if arguments.preview is not None:
        destinations.append(arguments.preview)
    normalized_destinations = [
        destination.resolve(strict=False) for destination in destinations
    ]
    if len(set(normalized_destinations)) != len(normalized_destinations):
        raise _CliError("--output, --manifest, and --preview must be distinct paths")

    numeric_values = (
        arguments.width,
        arguments.background_tolerance,
        arguments.contrast_threshold,
        arguments.min_area_ratio,
        arguments.rail_aspect_ratio,
        arguments.rail_width_ratio,
        arguments.row_tolerance_ratio,
    )
    if not all(math.isfinite(value) for value in numeric_values):
        raise _CliError("numeric options must be finite")
    if arguments.width <= 0:
        raise _CliError("--width must be positive")
    for name in ("background_tolerance", "contrast_threshold"):
        value = getattr(arguments, name)
        if not 0 <= value <= 255:
            raise _CliError(f"--{name.replace('_', '-')} must be between 0 and 255")
    if arguments.rail_aspect_ratio <= 0:
        raise _CliError("--rail-aspect-ratio must be positive")
    for name in ("min_area_ratio", "rail_width_ratio", "row_tolerance_ratio"):
        value = getattr(arguments, name)
        if not 0 <= value <= 1:
            raise _CliError(f"--{name.replace('_', '-')} must be between 0 and 1")


def _convert(arguments: argparse.Namespace) -> None:
    product = (
        get_product_template(arguments.product)
        if arguments.product is not None
        else None
    )
    loaded = load_image(arguments.source)
    mask = isolate_board(
        loaded.rgb, background_tolerance=arguments.background_tolerance
    )
    alignment: AlignmentInfo | None = None
    if product is not None:
        aligned = align_board_to_template(
            loaded.rgb,
            mask,
            product,
            allow_low_confidence=arguments.allow_low_confidence,
        )
        board = aligned.board
        alignment = aligned.info
        layout = layout_from_template(product, board)
    else:
        board = rectify_board(loaded.rgb, mask)
        detected = detect_openings(
            board,
            contrast_threshold=arguments.contrast_threshold,
            min_area_ratio=arguments.min_area_ratio,
        )
        layout = build_regions(
            detected,
            board.width,
            board.height,
            rail_aspect_ratio=arguments.rail_aspect_ratio,
            rail_width_ratio=arguments.rail_width_ratio,
            row_tolerance_ratio=arguments.row_tolerance_ratio,
        )
    regions = layout.regions
    if arguments.overrides is not None:
        document = json.loads(arguments.overrides.read_text(encoding="utf-8"))
        regions = apply_overrides(regions, document, board.width, board.height)
    if product is not None:
        validate_product_output(product, regions)

    svg = render_svg(
        board,
        layout.openings,
        regions,
        normalized_width=arguments.width,
        product=product,
    )
    manifest = build_manifest(
        arguments.source,
        board,
        layout.openings,
        regions,
        product=product,
        alignment=alignment,
    )
    destinations = [arguments.output, arguments.manifest]
    if arguments.preview is not None:
        destinations.append(arguments.preview)
    for parent in {destination.parent for destination in destinations}:
        parent.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        staged.append((_stage_text(arguments.output, svg), arguments.output))
        staged.append(
            (
                _stage_text(
                    arguments.manifest,
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                ),
                arguments.manifest,
            )
        )
        if arguments.preview is not None:
            preview = render_preview(board, layout.openings, regions)
            staged.append(
                (_stage_preview(arguments.preview, preview), arguments.preview)
            )
        _publish_transaction(staged)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def _stage_text(target: Path, content: str) -> Path:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        return temporary
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _stage_preview(target: Path, rgb: np.ndarray) -> Path:
    suffix = target.suffix or ".png"
    with tempfile.NamedTemporaryFile(
        dir=target.parent,
        prefix=f".{target.stem}.",
        suffix=suffix,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        if not cv2.imwrite(str(temporary), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
            raise OSError(f"could not write preview: {target}")
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _publish_transaction(staged: Sequence[tuple[Path, Path]]) -> None:
    targets = tuple(target for _, target in staged)
    backups = _backup_destinations(targets)
    try:
        for temporary, target in staged:
            temporary.replace(target)
    except OSError as publication_error:
        try:
            _rollback_publication(targets, backups)
        except OSError as rollback_error:
            raise rollback_error from publication_error
        raise
    else:
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def _backup_destinations(targets: tuple[Path, ...]) -> dict[Path, Path]:
    backups: dict[Path, Path] = {}
    try:
        for target in targets:
            if not (target.exists() or target.is_symlink()):
                continue
            backup = _reserve_backup(target)
            try:
                target.replace(backup)
            except OSError:
                backup.unlink(missing_ok=True)
                raise
            backups[target] = backup
    except OSError as backup_error:
        try:
            _restore_backups(backups)
        except OSError as rollback_error:
            raise rollback_error from backup_error
        raise
    return backups


def _reserve_backup(target: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".bak",
        delete=False,
    ) as handle:
        return Path(handle.name)


def _rollback_publication(targets: tuple[Path, ...], backups: dict[Path, Path]) -> None:
    errors: list[OSError] = []
    for target in targets:
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(exc)
    try:
        _restore_backups(backups)
    except OSError as exc:
        errors.append(exc)
    if errors:
        raise OSError(f"could not roll back output publication: {errors[0]}")


def _restore_backups(backups: dict[Path, Path]) -> None:
    errors: list[OSError] = []
    for target, backup in reversed(tuple(backups.items())):
        try:
            backup.replace(target)
        except OSError as exc:
            errors.append(exc)
    if errors:
        raise OSError(f"could not restore output backup: {errors[0]}")


if __name__ == "__main__":
    raise SystemExit(main())
