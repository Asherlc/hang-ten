from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

from fake_github_client import FakeGitHubClient
from github_client import GitHubConflictError


def test_branch_heads_and_immutable_blob_objects_follow_a_successful_write() -> None:
    client = FakeGitHubClient({"main": {"Hangboards/fixture/board.json": b"before"}})
    old_blob_sha = next(
        entry.sha
        for entry in client.get_tree("token", "main")
        if entry.path == "Hangboards/fixture/board.json"
    )

    commit_sha = client.put_file(
        "token",
        "Hangboards/fixture/board.json",
        "main",
        b"after",
        "Update fixture.board",
        old_blob_sha,
    )

    assert client.get_branch_head_sha("token", "main") == commit_sha
    client.create_branch("token", "review", commit_sha)
    assert client.file_bytes("review", "Hangboards/fixture/board.json") == b"after"
    assert client.get_blob("token", old_blob_sha) == b"before"
    with pytest.raises(GitHubConflictError, match="file changed"):
        client.put_file(
            "token",
            "Hangboards/fixture/board.json",
            "main",
            b"stale",
            "Update fixture.board",
            old_blob_sha,
        )


def test_remaining_public_client_methods_are_deterministic_and_recorded() -> None:
    client = FakeGitHubClient(
        {"main": {"Hangboards/fixture/board.json": b"fixture"}},
        username="climber",
    )

    assert client.get_default_branch("token") == "main"
    assert client.list_branches("token") == ["main"]
    assert client.get_authenticated_user("token") == "climber"
    assert (
        client.create_pull_request("token", "Update", "main", "main", "Body")
        == "https://example.test/pull/1"
    )
    assert [call.method for call in client.calls] == [
        "get_default_branch",
        "list_branches",
        "get_authenticated_user",
        "create_pull_request",
    ]
