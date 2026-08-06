"""Schema-limited semantic proposals for Stage 2 hold discovery.

The provider is deliberately unable to describe geometry beyond a single cell
on a coarse grid.  Pixel geometry is owned by :mod:`hold_discovery`.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
import json
import re
from typing import Literal, Protocol

import numpy as np


GripType = Literal["pocket", "jug", "sloper"]
VisualMode = Literal["aperture", "surface"]
_HINT_KEY = re.compile(r"grip-[0-9]{3}\Z")
_PROVIDER_IDENTIFIER = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*\Z")
_HINT_FIELDS = frozenset({"hintKey", "pieceIndex", "gripType", "visualMode", "anchor"})
_ROOT_FIELDS = frozenset(
    {
        "schemaVersion", "instructionVersion", "gridWidth", "gridHeight",
        "inputPixelSha256", "providerId", "modelId", "promptId",
        "promptSha256", "hints",
    }
)
BEASTMAKER_STAGE2_CAPTURE_SHA256 = "d41770c31ed7a71025373374b73189de32114971926dd6b6ec551db1a7ce1b95"
SEMANTIC_PROMPT_SCHEMA_VERSION = 1
SEMANTIC_PROMPT_ID = "semantic-hold-anchor-grid-v1"
SEMANTIC_PROMPT_BYTES = (
    b'{"instructionVersion":"hold-discovery-anchor-grid-v1",'
    b'"output":"coarse 20x8 anchor cells only; no contours, boxes, accepted IDs, or dimensions",'
    b'"schemaVersion":1}\n'
)
SEMANTIC_PROMPT_SHA256 = "4fa1f73065b2d7478f27d101c7303816edd68579efd86622fe8cbcefe769dee6"

if sha256(SEMANTIC_PROMPT_BYTES).hexdigest() != SEMANTIC_PROMPT_SHA256:
    raise RuntimeError("canonical semantic prompt identity is invalid")


def _frozen_array(value: np.ndarray) -> np.ndarray:
    return np.frombuffer(value.tobytes(), dtype=value.dtype).reshape(value.shape)


@dataclass(frozen=True, slots=True)
class PieceDescriptor:
    """Non-geometric commercial metadata for one Stage 1 piece."""

    id: str
    index: int
    material: str

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValueError("piece id must be a nonempty string")
        if type(self.index) is not int or self.index < 0:
            raise ValueError("piece index must be a nonnegative integer")
        if not self.material or not isinstance(self.material, str):
            raise ValueError("piece material must be a nonempty string")


@dataclass(frozen=True, slots=True)
class SemanticGripRequest:
    rgba: np.ndarray
    pieces: tuple[PieceDescriptor, ...]
    product_id: str
    schema_version: int = 1
    instruction_version: str = "hold-discovery-anchor-grid-v1"
    prompt_id: str = SEMANTIC_PROMPT_ID
    prompt_sha256: str = SEMANTIC_PROMPT_SHA256

    def __post_init__(self) -> None:
        if not isinstance(self.rgba, np.ndarray) or self.rgba.dtype != np.uint8 or self.rgba.ndim != 3 or self.rgba.shape[2] != 4:
            raise ValueError("semantic request pixels must be an RGBA uint8 raster")
        if (
            type(self.schema_version) is not int
            or self.schema_version != 1
            or self.instruction_version != "hold-discovery-anchor-grid-v1"
            or self.prompt_id != SEMANTIC_PROMPT_ID
            or self.prompt_sha256 != SEMANTIC_PROMPT_SHA256
        ):
            raise ValueError("unsupported semantic request schema/instruction version")
        if not self.product_id or not self.pieces:
            raise ValueError("semantic request requires commercial identity and pieces")
        indexes = tuple(piece.index for piece in self.pieces)
        if indexes != tuple(range(len(self.pieces))):
            raise ValueError("piece indexes must be contiguous and ordered")
        object.__setattr__(self, "rgba", _frozen_array(self.rgba))

    @property
    def pixel_sha256(self) -> str:
        return sha256(self.rgba.tobytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class CoarseHoldHint:
    hint_key: str
    piece_index: int
    grip_type: GripType
    visual_mode: VisualMode
    anchor: tuple[int, int]

    def __post_init__(self) -> None:
        if not isinstance(self.hint_key, str) or not _HINT_KEY.fullmatch(self.hint_key):
            raise ValueError("hint key must be generic grip-NNN")
        if type(self.piece_index) is not int or self.piece_index < 0:
            raise ValueError("hint piece index must be a nonnegative integer")
        if self.grip_type not in {"pocket", "jug", "sloper"}:
            raise ValueError("unsupported grip type")
        if self.visual_mode not in {"aperture", "surface"}:
            raise ValueError("unsupported visual mode")
        if (self.grip_type == "pocket") != (self.visual_mode == "aperture"):
            raise ValueError("pockets must be apertures and jugs/slopers must be surfaces")
        if (
            not isinstance(self.anchor, tuple)
            or len(self.anchor) != 2
            or any(type(value) is not int for value in self.anchor)
            or not (0 <= self.anchor[0] < 20 and 0 <= self.anchor[1] < 8)
        ):
            raise ValueError("hint anchor must be one integer cell on the 20x8 grid")

    def as_document(self) -> dict[str, object]:
        return {
            "anchor": list(self.anchor),
            "gripType": self.grip_type,
            "hintKey": self.hint_key,
            "pieceIndex": self.piece_index,
            "visualMode": self.visual_mode,
        }


@dataclass(frozen=True, slots=True)
class SemanticHoldInventory:
    hints: tuple[CoarseHoldHint, ...]
    grid_width: int = 20
    grid_height: int = 8

    def __post_init__(self) -> None:
        if (self.grid_width, self.grid_height) != (20, 8):
            raise ValueError("semantic inventory grid must be exactly 20x8")
        if not self.hints:
            raise ValueError("semantic inventory must contain at least one hint")
        keys = [hint.hint_key for hint in self.hints]
        cells = [(hint.piece_index, *hint.anchor) for hint in self.hints]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate semantic hint key")
        if len(cells) != len(set(cells)):
            raise ValueError("duplicate semantic anchor cell")


@dataclass(frozen=True, slots=True)
class SemanticGripResponse:
    inventory: SemanticHoldInventory
    schema_version: int
    instruction_version: str
    input_pixel_sha256: str
    provider_id: str
    model_id: str
    prompt_id: str
    prompt_sha256: str
    raw_bytes: bytes
    response_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.instruction_version != "hold-discovery-anchor-grid-v1":
            raise ValueError("unsupported semantic response schema/instruction version")
        if self.prompt_id != SEMANTIC_PROMPT_ID or self.prompt_sha256 != SEMANTIC_PROMPT_SHA256:
            raise ValueError("semantic response prompt identity mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", self.input_pixel_sha256):
            raise ValueError("semantic response input pixel identity is invalid")
        for name, value in (("providerId", self.provider_id), ("modelId", self.model_id)):
            if not isinstance(value, str) or len(value) > 64 or not _PROVIDER_IDENTIFIER.fullmatch(value):
                raise ValueError(f"semantic response {name} is not a safe generic identifier")
        if not isinstance(self.raw_bytes, bytes):
            raise ValueError("semantic response raw bytes must be immutable bytes")
        if not re.fullmatch(r"[0-9a-f]{64}", self.response_sha256):
            raise ValueError("semantic response byte identity is invalid")


class SemanticGripProvider(Protocol):
    def propose(self, request: SemanticGripRequest) -> SemanticGripResponse: ...


def parse_semantic_grip_response(raw_bytes: bytes, *, piece_count: int) -> SemanticGripResponse:
    """Strictly parse a provider capture and reject covert geometry fields."""
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"nonstandard JSON constant: {value}")

    try:
        root = json.loads(
            raw_bytes.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("semantic provider response is not valid JSON") from error
    if not isinstance(root, dict) or set(root) != _ROOT_FIELDS:
        raise ValueError("semantic provider response has unknown or missing fields")
    for field in ("schemaVersion", "gridWidth", "gridHeight"):
        if type(root[field]) is not int:
            raise ValueError(f"semantic response {field} must be an integer")
    if root["schemaVersion"] != 1 or root["instructionVersion"] != "hold-discovery-anchor-grid-v1":
        raise ValueError("unsupported semantic response schema/instruction version")
    if (root["gridWidth"], root["gridHeight"]) != (20, 8):
        raise ValueError("semantic response grid must be exactly 20x8")
    for field in ("providerId", "modelId"):
        value = root[field]
        if not isinstance(value, str) or len(value) > 64 or not _PROVIDER_IDENTIFIER.fullmatch(value):
            raise ValueError(f"semantic response {field} is not a safe generic identifier")
    if root["promptId"] != SEMANTIC_PROMPT_ID or root["promptSha256"] != SEMANTIC_PROMPT_SHA256:
        raise ValueError("semantic response prompt identity mismatch")
    if not isinstance(root["inputPixelSha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", root["inputPixelSha256"]):
        raise ValueError("semantic response input pixel identity is invalid")
    raw_hints = root["hints"]
    if not isinstance(raw_hints, list):
        raise ValueError("semantic response hints must be an array")
    hints: list[CoarseHoldHint] = []
    for index, value in enumerate(raw_hints):
        if not isinstance(value, dict) or set(value) != _HINT_FIELDS:
            raise ValueError(f"semantic hint {index} has unknown, missing, or covert geometry fields")
        anchor = value["anchor"]
        if not isinstance(anchor, list) or len(anchor) != 2:
            raise ValueError(f"semantic hint {index} anchor must be a two-item array")
        if type(value["pieceIndex"]) is not int:
            raise ValueError(f"semantic hint {index} pieceIndex must be an integer")
        if any(type(item) is not int for item in anchor):
            raise ValueError(f"semantic hint {index} anchor must use integer cells")
        hint = CoarseHoldHint(
            hint_key=value["hintKey"],
            piece_index=value["pieceIndex"],
            grip_type=value["gripType"],
            visual_mode=value["visualMode"],
            anchor=tuple(anchor),
        )
        if hint.piece_index >= piece_count:
            raise ValueError("semantic hint references an unavailable piece")
        hints.append(hint)
    inventory = SemanticHoldInventory(tuple(hints), root["gridWidth"], root["gridHeight"])
    return SemanticGripResponse(
        inventory=inventory,
        schema_version=1,
        instruction_version=root["instructionVersion"],
        input_pixel_sha256=root["inputPixelSha256"],
        provider_id=root["providerId"],
        model_id=root["modelId"],
        prompt_id=root["promptId"],
        prompt_sha256=root["promptSha256"],
        raw_bytes=bytes(raw_bytes),
        response_sha256=sha256(raw_bytes).hexdigest(),
    )


def validate_semantic_grip_response(
    response: object, *, piece_count: int,
) -> SemanticGripResponse:
    """Re-parse and bind arbitrary provider output to its typed representation."""
    if type(response) is not SemanticGripResponse:
        raise ValueError("semantic provider returned an unsupported response object")
    parsed = parse_semantic_grip_response(response.raw_bytes, piece_count=piece_count)
    if parsed != response:
        raise ValueError("semantic provider typed response does not match its validated raw bytes")
    return parsed


class CapturedSemanticGripProvider:
    """Offline byte replay of the reviewed anchor-only Beastmaker response."""

    def __init__(self, raw_bytes: bytes | None = None) -> None:
        packaged = raw_bytes is None
        if raw_bytes is None:
            raw_bytes = resources.files("hangboard_vectorizer.evidence").joinpath(
                "beastmaker-stage2-coarse-proposals.json"
            ).read_bytes()
        self.__raw_bytes = bytes(raw_bytes)
        if packaged and sha256(self.__raw_bytes).hexdigest() != BEASTMAKER_STAGE2_CAPTURE_SHA256:
            raise ValueError("captured semantic response byte identity mismatch")

    def propose(self, request: SemanticGripRequest) -> SemanticGripResponse:
        response = parse_semantic_grip_response(self.__raw_bytes, piece_count=len(request.pieces))
        if response.input_pixel_sha256 != request.pixel_sha256:
            raise ValueError("captured semantic response input pixel identity mismatch")
        return response
