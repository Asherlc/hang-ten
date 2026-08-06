"""Provider-neutral, compact semantic vision contracts.

This module intentionally models only coarse semantic hints.  It does not
perform image processing, model transport, or deterministic hold refinement.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Literal, Protocol


COMPACT_SEMANTIC_SCHEMA_VERSION = 1
GRID_WIDTH = 20
GRID_HEIGHT = 8
_IDENTIFIER = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*\Z")
_HINT_KEY = re.compile(r"grip-[0-9]{3}\Z")
_ROOT_FIELDS = frozenset({"h"})
_HINT_FIELDS = frozenset({"k", "p", "t", "m", "a"})
_GRIP_TYPES = frozenset({"pocket", "edge", "sloper", "jug"})
_VISUAL_MODES = frozenset({"aperture", "surface"})


def canonical_json_bytes(document: object) -> bytes:
    """Return the sole wire encoding accepted by the compact contract."""
    return json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _identifier(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) > 128 or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a safe compact identifier")
    return value


def _nonnegative_int(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class SemanticVisionRequest:
    """Identity for a batched request against registered local pixels."""

    registered_pixel_sha256: str
    prompt_bytes: bytes
    provider_id: str
    model_id: str
    request_kind: str
    schema_version: int = COMPACT_SEMANTIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _is_sha256(self.registered_pixel_sha256):
            raise ValueError("registered pixel SHA-256 must be lowercase hexadecimal")
        if not isinstance(self.prompt_bytes, bytes) or not self.prompt_bytes:
            raise ValueError("semantic prompt must be nonempty immutable bytes")
        _identifier(self.provider_id, name="provider ID")
        _identifier(self.model_id, name="model ID")
        _identifier(self.request_kind, name="request kind")
        if self.schema_version != COMPACT_SEMANTIC_SCHEMA_VERSION:
            raise ValueError("unsupported compact semantic schema version")
        object.__setattr__(self, "prompt_bytes", bytes(self.prompt_bytes))

    @property
    def prompt_sha256(self) -> str:
        return sha256(self.prompt_bytes).hexdigest()

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            {
                "modelId": self.model_id,
                "promptSha256": self.prompt_sha256,
                "providerId": self.provider_id,
                "registeredPixelSha256": self.registered_pixel_sha256,
                "requestKind": self.request_kind,
                "schemaVersion": self.schema_version,
            }
        )


@dataclass(frozen=True, slots=True)
class CompactHoldHint:
    hint_key: str
    piece_index: int
    grip_type: Literal["pocket", "edge", "sloper", "jug"]
    visual_mode: Literal["aperture", "surface"]
    anchor: tuple[int, int]

    def __post_init__(self) -> None:
        if not isinstance(self.hint_key, str) or not _HINT_KEY.fullmatch(self.hint_key):
            raise ValueError("compact hint key must be generic grip-NNN")
        _nonnegative_int(self.piece_index, name="compact hint piece index")
        if self.grip_type not in _GRIP_TYPES:
            raise ValueError("unsupported compact grip type")
        if self.visual_mode not in _VISUAL_MODES:
            raise ValueError("unsupported compact visual mode")
        if (
            not isinstance(self.anchor, tuple)
            or len(self.anchor) != 2
            or any(type(cell) is not int for cell in self.anchor)
            or not (0 <= self.anchor[0] < GRID_WIDTH and 0 <= self.anchor[1] < GRID_HEIGHT)
        ):
            raise ValueError("compact hint anchor must be an integer cell on the 20x8 grid")

    def as_wire_document(self) -> dict[str, object]:
        return {
            "a": list(self.anchor),
            "k": self.hint_key,
            "m": self.visual_mode,
            "p": self.piece_index,
            "t": self.grip_type,
        }


@dataclass(frozen=True, slots=True)
class SemanticVisionResponse:
    hints: tuple[CompactHoldHint, ...]
    raw_bytes: bytes
    response_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.raw_bytes, bytes):
            raise ValueError("semantic response evidence must be immutable bytes")
        if not _is_sha256(self.response_sha256):
            raise ValueError("semantic response hash must be lowercase hexadecimal")
        if sha256(self.raw_bytes).hexdigest() != self.response_sha256:
            raise ValueError("semantic response hash does not match its evidence")
        if len({hint.hint_key for hint in self.hints}) != len(self.hints):
            raise ValueError("duplicate compact hint key")
        if len({(hint.piece_index, hint.anchor) for hint in self.hints}) != len(self.hints):
            raise ValueError("duplicate compact hint anchor cell")

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes({"h": [hint.as_wire_document() for hint in self.hints]})


@dataclass(frozen=True, slots=True)
class ModelInvocation:
    """Provider-reported usage; absent token splits remain absent, never inferred."""

    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    attempts: int
    retries: int
    wall_milliseconds: int
    details: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, name)
            if value is not None:
                _nonnegative_int(value, name=name.replace("_", " "))
        if type(self.attempts) is not int or self.attempts < 1:
            raise ValueError("attempts must be a positive integer")
        _nonnegative_int(self.retries, name="retries")
        if self.retries >= self.attempts:
            raise ValueError("retries must be less than attempts")
        _nonnegative_int(self.wall_milliseconds, name="wall milliseconds")
        if self.details is not None:
            if not isinstance(self.details, Mapping):
                raise ValueError("invocation details must be a mapping")
            try:
                canonical_json_bytes(dict(self.details))
            except (TypeError, ValueError) as error:
                raise ValueError("invocation details must be JSON-serializable") from error
            object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def as_document(self) -> dict[str, object]:
        return {
            "attempts": self.attempts,
            "details": None if self.details is None else dict(self.details),
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "retries": self.retries,
            "totalTokens": self.total_tokens,
            "wallMilliseconds": self.wall_milliseconds,
        }


@dataclass(frozen=True, slots=True)
class ProviderInvocation:
    response: SemanticVisionResponse
    invocation: ModelInvocation


class SemanticVisionProvider(Protocol):
    """A transport seam; implementations may be SDK-, HTTP-, or fixture-backed."""

    def invoke(self, request: SemanticVisionRequest) -> ProviderInvocation: ...


def parse_compact_semantic_response(raw_bytes: bytes) -> SemanticVisionResponse:
    """Parse the exact compact wire response and reject all latent geometry."""
    if not isinstance(raw_bytes, bytes):
        raise ValueError("semantic response must be immutable bytes")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate compact response key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"nonstandard compact JSON constant: {value}")

    try:
        document = json.loads(
            raw_bytes.decode("utf-8"), object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("compact semantic response is not valid JSON") from error
    if not isinstance(document, dict) or set(document) != _ROOT_FIELDS:
        raise ValueError("compact semantic response must contain only h")
    raw_hints = document["h"]
    if not isinstance(raw_hints, list):
        raise ValueError("compact semantic response h must be an array")

    hints: list[CompactHoldHint] = []
    for index, raw_hint in enumerate(raw_hints):
        if not isinstance(raw_hint, dict) or set(raw_hint) != _HINT_FIELDS:
            raise ValueError(f"compact hint {index} has unknown or missing fields")
        anchor = raw_hint["a"]
        if not isinstance(anchor, list) or len(anchor) != 2 or any(type(cell) is not int for cell in anchor):
            raise ValueError(f"compact hint {index} anchor must contain two integer cells")
        hints.append(
            CompactHoldHint(
                hint_key=raw_hint["k"],
                piece_index=raw_hint["p"],
                grip_type=raw_hint["t"],
                visual_mode=raw_hint["m"],
                anchor=(anchor[0], anchor[1]),
            )
        )
    canonical = canonical_json_bytes({"h": [hint.as_wire_document() for hint in hints]})
    if raw_bytes != canonical:
        raise ValueError("compact semantic response is not canonical bytes")
    return SemanticVisionResponse(
        hints=tuple(hints), raw_bytes=bytes(raw_bytes), response_sha256=sha256(raw_bytes).hexdigest(),
    )
