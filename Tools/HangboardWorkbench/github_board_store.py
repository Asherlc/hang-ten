"""GitHub-backed board package storage."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable, Iterator, Mapping
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, Literal, ParamSpec, Protocol, TypeVar, overload

import board_package
from board_geometry import NormalizedFrame, union_normalized_frames
from github_client import GitHubConflictError, GitHubNotFoundError, TreeEntry

_BOARD_LIBRARY_PATH = "Hangboards"
_MAX_CONCURRENT_PACKAGE_LOADS = 4
_MAX_CONCURRENT_CONTROL_CALLS = 4
_MAX_CACHED_TREES = 16
_MAX_CACHED_TREE_ENTRIES = 50_000
_MAX_CACHED_TREE_BYTES = 16 * 1024 * 1024
_MAX_CACHED_CATALOGS = 16
_MAX_CACHED_CATALOG_BYTES = 16 * 1024 * 1024
_MAX_CACHED_OPENED_PACKAGES = 16
_MAX_CACHED_OPENED_PACKAGE_BYTES = 16 * 1024 * 1024
_MAX_CACHED_BLOBS = 128
_MAX_CACHED_BLOB_BYTES = 32 * 1024 * 1024

_Arguments = ParamSpec("_Arguments")
_Result = TypeVar("_Result")
_FlightKey = TypeVar("_FlightKey", bound=Hashable)


@dataclass(slots=True)
class _BlobFlight:
    future: Future[bytes]
    cache_on_success: bool


class _GitHubSnapshotClient(Protocol):
    def get_tree(self, token: str, branch: str) -> tuple[TreeEntry, ...]: ...

    def get_blob(self, token: str, sha: str) -> bytes: ...


class _GitHubMutationClient(_GitHubSnapshotClient, Protocol):
    def commit_files(
        self,
        token: str,
        branch: str,
        expected_head_sha: str,
        changes: Mapping[str, bytes | None],
        message: str,
    ) -> str: ...

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
        max_cached_tree_bytes: int = _MAX_CACHED_TREE_BYTES,
        max_cached_catalogs: int = _MAX_CACHED_CATALOGS,
        max_cached_catalog_bytes: int = _MAX_CACHED_CATALOG_BYTES,
        max_cached_opened_packages: int = _MAX_CACHED_OPENED_PACKAGES,
        max_cached_opened_package_bytes: int = _MAX_CACHED_OPENED_PACKAGE_BYTES,
        max_cached_blobs: int = _MAX_CACHED_BLOBS,
        max_cached_blob_bytes: int = _MAX_CACHED_BLOB_BYTES,
        max_concurrent_package_loads: int = _MAX_CONCURRENT_PACKAGE_LOADS,
        max_concurrent_control_calls: int = _MAX_CONCURRENT_CONTROL_CALLS,
    ) -> None:
        if (
            min(
                max_cached_trees,
                max_cached_tree_entries,
                max_cached_tree_bytes,
                max_cached_catalogs,
                max_cached_catalog_bytes,
                max_cached_opened_packages,
                max_cached_opened_package_bytes,
                max_cached_blobs,
                max_cached_blob_bytes,
                max_concurrent_package_loads,
                max_concurrent_control_calls,
            )
            < 1
        ):
            raise ValueError("GitHub cache limits must be positive")
        self._client = client
        self._max_cached_trees = max_cached_trees
        self._max_cached_tree_entries = max_cached_tree_entries
        self._max_cached_tree_bytes = max_cached_tree_bytes
        self._max_cached_catalogs = max_cached_catalogs
        self._max_cached_catalog_bytes = max_cached_catalog_bytes
        self._max_cached_opened_packages = max_cached_opened_packages
        self._max_cached_opened_package_bytes = max_cached_opened_package_bytes
        self._max_cached_blobs = max_cached_blobs
        self._max_cached_blob_bytes = max_cached_blob_bytes
        self._max_concurrent_package_loads = max_concurrent_package_loads
        self._trees: OrderedDict[tuple[bytes, str], tuple[TreeEntry, ...]] = (
            OrderedDict()
        )
        self._catalogs: OrderedDict[
            tuple[bytes, str], tuple[GitHubBoardListing, ...]
        ] = OrderedDict()
        self._tree_sizes: dict[tuple[bytes, str], int] = {}
        self._catalog_sizes: dict[tuple[bytes, str], int] = {}
        self._tree_bytes = 0
        self._catalog_bytes = 0
        self._opened_packages: OrderedDict[
            tuple[bytes, str, str], GitHubBoardPackage
        ] = OrderedDict()
        self._opened_package_sizes: dict[tuple[bytes, str, str], int] = {}
        self._opened_package_bytes = 0
        self._blobs: OrderedDict[tuple[bytes, str], bytes] = OrderedDict()
        self._blob_bytes = 0
        self._lock = threading.RLock()
        self._load_slots = threading.BoundedSemaphore(
            max_concurrent_package_loads
        )
        self._control_slots = threading.BoundedSemaphore(
            max_concurrent_control_calls
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent_package_loads,
            thread_name_prefix="hangboard-github-load",
        )
        self._tree_flights: dict[tuple[bytes, str], Future[tuple[TreeEntry, ...]]] = {}
        self._catalog_flights: dict[
            tuple[bytes, str], Future[tuple[GitHubBoardListing, ...]]
        ] = {}
        self._blob_flights: dict[tuple[bytes, str], _BlobFlight] = {}
        self._operations = threading.Condition(self._lock)
        self._active_operations = 0
        self._closing = False
        self._closed = False

    def discover_packages(
        self, token: str, branch: str
    ) -> tuple[GitHubBoardListing, ...]:
        with self._operation():
            snapshot = self._snapshot(token, branch, cache_blobs=True)
            return _copy_listings(self._catalog(snapshot, token, branch))

    def open_package(
        self, token: str, branch: str, board_id: str
    ) -> GitHubBoardPackage:
        with self._operation():
            board_id = board_package._identifier(board_id, "board ID")
            snapshot = self._snapshot(token, branch, cache_blobs=False)
            selected = _selected_package(
                self._catalog(snapshot, token, branch), board_id
            )
            package = _load_selected_package(
                snapshot.with_blob_cache(),
                token,
                branch,
                selected.slug,
                board_id,
                prevalidated_board=selected.board,
            )
            self._cache_opened_package(token, branch, package)
            return package

    def open_presentation(
        self,
        token: str,
        branch: str,
        board_id: str,
        presentation_id: str | None,
    ) -> GitHubBoardPackage:
        """Read one presentation for the editor without warming the save cache."""
        with self._operation():
            board_id = board_package._identifier(board_id, "board ID")
            snapshot = self._snapshot(token, branch, cache_blobs=False)
            selected = _selected_package(
                self._catalog(snapshot, token, branch), board_id
            )
            package, _image = _load_selected_presentation(
                snapshot.with_blob_cache(),
                token,
                branch,
                selected.slug,
                board_id,
                presentation_id,
                prevalidated_board=selected.board,
            )
            return package

    def primary_image_bytes(self, token: str, branch: str, board_id: str) -> bytes:
        return self.presentation_image_bytes(token, branch, board_id, None)

    def presentation_image_bytes(
        self,
        token: str,
        branch: str,
        board_id: str,
        presentation_id: str | None,
    ) -> bytes:
        with self._operation():
            board_id = board_package._identifier(board_id, "board ID")
            snapshot = self._snapshot(token, branch, cache_blobs=False)
            selected = _selected_package(
                self._catalog(snapshot, token, branch), board_id
            )
            _package, image = _load_selected_presentation(
                snapshot.with_blob_cache(),
                token,
                branch,
                selected.slug,
                board_id,
                presentation_id,
                prevalidated_board=selected.board,
            )
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
        with self._operation():
            slug = board_package._slug(slug)
            live = self._opened_package(token, branch, slug)
            if live is None:
                live = self._open_slug_for_save(
                    token, branch, slug, expected_board_id=expected_board_id
                )
            saved = _save_loaded_editor_document(
                _StoreMutationClient(self, token, branch),
                token,
                branch,
                slug,
                live,
                document,
                expected_board_id=expected_board_id,
            )
            self._cache_opened_package(token, branch, saved[0])
            return saved

    def save_board_editor_document(
        self,
        token: str,
        branch: str,
        board_id: str,
        document: Mapping[str, Any],
    ) -> tuple[GitHubBoardPackage, str]:
        """Save a selected board, reusing its fully validated opened package."""
        with self._operation():
            board_id = board_package._identifier(board_id, "board ID")
            live = self._opened_package_by_board_id(token, branch, board_id)
            if live is None:
                snapshot = self._snapshot(token, branch, cache_blobs=True)
                selected = _selected_package(
                    self._catalog(snapshot, token, branch), board_id
                )
                live = _load_selected_package(
                    snapshot,
                    token,
                    branch,
                    selected.slug,
                    board_id,
                    prevalidated_board=selected.board,
                )
                self._cache_opened_package(token, branch, live)
            saved = _save_loaded_editor_document(
                _StoreMutationClient(self, token, branch),
                token,
                branch,
                live.slug,
                live,
                document,
                expected_board_id=board_id,
            )
            self._cache_opened_package(token, branch, saved[0])
            return saved

    def delete_board_presentation(
        self,
        token: str,
        branch: str,
        board_id: str,
        presentation_id: str,
    ) -> tuple[GitHubBoardPackage, str]:
        """Remove a canonical surface through the authenticated GitHub store."""
        with self._operation():
            board_id = board_package._identifier(board_id, "board ID")
            snapshot = self._snapshot(token, branch, cache_blobs=True)
            selected = _selected_package(
                self._catalog(snapshot, token, branch), board_id
            )
            live = _load_selected_package(
                snapshot,
                token,
                branch,
                selected.slug,
                board_id,
                prevalidated_board=selected.board,
            )
            entries = _package_groups(snapshot.get_tree(token, branch))[live.slug]
            deleted = _delete_loaded_presentation(
                _StoreMutationClient(self, token, branch),
                token,
                branch,
                live,
                presentation_id,
                entries,
                expected_head_sha=snapshot.commit_sha,
            )
            self._cache_opened_package(token, branch, deleted[0])
            return deleted

    def close(self) -> None:
        with self._operations:
            if self._closed:
                return
            if self._closing:
                while not self._closed:
                    self._operations.wait()
                return
            self._closing = True
            while self._active_operations:
                self._operations.wait()
        try:
            self._executor.shutdown(wait=True, cancel_futures=True)
        finally:
            with self._operations:
                self._closed = True
                self._operations.notify_all()

    @contextmanager
    def _operation(self) -> Iterator[None]:
        """Lease the store for one public operation until close drains it."""
        with self._operations:
            if self._closing:
                raise RuntimeError("GitHub board store is closing")
            self._active_operations += 1
        try:
            yield
        finally:
            with self._operations:
                self._active_operations -= 1
                if not self._active_operations:
                    self._operations.notify_all()

    def _snapshot(
        self, token: str, branch: str, *, cache_blobs: bool
    ) -> _CachedSnapshotClient:
        credential_key = _credential_key(token)
        head = self._call_control(self._client.get_branch_head_sha, token, branch)
        key = (credential_key, head)
        tree = self._tree(key, token, head)
        return _CachedSnapshotClient(
            self, token, credential_key, branch, head, tree, cache_blobs
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
            tree = self._call_bulk(self._client.get_tree, token, head)
            cache_size = _tree_cache_size(tree)
            if (
                len(tree) <= self._max_cached_tree_entries
                and cache_size <= self._max_cached_tree_bytes
            ):
                with self._lock:
                    previous = self._trees.pop(key, None)
                    if previous is not None:
                        self._tree_bytes -= self._tree_sizes.pop(key)
                    self._trees[key] = tree
                    self._tree_sizes[key] = cache_size
                    self._tree_bytes += cache_size
                    self._trees.move_to_end(key)
                    while (
                        len(self._trees) > self._max_cached_trees
                        or self._tree_bytes > self._max_cached_tree_bytes
                    ):
                        discarded_key, _discarded = self._trees.popitem(last=False)
                        self._tree_bytes -= self._tree_sizes.pop(discarded_key)
            return tree

        return self._single_flight(self._tree_flights, key, load)

    def _catalog(
        self, snapshot: _CachedSnapshotClient, token: str, branch: str
    ) -> tuple[GitHubBoardListing, ...]:
        key = (snapshot.credential_key, snapshot.commit_sha)
        with self._lock:
            catalog = self._catalogs.get(key)
            if catalog is not None:
                self._catalogs.move_to_end(key)
                return catalog

        def load() -> tuple[GitHubBoardListing, ...]:
            catalog = discover_package_listings(snapshot, token, branch)
            cache_size = _catalog_cache_size(catalog)
            if cache_size <= self._max_cached_catalog_bytes:
                with self._lock:
                    previous = self._catalogs.pop(key, None)
                    if previous is not None:
                        self._catalog_bytes -= self._catalog_sizes.pop(key)
                    self._catalogs[key] = catalog
                    self._catalog_sizes[key] = cache_size
                    self._catalog_bytes += cache_size
                    self._catalogs.move_to_end(key)
                    while (
                        len(self._catalogs) > self._max_cached_catalogs
                        or self._catalog_bytes > self._max_cached_catalog_bytes
                    ):
                        discarded_key, _discarded = self._catalogs.popitem(last=False)
                        self._catalog_bytes -= self._catalog_sizes.pop(discarded_key)
            return catalog

        return self._single_flight(self._catalog_flights, key, load)

    def _opened_package(
        self, token: str, branch: str, slug: str
    ) -> GitHubBoardPackage | None:
        key = (_credential_key(token), branch, slug)
        with self._lock:
            package = self._opened_packages.get(key)
            if package is not None:
                self._opened_packages.move_to_end(key)
            return package

    def _opened_package_by_board_id(
        self, token: str, branch: str, board_id: str
    ) -> GitHubBoardPackage | None:
        credential_key = _credential_key(token)
        with self._lock:
            for key in reversed(self._opened_packages):
                package = self._opened_packages[key]
                if key[:2] == (credential_key, branch) and package.board_id == board_id:
                    self._opened_packages.move_to_end(key)
                    return package
        return None

    def _open_slug_for_save(
        self,
        token: str,
        branch: str,
        slug: str,
        *,
        expected_board_id: str | None,
    ) -> GitHubBoardPackage:
        snapshot = self._snapshot(token, branch, cache_blobs=True)
        package = _load_slug(
            snapshot, token, branch, slug, inspect_png_header_only=False
        )
        if expected_board_id is not None:
            expected_board_id = board_package._identifier(expected_board_id, "board ID")
            if package.board_id != expected_board_id:
                raise board_package.BoardSaveConflictError(
                    "board identity changed; reload and try again"
                )
        self._cache_opened_package(token, branch, package)
        return package

    def _cache_opened_package(
        self, token: str, branch: str, package: GitHubBoardPackage
    ) -> None:
        key = (_credential_key(token), branch, package.slug)
        size = _package_cache_size(package)
        if size > self._max_cached_opened_package_bytes:
            return
        with self._lock:
            previous = self._opened_packages.pop(key, None)
            if previous is not None:
                self._opened_package_bytes -= self._opened_package_sizes.pop(key)
            self._opened_packages[key] = package
            self._opened_package_sizes[key] = size
            self._opened_package_bytes += size
            while (
                len(self._opened_packages) > self._max_cached_opened_packages
                or self._opened_package_bytes > self._max_cached_opened_package_bytes
            ):
                discarded_key, _discarded = self._opened_packages.popitem(last=False)
                self._opened_package_bytes -= self._opened_package_sizes.pop(
                    discarded_key
                )

    def _blob(
        self,
        token: str,
        credential_key: bytes,
        sha: str,
        *,
        cache: bool,
        stage_cache_miss: bool = False,
    ) -> bytes:
        key = (credential_key, sha)
        if cache:
            with self._lock:
                blob = self._blobs.get(key)
                if blob is not None:
                    if not stage_cache_miss:
                        self._blobs.move_to_end(key)
                    return blob

        with self._lock:
            flight = self._blob_flights.get(key)
            if flight is None:
                flight = _BlobFlight(
                    Future(), cache and not stage_cache_miss
                )
                self._blob_flights[key] = flight
                owner = True
            else:
                if cache and not stage_cache_miss:
                    flight.cache_on_success = True
                owner = False
        if not owner:
            blob = flight.future.result()
            if cache and not stage_cache_miss:
                with self._lock:
                    if key not in self._blobs:
                        self._cache_blob(key, blob)
            return blob
        try:
            blob = self._call_bulk(self._client.get_blob, token, sha)
            with self._lock:
                if flight.cache_on_success:
                    self._cache_blob(key, blob)
                flight.future.set_result(blob)
            return blob
        except BaseException as error:
            flight.future.set_exception(error)
            raise
        finally:
            with self._lock:
                self._blob_flights.pop(key, None)

    def _cache_blob(self, key: tuple[bytes, str], blob: bytes) -> None:
        if len(blob) > self._max_cached_blob_bytes:
            return
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

    def _call_control(
        self,
        operation: Callable[_Arguments, _Result],
        *args: _Arguments.args,
        **kwargs: _Arguments.kwargs,
    ) -> _Result:
        with self._control_slots:
            return operation(*args, **kwargs)

    def _call_bulk(
        self,
        operation: Callable[_Arguments, _Result],
        *args: _Arguments.args,
        **kwargs: _Arguments.kwargs,
    ) -> _Result:
        with self._load_slots:
            return operation(*args, **kwargs)

    def _single_flight(
        self,
        flights: dict[_FlightKey, Future[_Result]],
        key: _FlightKey,
        load: Callable[[], _Result],
    ) -> _Result:
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

class _StoreMutationClient:
    """Pins a write to one credential and branch without reading a snapshot."""

    def __init__(self, store: GitHubBoardStore, token: str, branch: str) -> None:
        self._store = store
        self._token = token
        self._branch = branch

    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str:
        if token != self._token or branch != self._branch:
            raise RuntimeError("GitHub mutation credentials or branch do not match")
        return self._store._call_control(
            self._store._client.put_file,
            token,
            path,
            branch,
            content,
            message,
            sha,
        )

    def commit_files(
        self,
        token: str,
        branch: str,
        expected_head_sha: str,
        changes: Mapping[str, bytes | None],
        message: str,
    ) -> str:
        if token != self._token or branch != self._branch:
            raise RuntimeError("GitHub mutation credentials or branch do not match")
        return self._store._call_control(
            self._store._client.commit_files,
            token,
            branch,
            expected_head_sha,
            changes,
            message,
        )

class _CachedSnapshotClient:
    """Presents one authenticated immutable tree to existing load helpers."""

    def __init__(
        self,
        store: GitHubBoardStore,
        token: str,
        credential_key: bytes,
        branch: str,
        commit_sha: str,
        tree: tuple[TreeEntry, ...],
        cache_blobs: bool,
    ) -> None:
        self._store = store
        self._token = token
        self._credential_key = credential_key
        self._branch = branch
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
        self._require_snapshot(token, branch)
        return self._tree

    def get_blob(self, token: str, sha: str) -> bytes:
        self._require_token(token)
        return self._store._blob(
            token, self._credential_key, sha, cache=self._cache_blobs
        )

    def get_staged_blob(self, token: str, sha: str) -> bytes:
        self._require_token(token)
        return self._store._blob(
            token,
            self._credential_key,
            sha,
            cache=self._cache_blobs,
            stage_cache_miss=True,
        )

    def with_blob_cache(self) -> _CachedSnapshotClient:
        return _CachedSnapshotClient(
            self._store,
            self._token,
            self._credential_key,
            self._branch,
            self._commit_sha,
            self._tree,
            True,
        )

    def cache_blobs_in_order(self, blobs: tuple[tuple[str, bytes], ...]) -> None:
        if not self._cache_blobs:
            return
        for sha, blob in blobs:
            self._store._cache_blob((self._credential_key, sha), blob)

    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str:
        self._require_snapshot(token, branch)
        return self._store._call_control(
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

    def _require_snapshot(self, token: str, branch: str) -> None:
        self._require_token(token)
        if branch != self._branch:
            raise RuntimeError("GitHub snapshot branch does not match")


@dataclass(frozen=True, slots=True)
class GitHubBoardListing:
    """Metadata validated without downloading a package primary image."""

    slug: str
    board: dict[str, Any]
    board_json_sha: str

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def hold_ids(self) -> tuple[str, ...]:
        return tuple(hold["id"] for hold in self.board["holds"])


@dataclass(frozen=True, slots=True)
class GitHubBoardPackage:
    slug: str
    board: dict[str, Any]
    image_width: int
    image_height: int
    board_json_sha: str
    presentations: tuple[board_package.BoardPresentation, ...] = ()

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def hold_ids(self) -> tuple[str, ...]:
        return tuple(hold["id"] for hold in self.board["holds"])

    def presentation(
        self, presentation_id: str | None = None
    ) -> board_package.BoardPresentation:
        selected = (
            next((item for item in self.presentations if item.id == presentation_id), None)
            if presentation_id is not None
            else next((item for item in self.presentations if item.is_default), None)
        )
        if selected is None:
            raise board_package.BoardPackageError("presentation is not available")
        return selected

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
    max_concurrent_package_loads: int = _MAX_CONCURRENT_PACKAGE_LOADS,
) -> tuple[GitHubBoardPackage, ...]:
    """List completed remote board packages with header-only PNG validation."""
    if max_concurrent_package_loads < 1:
        raise ValueError("GitHub cache limits must be positive")
    groups = _package_groups(client.get_tree(token, branch))
    completed = [
        (slug, entries) for slug, entries in groups.items() if _is_completed(entries)
    ]
    if executor is None:
        with ThreadPoolExecutor(max_workers=max_concurrent_package_loads) as pool:
            packages = _load_completed_packages(
                pool,
                client,
                token,
                completed,
                max_concurrent_package_loads,
            )
    else:
        packages = _load_completed_packages(
            executor,
            client,
            token,
            completed,
            max_concurrent_package_loads,
        )
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
        completed_packages.append(package)
        if package.board_id in board_ids:
            raise board_package.BoardPackageError(
                f"duplicate board ID: {package.board_id}"
            )
        board_ids.add(package.board_id)
    return tuple(sorted(completed_packages, key=_package_sort_key))


def discover_package_listings(
    client: _GitHubSnapshotClient, token: str, branch: str
) -> tuple[GitHubBoardListing, ...]:
    """List complete package metadata without downloading primary image blobs."""
    groups = _package_groups(client.get_tree(token, branch))
    listings: list[GitHubBoardListing] = []
    board_ids: set[str] = set()
    for slug, entries in groups.items():
        if not _is_completed(entries):
            if not _is_primary_only_draft(entries):
                _raise_for_incomplete_layout(slug, entries)
            continue
        board_entry = entries["board.json"]
        board = _load_board_json(_get_blob(client, token, board_entry, "board.json"))
        board_package.validate_catalog_board(board, allow_missing_kind=True)
        listing = GitHubBoardListing(slug, board, board_entry.sha)
        if listing.board_id in board_ids:
            raise board_package.BoardPackageError(
                f"duplicate board ID: {listing.board_id}"
            )
        board_ids.add(listing.board_id)
        listings.append(listing)
    return tuple(sorted(listings, key=_package_sort_key))


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
    return presentation_image_bytes(client, token, branch, board_id, None)


def presentation_image_bytes(
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    board_id: str,
    presentation_id: str | None,
) -> bytes:
    """Return one authenticated board presentation's validated image bytes."""
    board_id = board_package._identifier(board_id, "board ID")
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    package, images = _load_slug_with_image(client, token, branch, selected.slug)
    if package.board_id == board_id:
        return images[package.presentation(presentation_id).asset_path]
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    package, images = _load_slug_with_image(client, token, branch, selected.slug)
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return images[package.presentation(presentation_id).asset_path]


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
    return _save_loaded_editor_document(
        client,
        token,
        branch,
        slug,
        live,
        document,
        expected_board_id=expected_board_id,
    )


