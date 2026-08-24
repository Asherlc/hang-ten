from __future__ import annotations

import builtins
import signal
import socket
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EDITOR_ROOT.parents[1]
sys.path.insert(0, str(EDITOR_ROOT))

import workbench_binary  # noqa: E402


class FakeServer:
    def __init__(self, address: tuple[str, int]):
        self.server_address = address
        self.served = False
        self.closed = False

    def serve_forever(self) -> None:
        self.served = True

    def server_close(self) -> None:
        self.closed = True


def test_resource_root_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert workbench_binary._resource_root() == tmp_path.resolve()


def test_version_reads_exact_embedded_commit(tmp_path):
    commit = "a" * 40
    (tmp_path / "build-commit.txt").write_text(commit + "\n", encoding="ascii")

    assert workbench_binary._build_commit(tmp_path) == commit


def test_run_starts_and_closes_backend_without_browser(monkeypatch, tmp_path, capsys):
    server = FakeServer(("127.0.0.1", 4317))
    forwarded: list[str] = []
    roots: list[Path] = []

    def server_factory(arguments, *, editor_root):
        forwarded.extend(arguments)
        roots.append(editor_root)
        return server, None

    monkeypatch.setattr(workbench_binary, "_resource_root", lambda: tmp_path)
    arguments = ["--repository-root", str(tmp_path), "--port", "4317"]
    original_import = builtins.__import__

    def reject_browser_import(name, *args, **kwargs):
        if name == "webbrowser":
            raise AssertionError("packaged startup must not reach a browser launcher")
        return original_import(name, *args, **kwargs)

    def fail_browser_launch(_url):
        raise AssertionError("packaged startup must not launch a browser")

    monkeypatch.setattr(builtins, "__import__", reject_browser_import)
    monkeypatch.setattr(
        workbench_binary,
        "webbrowser",
        SimpleNamespace(open=fail_browser_launch),
        raising=False,
    )

    result = workbench_binary._run(
        arguments,
        server_factory=server_factory,
    )

    assert result == 0
    assert forwarded == arguments
    assert roots == [tmp_path]
    assert server.served and server.closed
    assert capsys.readouterr().out == "Hangboard Workbench: http://127.0.0.1:4317/\n"


def test_packaged_server_factory_selects_local_checkout_storage(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def server_factory(arguments, *, editor_root, local_checkout):
        captured.update(
            arguments=arguments,
            editor_root=editor_root,
            local_checkout=local_checkout,
        )
        return object(), None

    monkeypatch.setattr(workbench_binary, "_server_from_cli", server_factory)

    workbench_binary._packaged_server_factory(["--port", "0"], editor_root=tmp_path)

    assert captured == {
        "arguments": ["--port", "0"],
        "editor_root": tmp_path,
        "local_checkout": True,
    }


@pytest.mark.filterwarnings(
    "ignore:urllib3 .* doesn't match a supported version!"
)
def test_main_names_a_missing_static_asset_without_exposing_its_root(
    monkeypatch, tmp_path, capsys
):
    repository_root = tmp_path / "repository"
    (repository_root / ".git").mkdir(parents=True)
    (repository_root / "Hangboards").mkdir(parents=True)
    (repository_root / "Tools" / "HangboardWorkbench").mkdir(parents=True)
    (repository_root / "Tools" / "HangboardWorkbench" / "server.py").touch()
    (repository_root / "Tools" / "HangboardWorkbench" / "board_package.py").touch()
    (repository_root / "Tools" / "HangboardWorkbench" / "board_geometry.py").touch()
    resource_root = tmp_path / "private-frozen-root"
    resource_root.mkdir()
    monkeypatch.setattr(workbench_binary, "_resource_root", lambda: resource_root)

    result = workbench_binary.main(
        [
            "--no-open",
            "--repository-root",
            str(repository_root),
            "--port",
            "0",
        ]
    )

    assert result == 2
    error = capsys.readouterr().err
    assert "required static asset is missing: index.html" in error
    assert str(resource_root) not in error


@pytest.mark.filterwarnings(
    "ignore:urllib3 .* doesn't match a supported version!"
)
def test_main_names_the_requested_host_and_port_when_binding_fails(
    tmp_path, capsys
):
    repository_root = tmp_path / "repository"
    (repository_root / ".git").mkdir(parents=True)
    (repository_root / "Hangboards").mkdir(parents=True)
    (repository_root / "Tools" / "HangboardWorkbench").mkdir(parents=True)
    (repository_root / "Tools" / "HangboardWorkbench" / "server.py").touch()
    (repository_root / "Tools" / "HangboardWorkbench" / "board_package.py").touch()
    (repository_root / "Tools" / "HangboardWorkbench" / "board_geometry.py").touch()
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        host, port = occupied.getsockname()
        result = workbench_binary.main(
            [
                "--no-open",
                "--repository-root",
                str(repository_root),
                "--host",
                host,
                "--port",
                str(port),
            ]
        )

    assert result == 2
    error = capsys.readouterr().err
    assert f"could not bind to {host}:{port}" in error
    assert str(tmp_path) not in error
    assert "Address already in use" not in error


@pytest.mark.parametrize(
    ("initial_signal", "late_signal"),
    [
        (signal.SIGINT, signal.SIGTERM),
        (signal.SIGTERM, signal.SIGINT),
    ],
)
def test_run_absorbs_a_late_shutdown_signal_and_restores_both_handlers(
    monkeypatch, tmp_path, initial_signal, late_signal
):
    class InterruptingServer(FakeServer):
        def serve_forever(self) -> None:
            self.served = True
            signal.raise_signal(initial_signal)

        def server_close(self) -> None:
            self.closed = True
            signal.raise_signal(late_signal)

    server = InterruptingServer(("127.0.0.1", 4317))

    def server_factory(_arguments, *, editor_root):
        assert editor_root == tmp_path
        return server, None

    monkeypatch.setattr(workbench_binary, "_resource_root", lambda: tmp_path)
    installed_handlers = {
        shutdown_signal: (lambda _signum, _frame: None)
        for shutdown_signal in (signal.SIGINT, signal.SIGTERM)
    }
    original_handlers = {
        shutdown_signal: signal.signal(
            shutdown_signal, installed_handlers[shutdown_signal]
        )
        for shutdown_signal in installed_handlers
    }
    try:
        try:
            result = workbench_binary._run(
                ["--no-open"],
                server_factory=server_factory,
            )
        except KeyboardInterrupt:
            pytest.fail("late duplicate interrupt escaped the entrypoint boundary")
        for shutdown_signal, installed_handler in installed_handlers.items():
            assert signal.getsignal(shutdown_signal) is installed_handler
    finally:
        for shutdown_signal, original_handler in original_handlers.items():
            signal.signal(shutdown_signal, original_handler)

    assert result == 0
    assert server.served and server.closed


@pytest.mark.parametrize("contents", [None, "short", "A" * 40])
def test_version_rejects_missing_or_invalid_build_metadata(tmp_path, contents):
    if contents is not None:
        (tmp_path / "build-commit.txt").write_text(contents, encoding="ascii")

    with pytest.raises(workbench_binary.PackagedWorkbenchError):
        workbench_binary._build_commit(tmp_path)
