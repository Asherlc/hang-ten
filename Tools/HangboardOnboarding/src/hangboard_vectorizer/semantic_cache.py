"""Fail-closed immutable storage for compact semantic vision evidence."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import base64
import json
import os
from pathlib import Path
import tempfile
from typing import Literal

from .semantic_vision import (
    COMPACT_SEMANTIC_SCHEMA_VERSION, ModelInvocation, ProviderInvocation,
    SemanticVisionProvider, SemanticVisionRequest, SemanticVisionResponse,
    canonical_json_bytes, parse_compact_semantic_response,
)


_ENVELOPE_VERSION = 1
_ENVELOPE_FIELDS = frozenset({"cacheVersion", "key", "response", "sourceInvocation"})
_KEY_FIELDS = frozenset(
    {"modelId", "promptSha256", "providerId", "registeredPixelSha256", "requestKind", "schemaVersion"}
)
_RESPONSE_FIELDS = frozenset({"bytesBase64", "sha256"})


class SemanticCacheError(ValueError):
    """A cache record cannot safely be used."""


class CacheOnlyMissError(SemanticCacheError):
    """Cache-only execution was requested without an exact immutable hit."""


class CacheCollisionError(SemanticCacheError):
    """A digest path contains an envelope for another semantic identity."""


@dataclass(frozen=True, slots=True)
class SemanticCacheKey:
    registered_pixel_sha256: str
    prompt_sha256: str
    schema_version: int
    provider_id: str
    model_id: str
    request_kind: str

    @classmethod
    def from_request(cls, request: SemanticVisionRequest) -> "SemanticCacheKey":
        return cls(
            registered_pixel_sha256=request.registered_pixel_sha256,
            prompt_sha256=request.prompt_sha256,
            schema_version=request.schema_version,
            provider_id=request.provider_id,
            model_id=request.model_id,
            request_kind=request.request_kind,
        )

    def as_document(self) -> dict[str, object]:
        return {
            "modelId": self.model_id,
            "promptSha256": self.prompt_sha256,
            "providerId": self.provider_id,
            "registeredPixelSha256": self.registered_pixel_sha256,
            "requestKind": self.request_kind,
            "schemaVersion": self.schema_version,
        }

    @property
    def digest(self) -> str:
        return sha256(canonical_json_bytes(self.as_document())).hexdigest()


@dataclass(frozen=True, slots=True)
class CacheTelemetry:
    hit: bool
    model_calls: Literal[0, 1]
    candidate_identity_bytes: bytes = b""


@dataclass(frozen=True, slots=True)
class SemanticCacheResult:
    response: SemanticVisionResponse
    cache: CacheTelemetry
    model_invocation: ModelInvocation | None
    source_invocation: ModelInvocation


@dataclass(frozen=True, slots=True)
class _CachedEnvelope:
    response: SemanticVisionResponse
    source_invocation: ModelInvocation


class SemanticCache:
    """An append-only cache keyed by all semantic identity inputs."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def envelope_path(self, key: SemanticCacheKey) -> Path:
        return self.root / f"{key.digest}.json"

    def load(self, key: SemanticCacheKey) -> _CachedEnvelope | None:
        path = self.envelope_path(key)
        try:
            raw_envelope = path.read_bytes()
        except FileNotFoundError:
            return None
        try:
            document = _decode_strict_json(raw_envelope)
            if not isinstance(document, dict) or set(document) != _ENVELOPE_FIELDS:
                raise SemanticCacheError("cache envelope has unknown or missing fields")
            if document["cacheVersion"] != _ENVELOPE_VERSION:
                raise SemanticCacheError("cache envelope schema is stale")
            if document["key"] != key.as_document():
                raise CacheCollisionError("cache envelope key collision")
            if not isinstance(document["response"], dict) or set(document["response"]) != _RESPONSE_FIELDS:
                raise SemanticCacheError("cache response envelope is invalid")
            encoded = document["response"]["bytesBase64"]
            claimed_hash = document["response"]["sha256"]
            if not isinstance(encoded, str) or not isinstance(claimed_hash, str):
                raise SemanticCacheError("cache response evidence is invalid")
            response_bytes = base64.b64decode(encoded.encode("ascii"), validate=True)
            if sha256(response_bytes).hexdigest() != claimed_hash:
                raise SemanticCacheError("cache response hash does not match evidence")
            response = parse_compact_semantic_response(response_bytes)
            if response.response_sha256 != claimed_hash:
                raise SemanticCacheError("cache response hash revalidation failed")
            invocation = _invocation_from_document(document["sourceInvocation"])
            canonical = canonical_json_bytes(_envelope_document(key, response, invocation))
            if canonical != raw_envelope:
                raise SemanticCacheError("cache envelope is not canonical")
            return _CachedEnvelope(response=response, source_invocation=invocation)
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError) as error:
            if isinstance(error, SemanticCacheError):
                raise
            raise SemanticCacheError("cache envelope is corrupt") from error

    def store(
        self,
        key: SemanticCacheKey,
        response: SemanticVisionResponse,
        invocation: ModelInvocation,
    ) -> _CachedEnvelope:
        validated = parse_compact_semantic_response(response.raw_bytes)
        if validated != response:
            raise SemanticCacheError("provider response does not match compact wire evidence")
        envelope = canonical_json_bytes(_envelope_document(key, response, invocation))
        path = self.envelope_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = self.load(key)
            if existing is None or existing.response.raw_bytes != response.raw_bytes:
                raise CacheCollisionError("cache key already has different response evidence")
            return existing

        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                existing = self.load(key)
                if existing is None or existing.response.raw_bytes != response.raw_bytes:
                    raise CacheCollisionError("cache key raced with different response evidence")
                return existing
        finally:
            temporary_path.unlink(missing_ok=True)
        return _CachedEnvelope(response=response, source_invocation=invocation)


