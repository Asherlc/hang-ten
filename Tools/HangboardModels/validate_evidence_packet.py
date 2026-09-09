#!/usr/bin/env python3
"""Validate one retained Stage 0 evidence packet from the command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evidence_packet import validate_evidence_packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Hang Ten evidence packet")
    parser.add_argument("packet", type=Path, help="path to packet.json")
    arguments = parser.parse_args(argv)
    try:
        validate_evidence_packet(arguments.packet)
    except ValueError as exc:
        print(f"invalid evidence packet: {exc}", file=sys.stderr)
        return 2
    print(f"valid evidence packet: {arguments.packet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

