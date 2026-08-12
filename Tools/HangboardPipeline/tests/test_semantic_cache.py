from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from hangboard_vectorizer.semantic_cache import (
    CacheOnlyMissError,
    SemanticCache,
    SemanticCacheKey,
    invoke_with_semantic_cache,
)
from hangboard_vectorizer.semantic_vision import (
    ModelInvocation,
    ProviderInvocation,
    SemanticVisionRequest,
    canonical_json_bytes,
    parse_compact_semantic_response,
)


def _request() -> SemanticVisionRequest:
    return SemanticVisionRequest(
        registered_pixel_sha256="b" * 64,
        prompt_bytes=b"compact prompt\n",
        provider_id="fake-provider",
        model_id="fake-model-v1",
        request_kind="full-board",
    )


@dataclass
class FakeProvider:
    calls: int = 0

    def invoke(self, request: SemanticVisionRequest) -> ProviderInvocation:
        self.calls += 1
        response = parse_compact_semantic_response(
            canonical_json_bytes(
                {"h": [{"a": [3, 2], "k": "grip-001", "m": "aperture", "p": 0, "t": "pocket"}]}
            )
        )
        return ProviderInvocation(
            response=response,
            invocation=ModelInvocation(
                input_tokens=11,
                output_tokens=7,
                total_tokens=18,
                attempts=1,
                retries=0,
                wall_milliseconds=9,
            ),
        )


def test_cache_replay_skips_client_and_preserves_response_bytes(tmp_path: Path) -> None:
    request = _request()
    cache = SemanticCache(tmp_path / "semantic-cache")
    provider = FakeProvider()

    first = invoke_with_semantic_cache(cache, request, provider)
    second = invoke_with_semantic_cache(cache, request, provider)

    assert provider.calls == 1
    assert first.cache.hit is False
    assert second.cache.hit is True
    assert second.response.raw_bytes == first.response.raw_bytes
    assert second.model_invocation is None
    assert second.cache.candidate_identity_bytes == b""


def test_cache_only_miss_fails_without_invoking_provider(tmp_path: Path) -> None:
    provider = FakeProvider()
    with pytest.raises(CacheOnlyMissError):
        invoke_with_semantic_cache(
            SemanticCache(tmp_path / "semantic-cache"), _request(), provider, cache_only=True
        )
    assert provider.calls == 0


def test_corrupt_or_colliding_cache_envelopes_fail_closed(tmp_path: Path) -> None:
    request = _request()
    cache = SemanticCache(tmp_path / "semantic-cache")
    key = SemanticCacheKey.from_request(request)
    envelope_path = cache.envelope_path(key)
    envelope_path.parent.mkdir(parents=True)
    envelope_path.write_bytes(b"not json")

    with pytest.raises(ValueError, match="cache"):
        invoke_with_semantic_cache(cache, request, FakeProvider(), cache_only=True)
