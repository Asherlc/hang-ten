#!/usr/bin/env python3
"""Loopback-only Workbench startup used exclusively by catalog capture."""

from __future__ import annotations

from server import _server_from_cli


def main() -> None:
    httpd, _ = _server_from_cli(local_checkout=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