def _delete_loaded_presentation(
    client: _GitHubMutationClient,
    token: str,
    branch: str,
    live: GitHubBoardPackage,
    presentation_id: str,
    entries: Mapping[str, TreeEntry],
    *,
    expected_head_sha: str,
) -> tuple[GitHubBoardPackage, str]:
    board, removed_assets = board_package._delete_presentation_from_board(
        live.board, presentation_id
    )
    presentation_values = board_package._parse_board_presentations(board)
    remaining_presentations = tuple(
        replace(
            presentation,
            is_default=next(
                item[4] for item in presentation_values if item[0] == presentation.id
            ),
        )
        for presentation in live.presentations
        if any(item[0] == presentation.id for item in presentation_values)
    )
    default = next(item for item in remaining_presentations if item.is_default)
    board_package._validate_board(
        board,
        default.image_width,
        default.image_height,
        presentations=remaining_presentations,
        allow_missing_kind=True,
    )
    content = (json.dumps(board, indent=2) + "\n").encode("utf-8")
    changes: dict[str, bytes | None] = {
        f"{_BOARD_LIBRARY_PATH}/{live.slug}/board.json": content,
    }
    for asset_path in removed_assets:
        entry = entries.get(asset_path)
        if entry is None or entry.type != "blob":
            raise board_package.BoardPackageError("package presentation image is missing")
        changes[f"{_BOARD_LIBRARY_PATH}/{live.slug}/{asset_path}"] = None
    try:
        commit_sha = client.commit_files(
            token,
            branch,
            expected_head_sha,
            changes,
            f"Delete presentation {presentation_id} from {live.board_id}",
        )
    except GitHubConflictError as error:
        raise board_package.BoardSaveConflictError(str(error)) from error
    return (
        GitHubBoardPackage(
            live.slug,
            board,
            default.image_width,
            default.image_height,
            _git_blob_sha(content),
            remaining_presentations,
        ),
        commit_sha,
    )


