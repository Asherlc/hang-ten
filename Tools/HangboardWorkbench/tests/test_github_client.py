from __future__ import annotations

import base64
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import github_client  # noqa: E402


@dataclass
class _Response:
    payload: object

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


@dataclass
class _RawResponse:
    data: bytes

    def __enter__(self) -> _RawResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.data


def test_client_emits_github_requests_and_decodes_all_endpoint_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = []
    timeouts = []
    blob = b"board image bytes"

    def fake_urlopen(request, *, timeout: float):
        requests.append(request)
        timeouts.append(timeout)
        path = request.full_url.removeprefix("https://example.test")
        responses = {
            "/repos/acme/boards": {"default_branch": "main"},
            "/repos/acme/boards/git/ref/heads/release%2F2026": {"object": {"sha": "head"}},
            "/repos/acme/boards/branches?per_page=100&page=1": [
                {"name": f"branch-{number}"} for number in range(100)
            ],
            "/repos/acme/boards/branches?per_page=100&page=2": [{"name": "main"}],
            "/repos/acme/boards/git/trees/release%2F2026?recursive=1": {
                "truncated": False,
                "tree": [{"path": "board.json", "type": "blob", "sha": "tree-sha"}],
            },
            "/repos/acme/boards/git/blobs/blob-sha": {
                "encoding": "base64",
                "content": base64.b64encode(blob).decode("ascii") + "\n",
            },
            "/repos/acme/boards/contents/nested/board%20file.json": {"commit": {"sha": "commit-sha"}},
            "/repos/acme/boards/contents/nested/new.json": {"commit": {"sha": "new-commit-sha"}},
            "/repos/acme/boards/pulls": {"html_url": "https://github.com/acme/boards/pull/1"},
            "/user": {"login": "climber"},
        }
        if request.get_method() == "POST" and path == "/repos/acme/boards/git/refs":
            return _Response({})
        return _Response(responses[path])

    monkeypatch.setattr(github_client.urllib.request, "urlopen", fake_urlopen)
    client = github_client.GitHubClient("acme", "boards", base_url="https://example.test")

    assert client.get_default_branch("token") == "main"
    assert client.get_branch_head_sha("token", "release/2026") == "head"
    assert client.list_branches("token") == [
        *(f"branch-{number}" for number in range(100)),
        "main",
    ]
    client.create_branch("token", "work/feature", "head")
    assert client.get_tree("token", "release/2026") == (
        github_client.TreeEntry("board.json", "blob", "tree-sha"),
    )
    assert client.get_blob("token", "blob-sha") == blob
    assert (
        client.put_file(
            "token", "nested/board file.json", "work/feature", b"{}", "Save board", "old-sha"
        )
        == "commit-sha"
    )
    assert (
        client.put_file(
            "token", "nested/new.json", "work/feature", b"{}", "Create board", None
        )
        == "new-commit-sha"
    )
    assert (
        client.create_pull_request("token", "Update", "work/feature", "main", "Body")
        == "https://github.com/acme/boards/pull/1"
    )
    assert client.get_authenticated_user("token") == "climber"

    by_path = {
        request.full_url.removeprefix("https://example.test"): request
        for request in requests
    }
    assert {request.full_url.removeprefix("https://example.test"): request.get_method() for request in requests} == {
        "/repos/acme/boards": "GET",
        "/repos/acme/boards/git/ref/heads/release%2F2026": "GET",
        "/repos/acme/boards/branches?per_page=100&page=1": "GET",
        "/repos/acme/boards/branches?per_page=100&page=2": "GET",
        "/repos/acme/boards/git/refs": "POST",
        "/repos/acme/boards/git/trees/release%2F2026?recursive=1": "GET",
        "/repos/acme/boards/git/blobs/blob-sha": "GET",
        "/repos/acme/boards/contents/nested/board%20file.json": "PUT",
        "/repos/acme/boards/contents/nested/new.json": "PUT",
        "/repos/acme/boards/pulls": "POST",
        "/user": "GET",
    }
    assert all(request.get_header("Authorization") == "Bearer token" for request in requests)
    assert all(request.get_header("Accept") == "application/vnd.github+json" for request in requests)
    assert all(request.get_header("X-github-api-version") == "2022-11-28" for request in requests)
    assert json.loads(by_path["/repos/acme/boards/git/refs"].data) == {
        "ref": "refs/heads/work/feature",
        "sha": "head",
    }
    assert json.loads(by_path["/repos/acme/boards/contents/nested/board%20file.json"].data) == {
        "message": "Save board",
        "content": "e30=",
        "branch": "work/feature",
        "sha": "old-sha",
    }
    assert json.loads(by_path["/repos/acme/boards/contents/nested/new.json"].data) == {
        "message": "Create board",
        "content": "e30=",
        "branch": "work/feature",
    }
    assert all(timeout == 30 for timeout in timeouts)


