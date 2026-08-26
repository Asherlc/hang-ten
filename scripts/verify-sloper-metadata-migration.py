#!/usr/bin/env python3
"""Verify that a Git range changes board JSON only by adding sloper metadata."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import PurePosixPath
import subprocess
import sys


_TRAINING_PLAN_PATHS = frozenset(
    {
        "HangTen/Models/PlanStorage.swift",
        "HangTen/Resources/PlanLibrary.json",
        "docs/TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md",
        "docs/source-audits/2026-08-10-plan-cue-provenance.md",
    }
)


class VerificationError(Exception):
    """Raised when the inspected range contains a prohibited change."""


def _git_text(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def _git_bytes(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
    )


def _changed_paths(base: str, head: str) -> list[str]:
    result = _git_text("diff", "--name-only", "--no-renames", "-z", base, head)
    if result.returncode != 0:
        message = result.stderr.strip() or "unknown Git error"
        raise VerificationError(f"could not inspect {base}..{head}: {message}")
    return sorted(path for path in result.stdout.split("\0") if path)


def _merge_base(base: str, head: str) -> str:
    result = _git_text("merge-base", base, head)
    merge_base = result.stdout.strip()
    if result.returncode != 0 or not merge_base:
        message = result.stderr.strip() or "no common ancestor"
        raise VerificationError(f"could not find merge base for {base} and {head}: {message}")
    return merge_base


def _is_board_json(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (
        len(parts) == 3
        and parts[0] == "Hangboards"
        and parts[1] not in {"", ".", ".."}
        and parts[2] == "board.json"
    )


def _load_json_at(ref: str, path: str, label: str) -> object:
    result = _git_bytes("show", f"{ref}:{path}")
    if result.returncode != 0:
        raise VerificationError(f"{path}: missing at {label}")
    try:
        source = result.stdout.decode("utf-8")
        return json.loads(source, parse_constant=_reject_nonstandard_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(f"{path}: {label} JSON is invalid: {error}") from error


def _reject_nonstandard_constant(value: str) -> object:
    raise ValueError(f"invalid constant {value}")


def _first_difference(base: object, head: object, path: str = "") -> str | None:
    label = path or "document"
    if type(base) is not type(head):
        return f"{label} changed type"
    if isinstance(base, dict):
        assert isinstance(head, dict)
        for key in base:
            key_path = f"{path}.{key}" if path else str(key)
            if key not in head:
                return f"{key_path} was removed"
            difference = _first_difference(base[key], head[key], key_path)
            if difference is not None:
                return difference
        for key in head:
            if key not in base:
                key_path = f"{path}.{key}" if path else str(key)
                return f"{key_path} was added"
        return None
    if isinstance(base, list):
        assert isinstance(head, list)
        if len(base) != len(head):
            return f"{label} length changed"
        for index, (base_item, head_item) in enumerate(zip(base, head)):
            item_path = f"{path}[{index}]"
            difference = _first_difference(base_item, head_item, item_path)
            if difference is not None:
                return difference
        return None
    if base != head:
        return f"{label} changed"
    return None


def _verify_added_sloper(head_hold: dict[object, object], path: str) -> None:
    if head_hold.get("kind") != "sloper":
        raise VerificationError(f"{path} is only allowed for kind sloper")

    value = head_hold["sloper"]
    if not isinstance(value, dict):
        raise VerificationError(f"{path} must be an object")
    if set(value) - {"type", "angleDegrees"}:
        raise VerificationError(
            f"{path} may contain only type and optional angleDegrees"
        )

    sloper_type = value.get("type")
    if not isinstance(sloper_type, str) or sloper_type not in {"flat", "round"}:
        raise VerificationError(f"{path}.type must be flat or round")
    if sloper_type == "round":
        if "angleDegrees" in value:
            raise VerificationError(
                f"{path}.angleDegrees is only allowed for flat slopers"
            )
        return

    angle_degrees = value.get("angleDegrees")
    if isinstance(angle_degrees, bool) or not isinstance(angle_degrees, (int, float)):
        raise VerificationError(f"{path}.angleDegrees must be a number")
    if not math.isfinite(angle_degrees) or not 0 <= angle_degrees <= 90:
        raise VerificationError(f"{path}.angleDegrees must be in 0...90")


def _verify_board_json(base: object, head: object, path: str) -> int:
    if not isinstance(base, dict) or not isinstance(base.get("holds"), list):
        raise VerificationError(f"{path}: base JSON must contain a holds array")
    if not isinstance(head, dict) or not isinstance(head.get("holds"), list):
        raise VerificationError(f"{path}: head JSON must contain a holds array")

    base_holds = base["holds"]
    head_holds = head["holds"]
    if len(base_holds) != len(head_holds):
        raise VerificationError(f"{path}: hold count changed")

    candidate = copy.deepcopy(head)
    candidate_holds = candidate["holds"]
    added_sloper_count = 0
    for index, (base_hold, head_hold, candidate_hold) in enumerate(
        zip(base_holds, head_holds, candidate_holds)
    ):
        if not all(
            isinstance(hold, dict) for hold in (base_hold, head_hold, candidate_hold)
        ):
            raise VerificationError(f"{path}: holds[{index}] must be an object")
        if base_hold.get("id") != head_hold.get("id"):
            raise VerificationError(
                f"{path}: hold identity/order changed at holds[{index}]"
            )

        sloper_path = f"holds[{index}].sloper"
        if "sloper" in base_hold:
            if "sloper" not in head_hold:
                raise VerificationError(
                    f"{path}: pre-existing {sloper_path} was removed"
                )
            if _first_difference(base_hold["sloper"], head_hold["sloper"]):
                raise VerificationError(f"{path}: pre-existing {sloper_path} changed")
        elif "sloper" in head_hold:
            _verify_added_sloper(head_hold, f"{path}: {sloper_path}")
            del candidate_hold["sloper"]
            added_sloper_count += 1

    difference = _first_difference(base, candidate)
    if difference is not None:
        raise VerificationError(f"{path}: {difference}")
    if added_sloper_count == 0:
        raise VerificationError(f"{path}: changed without adding holds[*].sloper")
    return added_sloper_count


def verify(base: str, head: str) -> int:
    board_paths: list[str] = []
    merge_base = _merge_base(base, head)
    for path in _changed_paths(merge_base, head):
        if path in _TRAINING_PLAN_PATHS:
            raise VerificationError(f"{path}: training-plan source path changed")
        if path.startswith("Hangboards/"):
            if not _is_board_json(path):
                raise VerificationError(
                    f"{path}: hangboard package change is not a board.json sloper addition"
                )
            board_paths.append(path)

    if not board_paths:
        raise VerificationError("range contains no changed Hangboards/*/board.json paths")

    added_sloper_count = 0
    for path in board_paths:
        base_document = _load_json_at(merge_base, path, "merge base")
        head_document = _load_json_at(head, path, "head")
        added_sloper_count += _verify_board_json(base_document, head_document, path)
    if added_sloper_count == 0:
        raise VerificationError("range contains no new valid holds[*].sloper values")
    return len(board_paths)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Allow only new holds[*].sloper values in changed board JSON."
    )
    parser.add_argument("base", help="base Git ref")
    parser.add_argument("head", help="head Git ref")
    arguments = parser.parse_args()

    try:
        board_count = verify(arguments.base, arguments.head)
    except VerificationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    noun = "file" if board_count == 1 else "files"
    print(f"Verified sloper-only board JSON changes in {board_count} {noun}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
