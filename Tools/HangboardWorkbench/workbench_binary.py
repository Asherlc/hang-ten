"""Packaged startup boundary for the local Hangboard Workbench."""

from __future__ import annotations

import re
import signal
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Protocol

from server import (
    EditorError,
    ServerBindError,
    StaticAssetError,
    WorkbenchHTTPServer,
    _server_from_cli,
)


class PackagedWorkbenchError(ValueError):
    """A safe startup error for the packaged workbench."""


class WorkbenchServerFactory(Protocol):
    """Build a packaged server with its embedded editor assets."""

    def __call__(
        self,
        arguments: list[str],
        *,
        editor_root: Path,
    ) -> tuple[WorkbenchHTTPServer, None]: ...


def _resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return (
        Path(frozen_root).resolve(strict=False)
        if frozen_root is not None
        else Path(__file__).resolve().parent
    )


def _build_commit(root: Path) -> str:
    path = root / "build-commit.txt"
    try:
        value = path.read_text(encoding="ascii").strip()
    except OSError as error:
        raise PackagedWorkbenchError("embedded build metadata is missing") from error
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise PackagedWorkbenchError("embedded build metadata is invalid")
    return value


def _packaged_arguments(arguments: list[str]) -> tuple[bool, bool, list[str]]:
    parser = ArgumentParser(add_help=False)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--version", action="store_true")
    packaged, forwarded = parser.parse_known_args(arguments)
    return packaged.no_open, packaged.version, forwarded


def _run(
    arguments: list[str],
    *,
    server_factory: WorkbenchServerFactory,
) -> int:
    _no_open, show_version, forwarded = _packaged_arguments(arguments)
    root = _resource_root()
    if show_version:
        print(_build_commit(root), flush=True)
        return 0

    server, _unused_state = server_factory(forwarded, editor_root=root)
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}/"
    shutdown_requested = False
    shutdown_signals = (signal.SIGINT, signal.SIGTERM)

    def interrupt_once(_signum, _frame) -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            return
        shutdown_requested = True
        for shutdown_signal in shutdown_signals:
            signal.signal(shutdown_signal, signal.SIG_IGN)
        raise KeyboardInterrupt

    previous_handlers = {
        shutdown_signal: signal.signal(shutdown_signal, interrupt_once)
        for shutdown_signal in shutdown_signals
    }
    try:
        print(f"Hangboard Workbench: {url}", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            server.server_close()
        finally:
            for shutdown_signal, previous_handler in previous_handlers.items():
                signal.signal(shutdown_signal, previous_handler)
    return 0


def main(arguments: list[str] | None = None) -> int:
    try:
        return _run(
            list(sys.argv[1:] if arguments is None else arguments),
            server_factory=_server_from_cli,
        )
    except (PackagedWorkbenchError, ServerBindError, StaticAssetError) as error:
        print(f"Hangboard Workbench: {error}", file=sys.stderr)
    except (EditorError, OSError):
        print("Hangboard Workbench: could not start", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
