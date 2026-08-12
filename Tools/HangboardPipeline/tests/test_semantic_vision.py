from __future__ import annotations

from hashlib import sha256
import json

import pytest

from hangboard_vectorizer.semantic_vision import (
    COMPACT_SEMANTIC_SCHEMA_VERSION,
    ModelInvocation,
    SemanticVisionRequest,
    canonical_json_bytes,
    parse_compact_semantic_response,
)


def _wire() -> bytes:
    return canonical_json_bytes(
        {"h": [{"a": [3, 2], "k": "grip-001", "m": "aperture", "p": 0, "t": "pocket"}]}
    )


def test_compact_wire_response_is_canonical_and_typed() -> None:
    response = parse_compact_semantic_response(_wire())

    assert response.raw_bytes == _wire()
    assert response.response_sha256 == sha256(_wire()).hexdigest()
    assert response.hints[0].anchor == (3, 2)
    assert response.hints[0].grip_type == "pocket"


@pytest.mark.parametrize(
    "document",
    (
        {"h": [], "explanation": "looks round"},
        {"h": [{"a": [3.0, 2], "k": "grip-001", "m": "aperture", "p": 0, "t": "pocket"}]},
        {"h": [{"a": [3, 2], "box": [1, 2, 3, 4], "k": "grip-001", "m": "aperture", "p": 0, "t": "pocket"}]},
        {"h": [{"a": [3, 2], "k": "accepted-id", "m": "aperture", "p": 0, "t": "pocket"}]},
        {"h": [{"a": [20, 2], "k": "grip-001", "m": "aperture", "p": 0, "t": "pocket"}]},
    ),
)
def test_compact_wire_rejects_noncontract_fields_and_values(document: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_compact_semantic_response(canonical_json_bytes(document))


def test_request_binds_prompt_schema_provider_and_model_identity() -> None:
    request = SemanticVisionRequest(
        registered_pixel_sha256="a" * 64,
        prompt_bytes=b"compact prompt\n",
        provider_id="fake-provider",
        model_id="fake-model-v1",
        request_kind="full-board",
    )

    assert request.schema_version == COMPACT_SEMANTIC_SCHEMA_VERSION
    assert request.prompt_sha256 == sha256(b"compact prompt\n").hexdigest()
    assert json.loads(request.canonical_bytes) == {
        "modelId": "fake-model-v1",
        "promptSha256": request.prompt_sha256,
        "providerId": "fake-provider",
        "registeredPixelSha256": "a" * 64,
        "requestKind": "full-board",
        "schemaVersion": COMPACT_SEMANTIC_SCHEMA_VERSION,
    }


def test_model_invocation_keeps_missing_token_splits_missing() -> None:
    invocation = ModelInvocation(
        input_tokens=None,
        output_tokens=None,
        total_tokens=17,
        attempts=2,
        retries=1,
        wall_milliseconds=42,
        details={"providerRequestId": "req-1"},
    )

    assert invocation.input_tokens is None
    assert invocation.output_tokens is None
    assert invocation.total_tokens == 17