@pytest.mark.parametrize(
    ("status", "headers", "expected_error"),
    [
        (404, {}, github_client.GitHubNotFoundError),
        (409, {}, github_client.GitHubConflictError),
        (412, {}, github_client.GitHubConflictError),
        (401, {}, github_client.GitHubAuthError),
        (403, {}, github_client.GitHubForbiddenError),
        (403, {"X-RateLimit-Remaining": "0"}, github_client.GitHubRateLimitError),
    ],
)
def test_client_maps_http_errors_to_typed_errors(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    headers: dict[str, str],
    expected_error: type[Exception],
) -> None:
    def fake_urlopen(request, *, timeout: float):
        raise HTTPError(request.full_url, status, "failure", headers, io.BytesIO(b'{"message":"denied"}'))

    monkeypatch.setattr(github_client.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(expected_error, match="denied"):
        github_client.GitHubClient("acme", "boards", base_url="https://example.test").get_default_branch("secret")


def test_client_rejects_truncated_tree_and_malformed_json_as_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [_Response({"truncated": True, "tree": []}), _Response({"default_branch": 3}), _Response([])]
    )
    monkeypatch.setattr(github_client.urllib.request, "urlopen", lambda _request, *, timeout: next(responses))
    client = github_client.GitHubClient("acme", "boards", base_url="https://example.test")

    with pytest.raises(github_client.GitHubTransportError):
        client.get_tree("token", "main")
    with pytest.raises(github_client.GitHubTransportError):
        client.get_default_branch("token")
    with pytest.raises(github_client.GitHubTransportError):
        client.get_tree("token", "main")


def test_client_maps_malformed_json_and_network_failures_to_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        github_client.urllib.request,
        "urlopen",
        lambda _request, *, timeout: _RawResponse(b"{not valid JSON"),
    )
    client = github_client.GitHubClient("acme", "boards", base_url="https://example.test")

    with pytest.raises(github_client.GitHubTransportError, match="malformed JSON"):
        client.get_default_branch("token")

    for error in (URLError("offline"), TimeoutError("slow")):
        monkeypatch.setattr(
            github_client.urllib.request,
            "urlopen",
            lambda _request, *, timeout, error=error: (_ for _ in ()).throw(error),
        )
        with pytest.raises(github_client.GitHubTransportError, match="Unable to reach GitHub"):
            client.get_default_branch("token")


@pytest.mark.parametrize(
    "payload",
    [
        {"encoding": "utf-8", "content": "board"},
        {"encoding": "base64", "content": "%%%"},
    ],
)
def test_client_rejects_invalid_blob_encodings_and_data(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, str]
) -> None:
    monkeypatch.setattr(
        github_client.urllib.request,
        "urlopen",
        lambda _request, *, timeout: _Response(payload),
    )

    with pytest.raises(github_client.GitHubTransportError):
        github_client.GitHubClient("acme", "boards", base_url="https://example.test").get_blob(
            "token", "blob-sha"
        )


def test_client_redacts_the_access_token_from_http_error_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "ghp_super_secret"

    def fake_urlopen(request, *, timeout: float):
        raise HTTPError(
            request.full_url,
            401,
            "failure",
            {},
            io.BytesIO(f'{{"message":"credential {token} rejected"}}'.encode("utf-8")),
        )

    monkeypatch.setattr(github_client.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(github_client.GitHubAuthError) as captured:
        github_client.GitHubClient("acme", "boards", base_url="https://example.test").get_default_branch(token)

    error = captured.value
    assert token not in str(error)
    assert token not in repr(error)
    assert token not in " ".join(str(argument) for argument in error.args)
    assert "credential" in str(error)
    assert "rejected" in str(error)