def _save_loaded_editor_document(
    client: _GitHubMutationClient,
    token: str,
    branch: str,
    slug: str,
    live: GitHubBoardPackage,
    document: Mapping[str, Any],
    *,
    expected_board_id: str | None = None,
) -> tuple[GitHubBoardPackage, str]:
    """Validate and conditionally commit against a previously opened package."""
    if expected_board_id is not None:
        expected_board_id = board_package._identifier(expected_board_id, "board ID")
        if live.board_id != expected_board_id:
            raise board_package.BoardSaveConflictError(
                "board identity changed; reload and try again"
            )
    requested_presentation_id = document.get("presentationID")
    presentation = live.presentation(
        requested_presentation_id if isinstance(requested_presentation_id, str) else None
    )
    if presentation.source_presentation_id is not None:
        raise board_package.BoardPackageError("alias presentations cannot be edited")
    width, height = presentation.image_width, presentation.image_height
    expected_equipment_objects = [
        item["id"] for item in live.board.get("equipmentObjects", [{"id": "primary"}])
    ]
    if document.get("equipmentObjects", ["primary"]) != expected_equipment_objects:
        raise board_package.BoardPackageError(
            "editor document equipment objects do not match the board package"
        )
    parsed_regions = board_package._validate_editor_document(
        document,
        width,
        height,
        presentation.id,
        require_presentation_id=True,
    )

    pieces_by_hold: dict[
        str, list[board_package._EditorPiece]
    ] = {}
    for (
        hold_id,
        piece_index,
        kind,
        sloper,
        path,
        shape_constraint,
        bendable_command_indexes,
        smooth_anchor_indexes,
        finger_capacity,
        size_millimeters,
        depth_range,
        hand_capacity,
        paired_hold_id,
        equipment_object_id,
    ) in parsed_regions.values():
        pieces_by_hold.setdefault(hold_id, []).append(
            (
                piece_index,
                kind,
                sloper,
                path,
                shape_constraint,
                bendable_command_indexes,
                smooth_anchor_indexes,
                finger_capacity,
                size_millimeters,
                depth_range,
                hand_capacity,
                paired_hold_id,
                equipment_object_id,
            )
        )
    for pieces in pieces_by_hold.values():
        pieces.sort(key=lambda item: item[0])

    current_holds = {
        hold["id"]: hold
        for hold in live.board["holds"]
        if hold["presentationID"] == presentation.id
    }
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
        presentation_id=presentation.id,
    )
    board_package._validate_board(
        board,
        width,
        height,
        presentations=live.presentations,
        allow_missing_kind=True,
    )
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
        slug,
        board,
        live.image_width,
        live.image_height,
        _git_blob_sha(content),
        live.presentations,
    ), commit_sha


