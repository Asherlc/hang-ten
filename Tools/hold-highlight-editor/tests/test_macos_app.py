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


def _runtime_directory(root: Path) -> Path:
    runtime = root / "hangboard-workbench"
    internal = runtime / "_internal"
    internal.mkdir(parents=True)
    _arm64_executable(runtime / "hangboard-workbench", 0o751)
    resource = internal / "runtime-resource.txt"
    resource.write_text("embedded runtime", encoding="utf-8")
    resource.chmod(0o640)
    return runtime


def test_creates_native_shell_and_complete_runtime_bundle_layout(tmp_path):
    app = _load_app_module()
    shell = _arm64_executable(tmp_path / "native-shell")
    runtime = _runtime_directory(tmp_path / "runtime-dist")
    output = tmp_path / "Hangboard Workbench.app"

    built = app._build_bundle(shell, runtime, output, "314")

    assert built == output
    assert sorted(path.relative_to(output).as_posix() for path in output.rglob("*")) == [
        "Contents",
        "Contents/Info.plist",
        "Contents/MacOS",
        "Contents/MacOS/HangboardWorkbench",
        "Contents/Resources",
        "Contents/Resources/workbench-runtime",
        "Contents/Resources/workbench-runtime/_internal",
        "Contents/Resources/workbench-runtime/_internal/runtime-resource.txt",
        "Contents/Resources/workbench-runtime/hangboard-workbench",
    ]
    with (output / "Contents" / "Info.plist").open("rb") as source:
        metadata = plistlib.load(source)
    assert metadata == {
        "CFBundleIdentifier": "com.hangten.hangboard-workbench",
        "CFBundleName": "Hangboard Workbench",
        "CFBundleExecutable": "HangboardWorkbench",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "314",
        "CFBundleVersion": "314",
    }


def test_cli_propagates_version_and_preserves_shell_and_runtime_modes(tmp_path):
    app = _load_app_module()
    shell = _arm64_executable(tmp_path / "native-shell", 0o751)
    runtime = _runtime_directory(tmp_path / "runtime-dist")
    runtime.chmod(0o750)
    output = tmp_path / "Hangboard Workbench.app"

    assert app.main(
        [
            "--shell",
            str(shell),
            "--runtime-dir",
            str(runtime),
            "--output",
            str(output),
            "--version",
            "99",
        ]
    ) == 0

    bundled_shell = output / "Contents" / "MacOS" / "HangboardWorkbench"
    bundled_runtime = output / "Contents" / "Resources" / "workbench-runtime"
    assert stat.S_IMODE(bundled_shell.stat().st_mode) == 0o751
    assert stat.S_IMODE(bundled_runtime.stat().st_mode) == 0o750
    assert stat.S_IMODE((bundled_runtime / "hangboard-workbench").stat().st_mode) == 0o751
    assert stat.S_IMODE(
        (bundled_runtime / "_internal" / "runtime-resource.txt").stat().st_mode
    ) == 0o640
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
    shell = prepare(tmp_path / "native-shell")
    runtime = _runtime_directory(tmp_path / "runtime-dist")

    with pytest.raises(app.MacOSAppError):
        app._build_bundle(shell, runtime, tmp_path / "Hangboard Workbench.app", "1")


def test_missing_runtime_executable_leaves_an_existing_bundle_untouched(tmp_path):
    app = _load_app_module()
    shell = _arm64_executable(tmp_path / "native-shell")
    runtime = tmp_path / "hangboard-workbench"
    runtime.mkdir()
    output = tmp_path / "Hangboard Workbench.app"
    marker = output / "existing-marker"
    marker.parent.mkdir()
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(app.MacOSAppError, match="runtime executable"):
        app._build_bundle(shell, runtime, output, "1")

    assert marker.read_text(encoding="utf-8") == "keep"


def test_valid_bundle_replaces_existing_output_after_staging(tmp_path):
    app = _load_app_module()
    shell = _arm64_executable(tmp_path / "native-shell")
    runtime = _runtime_directory(tmp_path / "runtime-dist")
    output = tmp_path / "Hangboard Workbench.app"
    stale_file = output / "stale"
    stale_file.parent.mkdir()
    stale_file.write_text("old", encoding="utf-8")

    app._build_bundle(shell, runtime, output, "2")

    assert not stale_file.exists()
    assert (output / "Contents" / "MacOS" / "HangboardWorkbench").is_file()


def test_failed_bundle_install_restores_existing_output(tmp_path, monkeypatch):
    app = _load_app_module()
    shell = _arm64_executable(tmp_path / "native-shell")
    runtime = _runtime_directory(tmp_path / "runtime-dist")
    output = tmp_path / "Hangboard Workbench.app"
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
        app._build_bundle(shell, runtime, output, "2")

    assert marker.read_text(encoding="utf-8") == "keep"
    assert not list(tmp_path.glob(f".{output.name}.backup-*"))