def invoke_with_semantic_cache(
    cache: SemanticCache,
    request: SemanticVisionRequest,
    provider: SemanticVisionProvider,
    *,
    cache_only: bool = False,
) -> SemanticCacheResult:
    """Fetch an exact evidence replay or invoke once and atomically publish it."""
    key = SemanticCacheKey.from_request(request)
    cached = cache.load(key)
    if cached is not None:
        return SemanticCacheResult(
            response=cached.response,
            cache=CacheTelemetry(hit=True, model_calls=0),
            model_invocation=None,
            source_invocation=cached.source_invocation,
        )
    if cache_only:
        raise CacheOnlyMissError("cache-only semantic request has no exact hit")
    result = provider.invoke(request)
    if type(result) is not ProviderInvocation:
        raise ValueError("semantic provider returned an unsupported invocation")
    stored = cache.store(key, result.response, result.invocation)
    return SemanticCacheResult(
        response=stored.response,
        cache=CacheTelemetry(hit=False, model_calls=1),
        model_invocation=result.invocation,
        source_invocation=stored.source_invocation,
    )


def _envelope_document(
    key: SemanticCacheKey,
    response: SemanticVisionResponse,
    invocation: ModelInvocation,
) -> dict[str, object]:
    return {
        "cacheVersion": _ENVELOPE_VERSION,
        "key": key.as_document(),
        "response": {
            "bytesBase64": base64.b64encode(response.raw_bytes).decode("ascii"),
            "sha256": response.response_sha256,
        },
        "sourceInvocation": invocation.as_document(),
    }


def _decode_strict_json(raw: bytes) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, value in pairs:
            if name in result:
                raise SemanticCacheError("cache envelope has duplicate keys")
            result[name] = value
        return result

    def reject_constant(value: str) -> object:
        raise SemanticCacheError(f"cache envelope has nonstandard JSON constant: {value}")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates, parse_constant=reject_constant)


def _invocation_from_document(document: object) -> ModelInvocation:
    expected = {"attempts", "details", "inputTokens", "outputTokens", "retries", "totalTokens", "wallMilliseconds"}
    if not isinstance(document, dict) or set(document) != expected:
        raise SemanticCacheError("cache invocation telemetry is invalid")
    try:
        return ModelInvocation(
            input_tokens=document["inputTokens"], output_tokens=document["outputTokens"],
            total_tokens=document["totalTokens"], attempts=document["attempts"],
            retries=document["retries"], wall_milliseconds=document["wallMilliseconds"],
            details=document["details"],
        )
    except ValueError as error:
        raise SemanticCacheError("cache invocation telemetry is invalid") from error
