from __future__ import annotations

import json
from pathlib import Path

import pytest

import board_package
from fake_github_client import FakeGitHubClient
from github_client import TreeEntry
from github_board_store import GitHubBoardStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _package_files(slug: str) -> dict[str, bytes]:
    root = REPOSITORY_ROOT / "Hangboards" / slug
    return {
        f"Hangboards/{slug}/{path.relative_to(root).as_posix()}": path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_github_store_opens_and_saves_native_v3_contact_documents() -> None:
    client = FakeGitHubClient({"main": _package_files("lattice-mini-bar")})
    store = GitHubBoardStore(client)
    try:
        listings = store.discover_packages("token", "main")
        assert [(item.board_id, item.editor_available) for item in listings] == [
            ("lattice.mini-bar", True)
        ]
        opened = store.open_presentation(
            "token", "main", "lattice.mini-bar", "edge-10"
        )
        document = board_package.editor_document(opened, "edge-10")
        document["contacts"][0]["name"] += " reviewed"
        document["regions"][0]["displayPath"] = "M 5 5 L 25 5 L 25 25 L 5 25 Z"
        document["regions"][0].pop("shapeConstraint", None)

        saved, commit = store.save_board_editor_document(
            "token", "main", "lattice.mini-bar", document
        )

        assert commit
        assert saved.board["schemaVersion"] == 3
        stored = json.loads(
            client.file_bytes(
                "main", "Hangboards/lattice-mini-bar/board.json"
            )
        )
        assert stored["contacts"][0]["name"].endswith(" reviewed")
        assert "holds" not in stored
        assert "holdID" not in json.dumps(stored)
    finally:
        store.close()


def test_github_store_lists_models_as_read_only_without_compatibility() -> None:
    client = FakeGitHubClient({"main": _package_files("yy-baguette-evo")})
    store = GitHubBoardStore(client)
    try:
        listing = store.discover_packages("token", "main")[0]
        assert listing.board_id == "yy.baguette-evo"
        assert listing.editor_available is False
        with pytest.raises(board_package.BoardEditorUnavailableError):
            store.open_package("token", "main", listing.board_id)
    finally:
        store.close()


def test_github_store_rejects_schema_v2_catalog_entries() -> None:
    files = _package_files("lattice-mini-bar")
    board_path = "Hangboards/lattice-mini-bar/board.json"
    board = json.loads(files[board_path])
    board["schemaVersion"] = 2
    files[board_path] = (json.dumps(board) + "\n").encode()
    store = GitHubBoardStore(FakeGitHubClient({"main": files}))
    try:
        with pytest.raises(board_package.BoardPackageError, match="schemaVersion must be 3"):
            store.discover_packages("token", "main")
    finally:
        store.close()


def test_github_store_reports_conflict_instead_of_overwriting_newer_board() -> None:
    client = FakeGitHubClient({"main": _package_files("lattice-mini-bar")})
    store = GitHubBoardStore(client)
    try:
        opened = store.open_package("token", "main", "lattice.mini-bar")
        document = board_package.editor_document(opened)
        document["contacts"][0]["name"] += " reviewed"
        board_path = "Hangboards/lattice-mini-bar/board.json"
        concurrent = json.loads(client.file_bytes("main", board_path))
        concurrent["contacts"][0]["name"] += " concurrent"
        client.put_file(
            "token", board_path, "main", (json.dumps(concurrent) + "\n").encode(),
            "Concurrent update", opened.board_json_sha,
        )

        with pytest.raises(board_package.BoardSaveConflictError, match="file changed"):
            store.save_board_editor_document(
                "token", "main", "lattice.mini-bar", document
            )
    finally:
        store.close()


def test_github_store_deletes_a_presentation_and_its_unshared_asset_atomically() -> None:
    client = FakeGitHubClient({"main": _package_files("lattice-mini-bar")})
    store = GitHubBoardStore(client)
    try:
        deleted, commit = store.delete_board_presentation(
            "token", "main", "lattice.mini-bar", "mini-pinch"
        )

        assert commit
        assert "mini-pinch" not in {item.id for item in deleted.presentations}
        paths = {entry.path for entry in client.get_tree("token", "main") if isinstance(entry, TreeEntry)}
        assert "Hangboards/lattice-mini-bar/assets/mini-pinch.png" not in paths
        stored = json.loads(client.file_bytes(
            "main", "Hangboards/lattice-mini-bar/board.json"
        ))
        assert "mini-pinch" not in {item["id"] for item in stored["presentations"]}
    finally:
        store.close()
