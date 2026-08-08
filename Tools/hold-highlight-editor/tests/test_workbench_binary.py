from __future__ import annotations

import sys
from pathlib import Path

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
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


def test_run_opens_browser_and_forwards_server_arguments(monkeypatch, tmp_path, capsys):
    server = FakeServer(("127.0.0.1", 4317))
    forwarded: list[str] = []
    roots: list[Path] = []
    opened: list[str] = []

    def server_factory(arguments, *, editor_root):
        forwarded.extend(arguments)
        roots.append(editor_root)
        return server, None

    def browser_open(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr(workbench_binary, "_resource_root", lambda: tmp_path)
    arguments = ["--repository-root", str(tmp_path), "--port", "4317"]

    result = workbench_binary._run(
        arguments,
        server_factory=server_factory,
        browser_open=browser_open,
    )

    assert result == 0
    assert forwarded == arguments
    assert roots == [tmp_path]
    assert opened == ["http://127.0.0.1:4317/"]
    assert server.served and server.closed
    assert capsys.readouterr().out == "Hangboard Workbench: http://127.0.0.1:4317/\n"


def test_no_open_skips_browser(monkeypatch, tmp_path):
    server = FakeServer(("127.0.0.1", 4317))
    opened: list[str] = []

    def server_factory(_arguments, *, editor_root):
        assert editor_root == tmp_path
        return server, None

    monkeypatch.setattr(workbench_binary, "_resource_root", lambda: tmp_path)

    result = workbench_binary._run(
        ["--no-open"],
        server_factory=server_factory,
        browser_open=lambda url: opened.append(url) or True,
    )

    assert result == 0
    assert opened == []
    assert server.served and server.closed


def test_browser_failure_prints_url_and_keeps_serving(monkeypatch, tmp_path, capsys):
    server = FakeServer(("127.0.0.1", 4317))

    def server_factory(_arguments, *, editor_root):
        assert editor_root == tmp_path
        return server, None

    monkeypatch.setattr(workbench_binary, "_resource_root", lambda: tmp_path)

    result = workbench_binary._run(
        [],
        server_factory=server_factory,
        browser_open=lambda _url: False,
    )

    assert result == 0
    assert server.served and server.closed
    assert "http://127.0.0.1:4317/" in capsys.readouterr().out


@pytest.mark.parametrize("contents", [None, "short", "A" * 40])
def test_version_rejects_missing_or_invalid_build_metadata(tmp_path, contents):
    if contents is not None:
        (tmp_path / "build-commit.txt").write_text(contents, encoding="ascii")

    with pytest.raises(workbench_binary.PackagedWorkbenchError):
        workbench_binary._build_commit(tmp_path)