def _load_completed_packages(
    executor: Executor,
    client: _GitHubSnapshotClient,
    token: str,
    completed: list[tuple[str, dict[str, TreeEntry]]],
    max_concurrent_package_loads: int,
) -> list[GitHubBoardPackage]:
    window = min(max_concurrent_package_loads, len(completed))
    blob_slots = threading.BoundedSemaphore(max_concurrent_package_loads)
    pending = [
        executor.submit(
            _load_package_from_entries,
            client,
            token,
            slug,
            entries,
            inspect_png_header_only=True,
            blob_slots=blob_slots,
        )
        for slug, entries in completed[:window]
    ]
    next_index = window
    packages: list[GitHubBoardPackage] = []
    try:
        while pending:
            future = pending.pop(0)
            packages.append(future.result())
            if next_index < len(completed):
                slug, entries = completed[next_index]
                pending.append(
                    executor.submit(
                        _load_package_from_entries,
                        client,
                        token,
                        slug,
                        entries,
                        inspect_png_header_only=True,
                        blob_slots=blob_slots,
                    )
                )
                next_index += 1
    except BaseException:
        for future in pending:
            future.cancel()
        raise
    return packages


def _copy_listings(
    packages: tuple[GitHubBoardListing, ...]
) -> tuple[GitHubBoardListing, ...]:
    return tuple(
        GitHubBoardListing(
            package.slug,
            deepcopy(package.board),
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
    *,
    prevalidated_board: dict[str, Any] | None = None,
) -> GitHubBoardPackage:
    package = _load_slug(
        client,
        token,
        branch,
        slug,
        inspect_png_header_only=False,
        prevalidated_board=prevalidated_board,
    )
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return package


def _load_selected_presentation(
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    slug: str,
    board_id: str,
    presentation_id: str | None,
    *,
    prevalidated_board: dict[str, Any],
) -> tuple[GitHubBoardPackage, bytes]:
    groups = _package_groups(client.get_tree(token, branch))
    entries = groups.get(slug)
    if entries is None:
        raise board_package.BoardPackageError("board package is not available")
    if not _is_completed(entries):
        _raise_for_incomplete_layout(slug, entries)

    board_entry = entries["board.json"]
    board = _load_board_json(_get_blob(client, token, board_entry, "board.json"))
    board_package.validate_catalog_board(board, allow_missing_kind=True)
    if board != prevalidated_board:
        raise board_package.BoardPackageError("board.json changed during loading")
    if board.get("id") != board_id:
        raise board_package.BoardNotAvailableError("board is not available")

    asset_entries = {
        path: entry
        for path, entry in entries.items()
        if path.startswith("assets/") and entry.type == "blob"
    }
    presentation_values = board_package._parse_board_presentations(board)
    if set(asset_entries) != {item[2] for item in presentation_values}:
        raise board_package.BoardPackageError(
            "board package assets must exactly match its presentations"
        )
    selected_value = (
        next(item for item in presentation_values if item[4])
        if presentation_id is None
        else next(
            (item for item in presentation_values if item[0] == presentation_id),
            None,
        )
    )
    if selected_value is None:
        raise board_package.BoardPackageError("presentation is not available")
    selected_asset = selected_value[2]
    image = _get_blob(
        client, token, asset_entries[selected_asset], "package presentation image"
    )
    width, height = board_package._png_dimensions_from_bytes(image)
    image_aspect_ratio = width / height
    relative_error = abs(selected_value[3] - image_aspect_ratio) / image_aspect_ratio
    if relative_error > board_package._ASPECT_RATIO_RELATIVE_TOLERANCE:
        raise board_package.BoardPackageError(
            f"board.json presentation {selected_value[0]}.aspectRatio must match its image width/height within 0.1%"
        )
    source_presentation_id = selected_value[5] or selected_value[0]
    for index, hold in enumerate(board["holds"]):
        if hold["presentationID"] != source_presentation_id:
            continue
        board_package._validate_hold(
            hold,
            width,
            height,
            f"board.json.holds[{index}]",
            requires_presentation_id=True,
            allow_missing_kind=True,
        )

    # Only the selected presentation reaches the editor document.  Sibling
    # dimensions are deliberately deferred to their own image request or save.
    presentations = tuple(
        board_package.BoardPresentation(
            id=item[0],
            name=item[1],
            asset_path=item[2],
            aspect_ratio=item[3],
            is_default=item[4],
            image_width=width,
            image_height=height,
            source_presentation_id=item[5],
            is_inverted=item[6],
        )
        for item in presentation_values
    )
    return (
        GitHubBoardPackage(slug, board, width, height, board_entry.sha, presentations),
        image,
    )


def _load_selected_package_with_image(
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    slug: str,
    board_id: str,
    *,
    prevalidated_board: dict[str, Any] | None = None,
) -> tuple[GitHubBoardPackage, dict[str, bytes]]:
    package, images = _load_slug_with_image(
        client, token, branch, slug, prevalidated_board=prevalidated_board
    )
    if package.board_id != board_id:
        raise board_package.BoardNotAvailableError("board is not available")
    return package, images


def _load_slug(
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    slug: str,
    *,
    inspect_png_header_only: bool,
    prevalidated_board: dict[str, Any] | None = None,
) -> GitHubBoardPackage:
    groups = _package_groups(client.get_tree(token, branch))
    entries = groups.get(slug)
    if entries is None:
        raise board_package.BoardPackageError("board package is not available")
    if not _is_completed(entries):
        _raise_for_incomplete_layout(slug, entries)
    return _load_package_from_entries(
        client,
        token,
        slug,
        entries,
        inspect_png_header_only=inspect_png_header_only,
        prevalidated_board=prevalidated_board,
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
    client: _GitHubSnapshotClient,
    token: str,
    branch: str,
    slug: str,
    *,
    prevalidated_board: dict[str, Any] | None = None,
) -> tuple[GitHubBoardPackage, dict[str, bytes]]:
    groups = _package_groups(client.get_tree(token, branch))
    entries = groups.get(slug)
    if entries is None:
        raise board_package.BoardPackageError("board package is not available")
    if not _is_completed(entries):
        _raise_for_incomplete_layout(slug, entries)
    package, images = _load_package_from_entries(
        client,
        token,
        slug,
        entries,
        inspect_png_header_only=False,
        include_image=True,
        prevalidated_board=prevalidated_board,
    )
    return package, images


@overload
def _load_package_from_entries(
    client: _GitHubSnapshotClient,
    token: str,
    slug: str,
    entries: Mapping[str, TreeEntry],
    *,
    inspect_png_header_only: bool,
    include_image: Literal[False] = False,
    prevalidated_board: dict[str, Any] | None = None,
    blob_slots: threading.BoundedSemaphore | None = None,
) -> GitHubBoardPackage: ...


@overload
def _load_package_from_entries(
    client: _GitHubSnapshotClient,
    token: str,
    slug: str,
    entries: Mapping[str, TreeEntry],
    *,
    inspect_png_header_only: bool,
    include_image: Literal[True],
    prevalidated_board: dict[str, Any] | None = None,
    blob_slots: threading.BoundedSemaphore | None = None,
) -> tuple[GitHubBoardPackage, dict[str, bytes]]: ...


def _load_package_from_entries(
    client: _GitHubSnapshotClient,
    token: str,
    slug: str,
    entries: Mapping[str, TreeEntry],
    *,
    inspect_png_header_only: bool,
    include_image: bool = False,
    prevalidated_board: dict[str, Any] | None = None,
    blob_slots: threading.BoundedSemaphore | None = None,
) -> GitHubBoardPackage | tuple[GitHubBoardPackage, dict[str, bytes]]:
    if prevalidated_board is not None and len(
        {item[2] for item in board_package._parse_board_presentations(prevalidated_board)}
    ) == 1:
        prevalidated_board = None
    asset_entries = {
        path: entry
        for path, entry in entries.items()
        if path.startswith("assets/") and entry.type == "blob"
    }
    images: dict[str, bytes] = {}
    dimensions: dict[str, tuple[int, int]] = {}
    primary_entry = asset_entries.get("assets/primary.png")
    board_entry = entries["board.json"]
    board_blob: bytes
    if prevalidated_board is None:
        if primary_entry is not None:
            primary_image = _get_blob(
                client,
                token,
                primary_entry,
                "package primary image",
                blob_slots=blob_slots,
            )
            images["assets/primary.png"] = primary_image
            dimensions["assets/primary.png"] = (
                board_package._png_header_dimensions_from_bytes(primary_image[:33])
                if inspect_png_header_only
                else board_package._png_dimensions_from_bytes(primary_image)
            )
        board_blob = _get_blob(
            client, token, board_entry, "board.json", blob_slots=blob_slots
        )
        board = _load_board_json(board_blob)
        concurrent_assets = {
            path: entry
            for path, entry in asset_entries.items()
            if path != "assets/primary.png"
        }
    else:
        board = deepcopy(prevalidated_board)
        concurrent_assets = asset_entries
    presentation_values = board_package._parse_board_presentations(board)
    expected_assets = {item[2] for item in presentation_values}
    if set(asset_entries) != expected_assets:
        raise board_package.BoardPackageError(
            "board package assets must exactly match its presentations"
        )
    with ThreadPoolExecutor(
        max_workers=min(
            _MAX_CONCURRENT_PACKAGE_LOADS, max(1, len(concurrent_assets) + 1)
        )
    ) as executor:
        board_future = (
            executor.submit(
                _get_blob,
                client,
                token,
                board_entry,
                "board.json",
                blob_slots=blob_slots,
            )
            if prevalidated_board is not None
            else None
        )
        image_futures = {
            asset_path: executor.submit(
                _get_blob,
                client,
                token,
                image_entry,
                (
                    "package primary image"
                    if asset_path == "assets/primary.png"
                    else "package presentation image"
                ),
                stage_cache_miss=True,
                blob_slots=blob_slots,
            )
            for asset_path, image_entry in concurrent_assets.items()
        }
        for asset_path in sorted(concurrent_assets):
            image = image_futures[asset_path].result()
            images[asset_path] = image
            dimensions[asset_path] = (
                board_package._png_header_dimensions_from_bytes(image[:33])
                if inspect_png_header_only
                else board_package._png_dimensions_from_bytes(image)
            )
        if board_future is not None:
            board_blob = board_future.result()
    if isinstance(client, _CachedSnapshotClient):
        cache_order: list[tuple[str, bytes]] = []
        if primary_entry is not None:
            cache_order.append((primary_entry.sha, images["assets/primary.png"]))
        cache_order.append((board_entry.sha, board_blob))
        cache_order.extend(
            (asset_entries[asset_path].sha, images[asset_path])
            for asset_path in sorted(asset_entries)
            if asset_path != "assets/primary.png"
        )
        client.cache_blobs_in_order(tuple(cache_order))
    presentations = tuple(
        board_package.BoardPresentation(
            id=presentation_id,
            name=name,
            asset_path=asset_path,
            aspect_ratio=aspect_ratio,
            is_default=is_default,
            image_width=dimensions[asset_path][0],
            image_height=dimensions[asset_path][1],
            source_presentation_id=source_presentation_id,
            is_inverted=is_inverted,
        )
        for (
            presentation_id,
            name,
            asset_path,
            aspect_ratio,
            is_default,
            source_presentation_id,
            is_inverted,
        ) in presentation_values
    )
    default = next(item for item in presentations if item.is_default)
    board_package._validate_board(
        board,
        default.image_width,
        default.image_height,
        presentations=presentations,
        validate_geometry=not inspect_png_header_only,
        allow_missing_kind=True,
    )
    package = GitHubBoardPackage(
        slug,
        board,
        default.image_width,
        default.image_height,
        board_entry.sha,
        presentations,
    )
    return (package, images) if include_image else package


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
    return (
        entries.get("board.json") is not None
        and entries["board.json"].type == "blob"
        and entries.get("assets") is not None
        and entries["assets"].type == "tree"
        and any(
            path.startswith("assets/") and entry.type == "blob"
            for path, entry in entries.items()
        )
        and all(
            path in {"board.json", "assets"} or path.startswith("assets/")
            for path in entries
        )
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
            raise board_package.BoardPackageError(
                "board package assets must exactly match its presentations"
            )
        if entries["board.json"].type != "blob":
            raise board_package.BoardPackageError("board.json is missing")
    if "board.json" in entries:
        raise board_package.BoardPackageError(
            "board package must contain only board.json and assets/"
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
    client: _GitHubSnapshotClient,
    token: str,
    entry: TreeEntry,
    label: str,
    *,
    stage_cache_miss: bool = False,
    blob_slots: threading.BoundedSemaphore | None = None,
) -> bytes:
    try:
        if stage_cache_miss and isinstance(client, _CachedSnapshotClient):
            read_blob = client.get_staged_blob
        else:
            read_blob = client.get_blob
        if blob_slots is None:
            return read_blob(token, entry.sha)
        with blob_slots:
            return read_blob(token, entry.sha)
    except GitHubNotFoundError as error:
        if label == "board.json":
            raise board_package.BoardPackageError("board.json is missing") from error
        raise board_package.BoardPackageError(
            "package primary image is missing"
        ) from error


def _package_sort_key(
    package: GitHubBoardListing | GitHubBoardPackage,
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


def _tree_cache_size(tree: tuple[TreeEntry, ...]) -> int:
    """Return deterministic UTF-8 payload bytes retained for one tree cache entry."""
    return sum(
        len(entry.path.encode("utf-8"))
        + len(entry.type.encode("utf-8"))
        + len(entry.sha.encode("utf-8"))
        for entry in tree
    )


def _catalog_cache_size(catalog: tuple[GitHubBoardListing, ...]) -> int:
    """Return deterministic UTF-8 metadata bytes retained for one catalog entry."""
    return sum(
        len(package.slug.encode("utf-8"))
        + len(package.board_json_sha.encode("utf-8"))
        + len(
            json.dumps(
                package.board,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        + 16
        for package in catalog
    )


def _package_cache_size(package: GitHubBoardPackage) -> int:
    return (
        len(package.slug.encode("utf-8"))
        + len(package.board_json_sha.encode("utf-8"))
        + len(
            json.dumps(
                package.board,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        + 16
    )


def _credential_key(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()
