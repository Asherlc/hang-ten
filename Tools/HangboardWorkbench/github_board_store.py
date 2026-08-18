"""GitHub-backed board package storage."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import board_package
from board_geometry import NormalizedFrame, union_normalized_frames
from github_client import GitHubConflictError, GitHubNotFoundError, TreeEntry

_BOARD_LIBRARY_PATH = "Hangboards"


class _GitHubBoardClient(Protocol):
    def get_tree(self, token: str, branch: str) -> tuple[TreeEntry, ...]: ...

    def get_blob(self, token: str, sha: str) -> bytes: ...

    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class GitHubBoardPackage:
    slug: str
    board: dict[str, Any]
    image_width: int
    image_height: int
    board_json_sha: str

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def hold_ids(self) -> tuple[str, ...]:
        return tuple(hold["id"] for hold in self.board["holds"])

    def hold_frame(self, hold_id: str) -> NormalizedFrame:
        hold = next(
            (
                candidate
                for candidate in self.board["holds"]
                if candidate["id"] == hold_id
            ),
            None,
        )
        if hold is None:
            raise board_package.BoardPackageError("hold is not available")
        try:
            return union_normalized_frames(
                NormalizedFrame.from_json(piece["frame"], f"hold {hold_id}.geometry")
                for piece in hold["geometry"]
            )
        except (board_package.GeometryError, KeyError, TypeError) as error:
            raise board_package.BoardPackageError(
                f"hold {hold_id} has invalid geometry"
            ) from error


def discover_packages(
    client: _GitHubBoardClient, token: str, branch: str
) -> tuple[GitHubBoardPackage, ...]:
    """List completed remote board packages with header-only PNG validation."""
    groups = _package_groups(client.get_tree(token, branch))
    packages = [
        _load_package_from_entries(
            client, token, slug, entries, inspect_png_header_only=True
        )
        for slug, entries in groups.items()
        if _is_completed(entries)
    ]
    for slug, entries in groups.items():
        if _is_completed(entries):
            continue
        if _is_primary_only_draft(entries):
            _load_draft_image_header(client, token, entries)
            continue
        _raise_for_incomplete_layout(slug, entries)
    board_ids: set[str] = set()
    for package in packages:
        if package.board_id in board_ids:
            raise board_package.BoardPackageError(
                f"duplicate board ID: {package.board_id}"
            )
        board_ids.add(package.board_id)
    return tuple(sorted(packages, key=_package_sort_key))


def open_package(
    client: _GitHubBoardClient, token: str, branch: str, board_id: str
) -> GitHubBoardPackage:
    """Open one board by ID after fully decoding the current primary PNG."""
    board_id = board_package._identifier(board_id, "board ID")
    package = _load_by_board_id(client, token, branch, board_id)
    return package


def primary_image_bytes(
    client: _GitHubBoardClient, token: str, branch: str, board_id: str
) -> bytes:
    """Return an authenticated board's fully validated primary image bytes."""
    board_id = board_package._identifier(board_id, "board ID")
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    package, image = _load_slug_with_image(client, token, branch, selected.slug)
    if package.board_id == board_id:
        return image
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    package, image = _load_slug_with_image(client, token, branch, selected.slug)
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return image


