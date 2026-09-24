"""Explicit role bindings of a native FCStd source, checked before compiling.

The archive preflight (``inspect_archive``) is pure host Python shared with the
package validator; it lives in ``hangboard_packages.cad_source``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import re

NODE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_bindings(nodes: Sequence[Mapping], board: Mapping, version: int,
                      slots: Sequence[str]) -> None:
    """Require explicit, complete role bindings; never infer meaning from geometry."""
    if isinstance(version, bool) or version not in {1, 2}:
        raise ValueError("descriptor version must be 1 or 2")
    if board.get("schemaVersion") != 3 or not isinstance(board.get("id"), str):
        raise ValueError("board metadata must be schema-v3 with an ID")
    contacts = board.get("contacts")
    if not isinstance(contacts, list) or not contacts:
        raise ValueError("board contacts must be a nonempty list")
    ids = [c.get("id") if isinstance(c, Mapping) else None for c in contacts]
    if any(not isinstance(c, str) or not c for c in ids) or len(ids) != len(set(ids)):
        raise ValueError("invalid or duplicate board contact IDs")
    if version == 1 and slots:
        raise ValueError("v1 source must not declare reusable slots")
    if version == 2 and (not slots or any(not isinstance(s, str) or not s for s in slots)
                         or len(slots) != len(set(slots))):
        raise ValueError("invalid reusable slot inventory")
    names, bound = set(), set()
    bodies = 0
    key = "contact" if version == 1 else "slot"
    for node in nodes:
        name, role = node.get("id"), node.get("role")
        if (not isinstance(name, str) or not NODE_ID.fullmatch(name) or name in names
                or role not in {"body", "contact", "attachment"}):
            raise ValueError("invalid/duplicate node ID or role")
        if set(node) - {"id", "role", key}:
            raise ValueError("unexpected node binding fields")
        names.add(name)
        if role == "contact":
            value = node.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError("contact node requires its explicit binding")
            bound.add(value)
        elif key in node:
            raise ValueError("non-contact node cannot carry contact binding")
        bodies += role == "body"
    expected = set(ids if version == 1 else slots)
    if not bodies or bound != expected:
        raise ValueError("source body/contact inventory does not match board/slots")
