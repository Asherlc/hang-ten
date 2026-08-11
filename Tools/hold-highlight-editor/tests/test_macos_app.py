from __future__ import annotations

import importlib.util
import os
import plistlib
import stat
import struct
from pathlib import Path

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = EDITOR_ROOT / "packaging" / "macos_app.py"


def _load_app_module():
    spec = importlib.util.spec_from_file_location("macos_app", APP_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arm64_executable(path: Path, mode: int = 0o751) -> Path:
    path.write_bytes(struct.pack("<II", 0xFEEDFACF, 0x0100000C))
    path.chmod(mode)
    return path


def _non_arm64_executable(path: Path) -> Path:
    path.write_text("not a Mach-O executable", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_source_controlled_bundler_exists():
    assert APP_PATH.is_file()


def test_creates_the_committed_bundle_layout_and_plist_contract(tmp_path):
    app = _load_app_module()
    executable = _arm64_executable(tmp_path / "hangboard-workbench")
    output = tmp_path / "hangboard-workbench.app"

    built = app._build_bundle(executable, output, "314")

    assert built == output
    assert sorted(path.relative_to(output).as_posix() for path in output.rglob("*")) == [
        "Contents",
        "Contents/Info.plist",
        "Contents/MacOS",
        "Contents/MacOS/hangboard-workbench",
    ]
    with (output / "Contents" / "Info.plist").open("rb") as source:
        metadata = plistlib.load(source)
    assert metadata == {
        "CFBundleIdentifier": "com.hangten.hangboard-workbench",
        "CFBundleName": "Hangboard Workbench",
        "CFBundleExecutable": "hangboard-workbench",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "314",
        "CFBundleVersion": "314",
    }


def test_cli_propagates_version_and_preserves_executable_mode(tmp_path):
    app = _load_app_module()
    executable = _arm64_executable(tmp_path / "hangboard-workbench", 0o751)
    output = tmp_path / "hangboard-workbench.app"

    assert app.main(
        ["--executable", str(executable), "--output", str(output), "--version", "99"]
    ) == 0

    bundled_executable = output / "Contents" / "MacOS" / "hangboard-workbench"
    assert stat.S_IMODE(bundled_executable.stat().st_mode) == 0o751
    with (output / "Contents" / "Info.plist").open("rb") as source:
        metadata = plistlib.load(source)
    assert metadata["CFBundleShortVersionString"] == "99"
    assert metadata["CFBundleVersion"] == "99"


@pytest.mark.parametrize(
    "prepare",
    [
        lambda path: path,
        lambda path: _arm64_executable(path, 0o644),
        _non_arm64_executable,
    ],
)
def test_rejects_invalid_executable_inputs(tmp_path, prepare):
    app = _load_app_module()
    executable = prepare(tmp_path / "hangboard-workbench")

    with pytest.raises(app.MacOSAppError):
        app._build_bundle(executable, tmp_path / "hangboard-workbench.app", "1")


def test_invalid_input_leaves_an_existing_bundle_untouched(tmp_path):
    app = _load_app_module()
    output = tmp_path / "hangboard-workbench.app"
    marker = output / "existing-marker"
    marker.parent.mkdir()
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(app.MacOSAppError):
        app._build_bundle(tmp_path / "missing", output, "1")

    assert marker.read_text(encoding="utf-8") == "keep"


def test_valid_bundle_replaces_existing_output_after_staging(tmp_path):
    app = _load_app_module()
    executable = _arm64_executable(tmp_path / "hangboard-workbench")
    output = tmp_path / "hangboard-workbench.app"
    stale_file = output / "stale"
    stale_file.parent.mkdir()
    stale_file.write_text("old", encoding="utf-8")

    app._build_bundle(executable, output, "2")

    assert not stale_file.exists()
    assert (output / "Contents" / "MacOS" / "hangboard-workbench").is_file()


def test_failed_bundle_install_restores_existing_output(tmp_path, monkeypatch):
    app = _load_app_module()
    executable = _arm64_executable(tmp_path / "hangboard-workbench")
    output = tmp_path / "hangboard-workbench.app"
    marker = output / "existing-marker"
    marker.parent.mkdir()
    marker.write_text("keep", encoding="utf-8")

    original_replace = app.os.replace
    installation_failed = False

    def fail_install_once(source, destination):
        nonlocal installation_failed
        if (
            not installation_failed
            and destination == output
            and ".backup-" not in Path(source).parent.name
        ):
            installation_failed = True
            raise OSError("simulated installation failure")
        return original_replace(source, destination)

    monkeypatch.setattr(app.os, "replace", fail_install_once)

    with pytest.raises(OSError, match="simulated installation failure"):
        app._build_bundle(executable, output, "2")

    assert marker.read_text(encoding="utf-8") == "keep"
    assert not list(tmp_path.glob(f".{output.name}.backup-*"))
