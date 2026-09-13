#!/usr/bin/env python3
"""Convert a single-layer USDA USDZ to deterministic binary-USDC USDZ.

This is a serialization-only optimization. It does not regenerate descriptors
or modify the input archive; verify the actual exported model and explicitly
regenerate any descriptor after promoting the output.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence


_DETERMINISTIC_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_USD_LAYER_SUFFIXES = frozenset({".usda"})
_TARGET_LAYER_SUFFIX = ".usdc"


def optimize_usdz(
    input_path: Path,
    output_path: Path,
    *,
    usdcat_executable: str = "usdcat",
) -> None:
    """Write a deterministic USDZ with its one USD layer encoded as USDC.

    The input is never modified. All non-layer members are copied byte-for-byte
    and every output member is uncompressed, timestamp-stable, and 64-byte
    aligned for USDZ consumers.
    """
    source = _regular_file(input_path, "input USDZ")
    output = Path(output_path)
    if output.exists() or output.is_symlink():
        raise ValueError(f"output USDZ must not already exist: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    if source == output:
        raise ValueError("input and output USDZ paths must differ")
    usdcat = _resolve_executable(usdcat_executable)

    with tempfile.TemporaryDirectory(
        prefix=f".{output.stem}.optimize-", dir=output.parent
    ) as raw_directory:
        directory = Path(raw_directory)
        members = _extract_safe_archive(source, directory)
        layer_names = [
            name for name in members if PurePosixPath(name).suffix in _USD_LAYER_SUFFIXES
        ]
        if len(layer_names) != 1:
            raise ValueError("USDZ optimizer requires exactly one text USDA layer")
        source_layer_name = layer_names[0]
        source_layer = directory / _native_path(source_layer_name)
        target_layer_name = str(
            PurePosixPath(source_layer_name).with_suffix(_TARGET_LAYER_SUFFIX)
        )
        target_layer = directory / _native_path(target_layer_name)
        _convert_layer_to_usdc(usdcat, source_layer, target_layer)
        source_layer.unlink()

        output_members = [target_layer_name] + sorted(
            name for name in members if name != source_layer_name
        )
        temporary_archive = output.with_name(f".{output.name}.tmp")
        try:
            _write_deterministic_archive(temporary_archive, directory, output_members)
            os.replace(temporary_archive, output)
        finally:
            temporary_archive.unlink(missing_ok=True)


def _regular_file(path: Path, label: str) -> Path:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"{label} must be a regular file: {candidate}")
    return candidate.resolve()


def _resolve_executable(command: str) -> str:
    resolved = shutil.which(command)
    if resolved is None:
        raise ValueError(f"usdcat executable was not found: {command}")
    return resolved


def _native_path(name: str) -> Path:
    return Path(*PurePosixPath(name).parts)


def _safe_member_name(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or path.as_posix() != name
        or path.is_absolute()
        or name.endswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("USDZ export contains unsafe member paths")


def _extract_safe_archive(source: Path, destination: Path) -> tuple[str, ...]:
    try:
        with zipfile.ZipFile(source) as archive:
            names = tuple(info.filename for info in archive.infolist())
            if len(names) != len(set(names)):
                raise ValueError("USDZ export contains duplicate member paths")
            for name in names:
                _safe_member_name(name)
                target = destination / _native_path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
            return names
    except zipfile.BadZipFile as error:
        raise ValueError("input USDZ is not a readable archive") from error


def _convert_layer_to_usdc(usdcat: str, source: Path, target: Path) -> None:
    # usdcat only accepts --usdFormat when the output extension is `.usd`;
    # rename the resulting binary layer after conversion to retain `.usdc`.
    temporary_target = target.with_suffix(".usd")
    try:
        result = subprocess.run(
            [
                usdcat,
                "--usdFormat",
                "usdc",
                "--out",
                str(temporary_target),
                str(source),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if (
            result.returncode != 0
            or not temporary_target.is_file()
            or not temporary_target.read_bytes()
        ):
            detail = (result.stderr or result.stdout).strip()
            raise ValueError(f"USD layer conversion to USDC failed: {detail}")
        os.replace(temporary_target, target)
    finally:
        temporary_target.unlink(missing_ok=True)


def _write_deterministic_archive(
    destination: Path,
    directory: Path,
    members: Sequence[str],
) -> None:
    with destination.open("wb") as raw_destination:
        with zipfile.ZipFile(
            raw_destination, "w", compression=zipfile.ZIP_STORED
        ) as archive:
            for name in members:
                offset = raw_destination.tell()
                encoded_name = name.encode("utf-8")
                padding = (-(offset + 30 + len(encoded_name) + 4)) % 64
                info = zipfile.ZipInfo(name, _DETERMINISTIC_ZIP_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.extra = (
                    b"\xff\xff"
                    + padding.to_bytes(2, "little")
                    + bytes(padding)
                )
                archive.writestr(info, (directory / _native_path(name)).read_bytes())


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="source USDZ")
    parser.add_argument("--output", type=Path, required=True, help="new optimized USDZ")
    parser.add_argument(
        "--usdcat",
        default="usdcat",
        help="usdcat executable or path (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = (
        list(sys.argv[sys.argv.index("--") + 1 :])
        if argv is None and "--" in sys.argv
        else list(sys.argv[1:] if argv is None else argv)
    )
    arguments = _arguments(raw_arguments)
    try:
        optimize_usdz(
            arguments.input,
            arguments.output,
            usdcat_executable=arguments.usdcat,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
