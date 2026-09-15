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
from dataclasses import dataclass, replace as dataclass_replace
from pathlib import Path
from typing import Any, Literal, ParamSpec, Protocol, TypeVar, overload

import board_package
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
            if not selected.editor_available:
                raise board_package.BoardEditorUnavailableError(
                    "3D model editing is not supported"
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
            if not selected.editor_available:
                raise board_package.BoardEditorUnavailableError(
                    "3D model editing is not supported"
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
            if not selected.editor_available:
                raise board_package.BoardEditorUnavailableError(
                    "3D model editing is not supported"
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
                if not selected.editor_available:
                    raise board_package.BoardEditorUnavailableError(
                        "3D model editing is not supported"
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
            if not selected.editor_available:
                raise board_package.BoardEditorUnavailableError(
                    "3D model editing is not supported"
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
    def contact_ids(self) -> tuple[str, ...]:
        return tuple(contact["id"] for contact in self.board["contacts"])

    @property
    def editor_available(self) -> bool:
        return board_package._board_editor_available(self.board)


@dataclass(frozen=True, slots=True)
class GitHubBoardPackage:
    slug: str
    board: dict[str, Any]
    image_width: int
    image_height: int
    board_json_sha: str
    presentations: tuple[board_package.BoardPresentation, ...] = ()
    schema_version: int = 3

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def contact_ids(self) -> tuple[str, ...]:
        return tuple(contact["id"] for contact in self.board["contacts"])

    @property
    def editor_available(self) -> bool:
        return all(item.media_type == "raster" for item in self.presentations)

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

    def contact_frame(self, contact_id: str) -> board_package.NormalizedFrame:
        local_view = board_package.BoardPackage(
            Path("."), self.board, self.image_width, self.image_height,
            self.presentations,
        )
        return local_view.contact_frame(contact_id)


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
    selected = _selected_package(discover_packages(client, token, branch), board_id)
    if not selected.editor_available:
        raise board_package.BoardEditorUnavailableError(
            "3D model editing is not supported"
        )
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
    if not selected.editor_available:
        raise board_package.BoardEditorUnavailableError(
            "3D model editing is not supported"
        )
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
    if not live.editor_available:
        raise board_package.BoardEditorUnavailableError(
            "3D model editing is not supported"
        )
    board, removed_assets = board_package._delete_presentation_from_board(
        live.board, presentation_id
    )
    remaining_ids = {item["id"] for item in board["presentations"]}
    default_id = next(item["id"] for item in board["presentations"] if item["isDefault"])
    remaining_presentations = tuple(
        dataclass_replace(presentation, is_default=presentation.id == default_id)
        for presentation in live.presentations
        if presentation.id in remaining_ids
    )
    default = next(item for item in remaining_presentations if item.is_default)
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
            schema_version=3,
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
    if not live.editor_available:
        raise board_package.BoardEditorUnavailableError(
            "3D model editing is not supported"
        )
    if expected_board_id is not None:
        expected_board_id = board_package._identifier(expected_board_id, "board ID")
        if live.board_id != expected_board_id:
            raise board_package.BoardSaveConflictError(
                "board identity changed; reload and try again"
            )
    board = board_package.apply_editor_document(live, document)
    if board_package._json_values_are_exactly_equal(board, live.board):
        return live, live.board_json_sha
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
        schema_version=3,
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
    if not board_package._board_editor_available(board):
        raise board_package.BoardEditorUnavailableError(
            "3D model editing is not supported"
        )

    asset_entries = {
        path: entry
        for path, entry in entries.items()
        if path.startswith("assets/") and entry.type == "blob"
    }
    expected_assets = {
        presentation["media"]["assetPath"]
        for presentation in board["presentations"]
    }
    _validate_remote_asset_inventory(set(asset_entries), expected_assets)
    selected_value = (
        next(item for item in board["presentations"] if item["isDefault"])
        if presentation_id is None
        else next(
            (item for item in board["presentations"] if item["id"] == presentation_id),
            None,
        )
    )
    if selected_value is None:
        raise board_package.BoardPackageError("presentation is not available")
    selected_asset = selected_value["media"]["assetPath"]
    image = _get_blob(
        client, token, asset_entries[selected_asset], "package presentation image"
    )
    width, height = board_package._png_dimensions_from_bytes(image)
    image_aspect_ratio = width / height
    relative_error = abs(selected_value["aspectRatio"] - image_aspect_ratio) / image_aspect_ratio
    if relative_error > board_package._ASPECT_RATIO_RELATIVE_TOLERANCE:
        raise board_package.BoardPackageError(
            f"board.json presentation {selected_value['id']}.aspectRatio must match its image width/height within 0.1%"
        )

    # Only the selected presentation reaches the editor document.  Sibling
    # dimensions are deliberately deferred to their own image request or save.
    presentations = tuple(
        board_package.BoardPresentation(
            id=item["id"],
            name=item["name"],
            asset_path=item["media"]["assetPath"],
            aspect_ratio=item["aspectRatio"],
            is_default=item["isDefault"],
            image_width=width,
            image_height=height,
            source_presentation_id=item["derivation"].get("sourcePresentationID"),
            is_inverted=item["derivation"].get("isInverted", False),
        )
        for item in board["presentations"]
    )
    return (
        GitHubBoardPackage(
            slug,
            board,
            width,
            height,
            board_entry.sha,
            presentations,
            schema_version=3,
        ),
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
    asset_entries = {
        path: entry
        for path, entry in entries.items()
        if path.startswith("assets/") and entry.type == "blob"
    }
    images: dict[str, bytes] = {}
    dimensions: dict[str, tuple[int, int]] = {}
    board_entry = entries["board.json"]
    if prevalidated_board is None:
        board_blob = _get_blob(
            client, token, board_entry, "board.json", blob_slots=blob_slots
        )
        board = _load_board_json(board_blob)
    else:
        board = deepcopy(prevalidated_board)
        board_blob = _get_blob(
            client, token, board_entry, "board.json", blob_slots=blob_slots
        )
        if _load_board_json(board_blob) != board:
            raise board_package.BoardPackageError("board.json changed during loading")
    board_package.validate_catalog_board(board)
    model_only = not board_package._board_editor_available(board)
    expected_assets = {
        path
        for presentation in board["presentations"]
        for path in (
            presentation["media"]["assetPath"],
            *((presentation["media"]["descriptorPath"],)
              if presentation["media"]["type"] == "model" else ()),
        )
    }
    _validate_remote_asset_inventory(set(asset_entries), expected_assets)
    if model_only:
        presentations = tuple(
            board_package.BoardPresentation(
                id=item["id"],
                name=item["name"],
                asset_path=item["media"]["assetPath"],
                aspect_ratio=item["aspectRatio"],
                is_default=item["isDefault"],
                image_width=0,
                image_height=0,
                media_type="model",
                descriptor_path=item["media"]["descriptorPath"],
            )
            for item in board["presentations"]
        )
        package = GitHubBoardPackage(
            slug, board, 0, 0, board_entry.sha, presentations, schema_version=3,
        )
        return (package, {}) if include_image else package

    raster_entries = {
        presentation["media"]["assetPath"]: asset_entries[presentation["media"]["assetPath"]]
        for presentation in board["presentations"]
    }
    with ThreadPoolExecutor(
        max_workers=min(_MAX_CONCURRENT_PACKAGE_LOADS, max(1, len(raster_entries)))
    ) as executor:
        image_futures = {
            asset_path: executor.submit(
                _get_blob,
                client,
                token,
                image_entry,
                "package presentation image",
                stage_cache_miss=True,
                blob_slots=blob_slots,
            )
            for asset_path, image_entry in raster_entries.items()
        }
        for asset_path in sorted(raster_entries):
            image = image_futures[asset_path].result()
            images[asset_path] = image
            dimensions[asset_path] = (
                board_package._png_header_dimensions_from_bytes(image[:33])
                if inspect_png_header_only
                else board_package._png_dimensions_from_bytes(image)
            )
    presentations = tuple(
        board_package.BoardPresentation(
            id=item["id"],
            name=item["name"],
            asset_path=item["media"]["assetPath"],
            aspect_ratio=item["aspectRatio"],
            is_default=item["isDefault"],
            image_width=dimensions[item["media"]["assetPath"]][0],
            image_height=dimensions[item["media"]["assetPath"]][1],
            source_presentation_id=item["derivation"].get("sourcePresentationID"),
            is_inverted=item["derivation"].get("isInverted", False),
        )
        for item in board["presentations"]
    )
    for item in board["presentations"]:
        width, height = dimensions[item["media"]["assetPath"]]
        image_aspect_ratio = width / height
        relative_error = abs(item["aspectRatio"] - image_aspect_ratio) / image_aspect_ratio
        if relative_error > board_package._ASPECT_RATIO_RELATIVE_TOLERANCE:
            raise board_package.BoardPackageError(
                f"board.json presentation {item['id']}.aspectRatio must match "
                "its image width/height within 0.1%"
            )
    default = next(item for item in presentations if item.is_default)
    package = GitHubBoardPackage(
        slug, board, default.image_width, default.image_height, board_entry.sha,
        presentations, schema_version=3,
    )
    if not inspect_png_header_only:
        for presentation in presentations:
            board_package.editor_document(package, presentation.id)
    if isinstance(client, _CachedSnapshotClient):
        client.cache_blobs_in_order(
            tuple(
                (raster_entries[asset_path].sha, images[asset_path])
                for asset_path in sorted(raster_entries)
            )
        )
    return (package, images) if include_image else package


def _validate_remote_asset_inventory(
    actual_assets: set[str], expected_assets: set[str]
) -> None:
    missing = expected_assets - actual_assets
    if missing:
        raise board_package.BoardPackageError(
            f"missing declared presentation asset: {sorted(missing)[0]}"
        )
    unknown = actual_assets - expected_assets
    if unknown:
        raise board_package.BoardPackageError(
            f"undeclared presentation asset: {sorted(unknown)[0]}"
        )


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
                "missing declared presentation asset: assets/primary.png"
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
