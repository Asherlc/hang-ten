"""GitHub-backed board package storage."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Mapping
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

import board_package
from board_geometry import NormalizedFrame, union_normalized_frames
from github_client import GitHubConflictError, GitHubNotFoundError, TreeEntry

_BOARD_LIBRARY_PATH = "Hangboards"
_MAX_CONCURRENT_PACKAGE_LOADS = 4
_MAX_CACHED_TREES = 16
_MAX_CACHED_TREE_ENTRIES = 50_000
_MAX_CACHED_CATALOGS = 16
_MAX_CACHED_BLOBS = 128
_MAX_CACHED_BLOB_BYTES = 32 * 1024 * 1024


class _GitHubSnapshotClient(Protocol):
    def get_tree(self, token: str, branch: str) -> tuple[TreeEntry, ...]: ...

    def get_blob(self, token: str, sha: str) -> bytes: ...


class _GitHubMutationClient(_GitHubSnapshotClient, Protocol):
    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str: ...


class _GitHubBoardClient(_GitHubMutationClient, Protocol):
    def get_branch_head_sha(self, token: str, branch: str) -> str: ...


class GitHubBoardStore:
    """Bounded, credential-partitioned cache for immutable GitHub snapshots."""

    def __init__(
        self,
        client: _GitHubBoardClient,
        *,
        max_cached_trees: int = _MAX_CACHED_TREES,
        max_cached_tree_entries: int = _MAX_CACHED_TREE_ENTRIES,
        max_cached_blobs: int = _MAX_CACHED_BLOBS,
        max_cached_blob_bytes: int = _MAX_CACHED_BLOB_BYTES,
    ) -> None:
        if (
            min(
                max_cached_trees,
                max_cached_tree_entries,
                max_cached_blobs,
                max_cached_blob_bytes,
            )
            < 1
        ):
            raise ValueError("GitHub cache limits must be positive")
        self._client = client
        self._max_cached_trees = max_cached_trees
        self._max_cached_tree_entries = max_cached_tree_entries
        self._max_cached_blobs = max_cached_blobs
        self._max_cached_blob_bytes = max_cached_blob_bytes
        self._trees: OrderedDict[tuple[bytes, str], tuple[TreeEntry, ...]] = (
            OrderedDict()
        )
        self._catalogs: OrderedDict[
            tuple[bytes, str], tuple[GitHubBoardPackage, ...]
        ] = OrderedDict()
        self._blobs: OrderedDict[tuple[bytes, str], bytes] = OrderedDict()
        self._blob_bytes = 0
        self._lock = threading.RLock()
        self._request_slots = threading.BoundedSemaphore(
            _MAX_CONCURRENT_PACKAGE_LOADS
        )
        self._executor = ThreadPoolExecutor(
            max_workers=_MAX_CONCURRENT_PACKAGE_LOADS,
            thread_name_prefix="hangboard-github-load",
        )
        self._tree_flights: dict[tuple[bytes, str], Future[tuple[TreeEntry, ...]]] = {}
        self._catalog_flights: dict[
            tuple[bytes, str], Future[tuple[GitHubBoardPackage, ...]]
        ] = {}
        self._blob_flights: dict[tuple[bytes, str], Future[bytes]] = {}

    def discover_packages(
        self, token: str, branch: str
    ) -> tuple[GitHubBoardPackage, ...]:
        snapshot = self._snapshot(token, branch, cache_blobs=False)
        return _copy_packages(self._catalog(snapshot, token, branch))

    def open_package(
        self, token: str, branch: str, board_id: str
    ) -> GitHubBoardPackage:
        board_id = board_package._identifier(board_id, "board ID")
        snapshot = self._snapshot(token, branch, cache_blobs=False)
        selected = _selected_package(self._catalog(snapshot, token, branch), board_id)
        return _load_selected_package(
            snapshot.with_blob_cache(), token, branch, selected.slug, board_id
        )

    def primary_image_bytes(self, token: str, branch: str, board_id: str) -> bytes:
        board_id = board_package._identifier(board_id, "board ID")
        snapshot = self._snapshot(token, branch, cache_blobs=False)
        selected = _selected_package(self._catalog(snapshot, token, branch), board_id)
        package, image = _load_selected_package_with_image(
            snapshot.with_blob_cache(), token, branch, selected.slug, board_id
        )
        if package.board_id != board_id:
            raise board_package.BoardNotAvailableError("board is not available")
        return image

    def save_editor_document(
        self,
        token: str,
        branch: str,
        slug: str,
        document: Mapping[str, Any],
        *,
        expected_board_id: str | None = None,
    ) -> tuple[GitHubBoardPackage, str]:
        snapshot = self._snapshot(token, branch, cache_blobs=True)
        saved = save_editor_document(
            snapshot,
            token,
            branch,
            slug,
            document,
            expected_board_id=expected_board_id,
        )
        self._discard_credential_entries(_credential_key(token))
        return saved

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _snapshot(
        self, token: str, branch: str, *, cache_blobs: bool
    ) -> _CachedSnapshotClient:
        credential_key = _credential_key(token)
        head = self._call_bounded(self._client.get_branch_head_sha, token, branch)
        key = (credential_key, head)
        tree = self._tree(key, token, head)
        return _CachedSnapshotClient(
            self, token, credential_key, head, tree, cache_blobs
        )

    def _tree(
        self, key: tuple[bytes, str], token: str, head: str
    ) -> tuple[TreeEntry, ...]:
        with self._lock:
            tree = self._trees.get(key)
            if tree is not None:
                self._trees.move_to_end(key)
                return tree

        def load() -> tuple[TreeEntry, ...]:
            tree = self._call_bounded(self._client.get_tree, token, head)
            if len(tree) <= self._max_cached_tree_entries:
                with self._lock:
                    self._trees[key] = tree
                    self._trees.move_to_end(key)
                    while len(self._trees) > self._max_cached_trees:
                        self._trees.popitem(last=False)
            return tree

        return self._single_flight(self._tree_flights, key, load)

    def _catalog(
        self, snapshot: _CachedSnapshotClient, token: str, branch: str
    ) -> tuple[GitHubBoardPackage, ...]:
        key = (snapshot.credential_key, snapshot.commit_sha)
        with self._lock:
            catalog = self._catalogs.get(key)
            if catalog is not None:
                self._catalogs.move_to_end(key)
                return catalog

        def load() -> tuple[GitHubBoardPackage, ...]:
            catalog = discover_packages(snapshot, token, branch, executor=self._executor)
            if len(catalog) <= self._max_cached_tree_entries:
                with self._lock:
                    self._catalogs[key] = catalog
                    self._catalogs.move_to_end(key)
                    while len(self._catalogs) > _MAX_CACHED_CATALOGS:
                        self._catalogs.popitem(last=False)
            return catalog

        return self._single_flight(self._catalog_flights, key, load)

    def _blob(
        self, token: str, credential_key: bytes, sha: str, *, cache: bool
    ) -> bytes:
        key = (credential_key, sha)
        if cache:
            with self._lock:
                blob = self._blobs.get(key)
                if blob is not None:
                    self._blobs.move_to_end(key)
                    return blob

        def load() -> bytes:
            blob = self._call_bounded(self._client.get_blob, token, sha)
            if not cache or len(blob) > self._max_cached_blob_bytes:
                return blob
            with self._lock:
                previous = self._blobs.pop(key, None)
                if previous is not None:
                    self._blob_bytes -= len(previous)
                self._blobs[key] = blob
                self._blob_bytes += len(blob)
                while (
                    len(self._blobs) > self._max_cached_blobs
                    or self._blob_bytes > self._max_cached_blob_bytes
                ):
                    _discarded_key, discarded = self._blobs.popitem(last=False)
                    self._blob_bytes -= len(discarded)
            return blob

        return self._single_flight(self._blob_flights, key, load)

    def _call_bounded(self, operation, *args):
        with self._request_slots:
            return operation(*args)

    def _single_flight(self, flights, key, load):
        with self._lock:
            future = flights.get(key)
            if future is None:
                future = Future()
                flights[key] = future
                owner = True
            else:
                owner = False
        if not owner:
            return future.result()
        try:
            result = load()
        except BaseException as error:
            future.set_exception(error)
            raise
        else:
            future.set_result(result)
            return result
        finally:
            with self._lock:
                flights.pop(key, None)

    def _discard_credential_entries(self, credential_key: bytes) -> None:
        with self._lock:
            self._trees = OrderedDict(
                (key, tree)
                for key, tree in self._trees.items()
                if key[0] != credential_key
            )
            self._catalogs = OrderedDict(
                (key, catalog)
                for key, catalog in self._catalogs.items()
                if key[0] != credential_key
            )
            retained_blobs: OrderedDict[tuple[bytes, str], bytes] = OrderedDict()
            self._blob_bytes = 0
            for key, blob in self._blobs.items():
                if key[0] == credential_key:
                    continue
                retained_blobs[key] = blob
                self._blob_bytes += len(blob)
            self._blobs = retained_blobs


class _CachedSnapshotClient:
    """Presents one authenticated immutable tree to existing load helpers."""

    def __init__(
        self,
        store: GitHubBoardStore,
        token: str,
        credential_key: bytes,
        commit_sha: str,
        tree: tuple[TreeEntry, ...],
        cache_blobs: bool,
    ) -> None:
        self._store = store
        self._token = token
        self._credential_key = credential_key
        self._commit_sha = commit_sha
        self._tree = tree
        self._cache_blobs = cache_blobs

    @property
    def credential_key(self) -> bytes:
        return self._credential_key

    @property
    def commit_sha(self) -> str:
        return self._commit_sha

    def get_tree(self, token: str, branch: str) -> tuple[TreeEntry, ...]:
        self._require_token(token)
        return self._tree

    def get_blob(self, token: str, sha: str) -> bytes:
        self._require_token(token)
        return self._store._blob(
            token, self._credential_key, sha, cache=self._cache_blobs
        )

    def with_blob_cache(self) -> _CachedSnapshotClient:
        return _CachedSnapshotClient(
            self._store,
            self._token,
            self._credential_key,
            self._commit_sha,
            self._tree,
            True,
        )

    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str:
        self._require_token(token)
        return self._store._call_bounded(
            self._store._client.put_file,
            token,
            path,
            branch,
            content,
            message,
            sha,
        )

    def _require_token(self, token: str) -> None:
        if token != self._token:
            raise RuntimeError("GitHub snapshot credentials do not match")


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
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    *,
    executor: Executor | None = None,
) -> tuple[GitHubBoardPackage, ...]:
    """List completed remote board packages with header-only PNG validation."""
    groups = _package_groups(client.get_tree(token, branch))
    completed = [
        (slug, entries) for slug, entries in groups.items() if _is_completed(entries)
    ]
    if executor is None:
        with ThreadPoolExecutor(max_workers=_MAX_CONCURRENT_PACKAGE_LOADS) as pool:
            packages = _load_completed_packages(pool, client, token, completed)
    else:
        packages = _load_completed_packages(executor, client, token, completed)
    for slug, entries in groups.items():
        if _is_completed(entries):
            continue
        if _is_primary_only_draft(entries):
            _load_draft_image_header(client, token, entries)
            continue
        _raise_for_incomplete_layout(slug, entries)
    board_ids: set[str] = set()
    completed_packages: list[GitHubBoardPackage] = []
    for package in packages:
        if not isinstance(package, GitHubBoardPackage):
            raise TypeError("completed board package unexpectedly included image bytes")
        completed_packages.append(package)
        if package.board_id in board_ids:
            raise board_package.BoardPackageError(
                f"duplicate board ID: {package.board_id}"
            )
        board_ids.add(package.board_id)
    return tuple(sorted(completed_packages, key=_package_sort_key))


def open_package(
    client: _GitHubSnapshotClient, token: str, branch: str, board_id: str
) -> GitHubBoardPackage:
    """Open one board by ID after fully decoding the current primary PNG."""
    board_id = board_package._identifier(board_id, "board ID")
    package = _load_by_board_id(client, token, branch, board_id)
    return package


def primary_image_bytes(
    client: _GitHubSnapshotClient, token: str, branch: str, board_id: str
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
    client: _GitHubMutationClient,
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


def _load_completed_packages(
    executor: Executor,
    client: _GitHubSnapshotClient,
    token: str,
    completed: list[tuple[str, dict[str, TreeEntry]]],
) -> list[GitHubBoardPackage | tuple[GitHubBoardPackage, bytes]]:
    pending = [
        executor.submit(
            _load_package_from_entries,
            client,
            token,
            slug,
            entries,
            inspect_png_header_only=True,
        )
        for slug, entries in completed
    ]
    return [future.result() for future in pending]


def _copy_packages(
    packages: tuple[GitHubBoardPackage, ...]
) -> tuple[GitHubBoardPackage, ...]:
    return tuple(
        GitHubBoardPackage(
            package.slug,
            deepcopy(package.board),
            package.image_width,
            package.image_height,
            package.board_json_sha,
        )
        for package in packages
    )


def _load_selected_package(
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    slug: str,
    board_id: str,
) -> GitHubBoardPackage:
    package = _load_slug(
        client, token, branch, slug, inspect_png_header_only=False
    )
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return package


def _load_selected_package_with_image(
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    slug: str,
    board_id: str,
) -> tuple[GitHubBoardPackage, bytes]:
    package, image = _load_slug_with_image(client, token, branch, slug)
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return package, image


def _load_slug(
    client: _GitHubSnapshotClient,
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
    client: _GitHubSnapshotClient, token: str, branch: str, board_id: str
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
    client: _GitHubSnapshotClient, token: str, branch: str, slug: str
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
    client: _GitHubSnapshotClient,
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
    client: _GitHubSnapshotClient, token: str, entries: Mapping[str, TreeEntry]
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
    client: _GitHubSnapshotClient, token: str, entry: TreeEntry, label: str
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


def _credential_key(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()