def save_editor_document(
    client: _GitHubBoardClient,
    token: str,
    branch: str,
    slug: str,
    document: Mapping[str, Any],
    *,
    expected_board_id: str | None = None,
) -> tuple[GitHubBoardPackage, str]:
    """Validate and conditionally commit an editor document to its live package."""
    slug = board_package._slug(slug)
    live = _load_slug(client, token, branch, slug, inspect_png_header_only=False)
    if expected_board_id is not None:
        expected_board_id = board_package._identifier(expected_board_id, "board ID")
        if live.board_id != expected_board_id:
            raise board_package.BoardSaveConflictError(
                "board identity changed; reload and try again"
            )
    width, height = live.image_width, live.image_height
    parsed_regions = board_package._validate_editor_document(document, width, height)

    pieces_by_hold: dict[str, list[tuple[int, str, Any]]] = {}
    for hold_id, piece_index, kind, path in parsed_regions.values():
        pieces_by_hold.setdefault(hold_id, []).append((piece_index, kind, path))
    for pieces in pieces_by_hold.values():
        pieces.sort(key=lambda item: item[0])

    current_holds = {hold["id"]: hold for hold in live.board["holds"]}
    current_paths = board_package._current_display_paths(
        pieces_by_hold, current_holds, width, height
    )
    if not board_package._editor_document_is_dirty(
        pieces_by_hold, current_holds, current_paths
    ):
        return live, live.board_json_sha

    board = board_package._apply_editor_document(
        live.board,
        board_package._EditorPiecesByHold(pieces_by_hold, current_paths),
        width,
        height,
    )
    board_package._validate_board(board, width, height)
    content = (json.dumps(board, indent=2) + "\n").encode("utf-8")
    try:
        commit_sha = client.put_file(
            token,
            f"{_BOARD_LIBRARY_PATH}/{slug}/board.json",
            branch,
            content,
            message=f"Update {live.board_id}",
            sha=live.board_json_sha,
        )
    except GitHubConflictError as error:
        raise board_package.BoardSaveConflictError(str(error)) from error
    return GitHubBoardPackage(
        slug, board, width, height, _git_blob_sha(content)
    ), commit_sha


def _load_slug(
    client: _GitHubBoardClient,
    token: str,
    branch: str,
    slug: str,
    *,
    inspect_png_header_only: bool,
) -> GitHubBoardPackage:
    groups = _package_groups(client.get_tree(token, branch))
    entries = groups.get(slug)
    if entries is None:
        raise board_package.BoardPackageError("board package is not available")
    if not _is_completed(entries):
        _raise_for_incomplete_layout(slug, entries)
    return _load_package_from_entries(
        client, token, slug, entries, inspect_png_header_only=inspect_png_header_only
    )


def _load_by_board_id(
    client: _GitHubBoardClient, token: str, branch: str, board_id: str
) -> GitHubBoardPackage:
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    package = _load_slug(
        client, token, branch, selected.slug, inspect_png_header_only=False
    )
    if package.board_id == board_id:
        return package
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    package = _load_slug(
        client, token, branch, selected.slug, inspect_png_header_only=False
    )
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return package


def _selected_package(
    packages: tuple[GitHubBoardPackage, ...], board_id: str
) -> GitHubBoardPackage:
    selected = next(
        (package for package in packages if package.board_id == board_id), None
    )
    if selected is None:
        raise board_package.BoardNotAvailableError("board is not available")
    return selected


def _load_slug_with_image(
    client: _GitHubBoardClient, token: str, branch: str, slug: str
) -> tuple[GitHubBoardPackage, bytes]:
    groups = _package_groups(client.get_tree(token, branch))
    entries = groups.get(slug)
    if entries is None:
        raise board_package.BoardPackageError("board package is not available")
    if not _is_completed(entries):
        _raise_for_incomplete_layout(slug, entries)
    package, image = _load_package_from_entries(
        client, token, slug, entries, inspect_png_header_only=False, include_image=True
    )
    return package, image


def _load_package_from_entries(
    client: _GitHubBoardClient,
    token: str,
    slug: str,
    entries: Mapping[str, TreeEntry],
    *,
    inspect_png_header_only: bool,
    include_image: bool = False,
) -> GitHubBoardPackage | tuple[GitHubBoardPackage, bytes]:
    image_entry = entries["assets/primary.png"]
    image = _get_blob(client, token, image_entry, "package primary image")
    width, height = (
        board_package._png_header_dimensions_from_bytes(image[:33])
        if inspect_png_header_only
        else board_package._png_dimensions_from_bytes(image)
    )
    board_entry = entries["board.json"]
    board = _load_board_json(_get_blob(client, token, board_entry, "board.json"))
    board_package._validate_board(
        board, width, height, validate_geometry=not inspect_png_header_only
    )
    package = GitHubBoardPackage(slug, board, width, height, board_entry.sha)
    return (package, image) if include_image else package


def _package_groups(tree: tuple[TreeEntry, ...]) -> dict[str, dict[str, TreeEntry]]:
    groups: dict[str, dict[str, TreeEntry]] = {}
    root_entries: dict[str, TreeEntry] = {}
    for entry in tree:
        if not entry.path.startswith(f"{_BOARD_LIBRARY_PATH}/"):
            continue
        relative = entry.path.removeprefix(f"{_BOARD_LIBRARY_PATH}/")
        slug, separator, nested = relative.partition("/")
        if not separator:
            root_entries[slug] = entry
            continue
        groups.setdefault(slug, {})[nested] = entry
    for slug, entry in root_entries.items():
        if entry.type != "tree":
            raise board_package.BoardPackageError(
                "board library must contain only direct child directories"
            )
        groups.setdefault(slug, {})
    for slug in groups:
        board_package._slug(slug)
    return groups


def _is_completed(entries: Mapping[str, TreeEntry]) -> bool:
    return set(entries) == {"board.json", "assets", "assets/primary.png"} and (
        entries["board.json"].type == "blob"
        and entries["assets"].type == "tree"
        and entries["assets/primary.png"].type == "blob"
    )


def _is_primary_only_draft(entries: Mapping[str, TreeEntry]) -> bool:
    return set(entries) == {"assets", "assets/primary.png"} and (
        entries["assets"].type == "tree"
        and entries["assets/primary.png"].type == "blob"
    )


def _raise_for_incomplete_layout(slug: str, entries: Mapping[str, TreeEntry]) -> None:
    if set(entries) == {"board.json", "assets", "assets/primary.png"}:
        if (
            entries["assets"].type == "tree"
            and entries["assets/primary.png"].type != "blob"
        ):
            raise board_package.BoardPackageError("package primary image is missing")
        if entries["board.json"].type != "blob":
            raise board_package.BoardPackageError("board.json is missing")
    if "board.json" in entries:
        raise board_package.BoardPackageError(
            "board package must contain only board.json and assets/primary.png"
        )
    if set(entries) == {"assets"} and entries["assets"].type != "tree":
        raise board_package.BoardPackageError(
            f"{slug} draft assets must not be a symlink"
        )
    if (
        set(entries) == {"assets", "assets/primary.png"}
        and entries["assets"].type == "tree"
        and entries["assets/primary.png"].type != "blob"
    ):
        raise board_package.BoardPackageError(
            f"{slug} draft primary image must be regular"
        )
    raise board_package.BoardPackageError(
        f"{slug} must be a completed package or exact primary-only draft"
    )


def _load_draft_image_header(
    client: _GitHubBoardClient, token: str, entries: Mapping[str, TreeEntry]
) -> None:
    image = _get_blob(
        client, token, entries["assets/primary.png"], "package primary image"
    )
    board_package._png_header_dimensions_from_bytes(image[:33])


def _load_board_json(data: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise board_package.BoardPackageError("board.json is invalid JSON") from error
    if not isinstance(decoded, dict):
        raise board_package.BoardPackageError("board.json must be an object")
    return decoded


def _get_blob(
    client: _GitHubBoardClient, token: str, entry: TreeEntry, label: str
) -> bytes:
    try:
        return client.get_blob(token, entry.sha)
    except GitHubNotFoundError as error:
        if label == "board.json":
            raise board_package.BoardPackageError("board.json is missing") from error
        raise board_package.BoardPackageError(
            "package primary image is missing"
        ) from error


def _package_sort_key(
    package: GitHubBoardPackage,
) -> tuple[str, str, str, str, str, str]:
    return (
        package.board["manufacturer"].lower(),
        package.board["manufacturer"],
        package.board["name"].lower(),
        package.board["name"],
        package.board_id.lower(),
        package.board_id,
    )


def _git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
