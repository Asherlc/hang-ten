from __future__ import annotations

import copy
import hashlib
import json
import shutil
import struct
import sys
import threading
import zlib
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package
import github_board_store
from fake_github_client import FakeGitHubClient
from github_client import GitHubForbiddenError, GitHubNotFoundError
from workbench_fixtures import PRIMARY_IMAGE, board_document, board_document_v2

TOKEN = "test-token"
BRANCH = "main"


def _encoded_board(board: dict[str, object]) -> bytes:
    return (json.dumps(board, indent=2) + "\n").encode("utf-8")


def _complete_package(slug: str, board: dict[str, object]) -> dict[str, bytes]:
    return {
        f"Hangboards/{slug}/board.json": _encoded_board(board),
        f"Hangboards/{slug}/assets/primary.png": PRIMARY_IMAGE.read_bytes(),
    }


def _client(*packages: tuple[str, dict[str, object]]) -> FakeGitHubClient:
    files: dict[str, bytes] = {}
    for slug, board in packages:
        files.update(_complete_package(slug, board))
    return FakeGitHubClient({BRANCH: files})


class _TreeRaceClient(FakeGitHubClient):
    def __init__(
        self, original: dict[str, object], replacement: dict[str, object]
    ) -> None:
        super().__init__({BRANCH: _complete_package("fixture-board", original)})
        self._replacement = _encoded_board(replacement)
        self._raced = False

    def get_tree(self, token: str, branch: str):
        tree = super().get_tree(token, branch)
        if not self._raced:
            self._raced = True
            board_entry = next(
                entry
                for entry in tree
                if entry.path == "Hangboards/fixture-board/board.json"
            )
            super().put_file(
                token,
                "Hangboards/fixture-board/board.json",
                branch,
                self._replacement,
                "Concurrent board rename",
                board_entry.sha,
            )
        return tree


class _RelocatingTreeClient(FakeGitHubClient):
    def __init__(self) -> None:
        self.moved_image = _primary_image_with_text_chunk(b"moved-board")
        super().__init__(
            {
                BRANCH: _complete_package(
                    "fixture-board", board_document("fixture.board")
                )
            }
        )
        self._raced = False

    def get_tree(self, token: str, branch: str):
        tree = super().get_tree(token, branch)
        if not self._raced:
            self._raced = True
            board_entry = next(
                entry
                for entry in tree
                if entry.path == "Hangboards/fixture-board/board.json"
            )
            super().put_file(
                token,
                "Hangboards/fixture-board/board.json",
                branch,
                _encoded_board(board_document("different.board")),
                "Concurrent board rename",
                board_entry.sha,
            )
            super().put_file(
                token,
                "Hangboards/moved-board/assets/primary.png",
                branch,
                self.moved_image,
                "Concurrent board move",
                None,
            )
            super().put_file(
                token,
                "Hangboards/moved-board/board.json",
                branch,
                _encoded_board(board_document("fixture.board")),
                "Concurrent board move",
                None,
            )
        return tree


class _EntryTypeClient(FakeGitHubClient):
    def __init__(self, files: dict[str, bytes], path: str) -> None:
        super().__init__({BRANCH: files})
        self._path = path

    def get_tree(self, token: str, branch: str):
        return tuple(
            replace(entry, type="tree") if entry.path == self._path else entry
            for entry in super().get_tree(token, branch)
        )


class _ConcurrentSaveClient(FakeGitHubClient):
    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__({BRANCH: files})
        self._raced = False

    def put_file(self, token, path, branch, content, message, sha):
        if not self._raced:
            self._raced = True
            current_sha = next(
                entry.sha
                for entry in super().get_tree(token, branch)
                if entry.path == path
            )
            super().put_file(
                token,
                path,
                branch,
                b'{"concurrent":true}\n',
                "Concurrent write",
                current_sha,
            )
        return super().put_file(token, path, branch, content, message, sha)


class _ForbiddenSaveClient(FakeGitHubClient):
    def put_file(self, token, path, branch, content, message, sha):
        raise GitHubForbiddenError("write denied")


class _OverlappingBlobClient(FakeGitHubClient):
    """Requires concurrent blob reads without changing their returned bytes."""

    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__({BRANCH: files})
        self._lock = threading.Lock()
        self._barrier = threading.Barrier(2, timeout=5)
        self._barrier_waiters_remaining = 2
        self._active_blob_reads = 0
        self.max_active_blob_reads = 0

    def get_blob(self, token: str, sha: str) -> bytes:
        with self._lock:
            self._active_blob_reads += 1
            wait_for_overlap = self._barrier_waiters_remaining > 0
            if wait_for_overlap:
                self._barrier_waiters_remaining -= 1
            self.max_active_blob_reads = max(
                self.max_active_blob_reads, self._active_blob_reads
            )
        try:
            if wait_for_overlap:
                try:
                    self._barrier.wait()
                except threading.BrokenBarrierError:
                    pass
            return super().get_blob(token, sha)
        finally:
            with self._lock:
                self._active_blob_reads -= 1


class _OneTimeMissingBlobClient(FakeGitHubClient):
    """Makes the first blob lookup unavailable, then serves the same blob."""

    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__({BRANCH: files})
        self._failed = False

    def get_blob(self, token: str, sha: str) -> bytes:
        content = super().get_blob(token, sha)
        if not self._failed:
            self._failed = True
            raise GitHubNotFoundError("blob is not available")
        return content


class _FirstPackageFailureClient(FakeGitHubClient):
    """Fails the first package image once and records which packages began."""

    def __init__(self, files: dict[str, bytes], failing_sha: str) -> None:
        super().__init__({BRANCH: files})
        self._failing_sha = failing_sha
        self._failed = False
        self._started = threading.Condition()
        self._image_barrier = threading.Barrier(
            github_board_store._MAX_CONCURRENT_PACKAGE_LOADS, timeout=5
        )
        self.started_shas: set[str] = set()

    def get_blob(self, token: str, sha: str) -> bytes:
        with self._started:
            self.started_shas.add(sha)
            is_initial_image = (
                len(self.started_shas)
                <= github_board_store._MAX_CONCURRENT_PACKAGE_LOADS
            )
            self._started.notify_all()
        if is_initial_image:
            self._image_barrier.wait()
        if sha == self._failing_sha and not self._failed:
            self._failed = True
            super().get_blob(token, sha)
            raise GitHubNotFoundError("blob is not available")
        return super().get_blob(token, sha)

    def wait_for_started(self, count: int) -> set[str]:
        with self._started:
            assert self._started.wait_for(
                lambda: len(self.started_shas) >= count, timeout=5
            )
            return set(self.started_shas)


class _RejectingExecutor:
    """Records the initial worker window, then rejects its first package."""

    def __init__(self) -> None:
        self.submitted_slugs: list[str] = []
        self._futures: list[Future[github_board_store.GitHubBoardPackage]] = []

    def submit(self, operation, *args, **kwargs):
        del operation, kwargs
        self.submitted_slugs.append(args[2])
        future: Future[github_board_store.GitHubBoardPackage] = Future()
        self._futures.append(future)
        if len(self._futures) == 1:
            future.set_exception(
                board_package.BoardPackageError("catalog load stopped")
            )
        return future

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        del wait
        if cancel_futures:
            for future in self._futures:
                future.cancel()


class _PausedConfiguredWindowClient(FakeGitHubClient):
    """Pauses blob reads so the configured package-load width is observable."""

    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__({BRANCH: files})
        self._active = threading.Condition()
        self._active_blob_reads = 0
        self.max_active_blob_reads = 0
        self.release = threading.Event()

    def get_blob(self, token: str, sha: str) -> bytes:
        with self._active:
            self._active_blob_reads += 1
            self.max_active_blob_reads = max(
                self.max_active_blob_reads, self._active_blob_reads
            )
            self._active.notify_all()
        try:
            assert self.release.wait(timeout=5)
            return super().get_blob(token, sha)
        finally:
            with self._active:
                self._active_blob_reads -= 1

    def wait_for_active(self, count: int) -> int:
        with self._active:
            self._active.wait_for(
                lambda: self.max_active_blob_reads >= count, timeout=1
            )
            return self.max_active_blob_reads


class _PausedBulkClient(FakeGitHubClient):
    """Pauses a bulk blob read while exposing later control-call progress."""

    def __init__(self, files: dict[str, bytes]) -> None:
        super().__init__({BRANCH: files})
        self.bulk_started = threading.Event()
        self.release_bulk = threading.Event()
        self.second_head_completed = threading.Event()
        self._head_lock = threading.Lock()
        self._head_calls = 0

    def get_branch_head_sha(self, token: str, branch: str) -> str:
        head = super().get_branch_head_sha(token, branch)
        with self._head_lock:
            self._head_calls += 1
            if self._head_calls == 2:
                self.second_head_completed.set()
        return head

    def get_blob(self, token: str, sha: str) -> bytes:
        self.bulk_started.set()
        assert self.release_bulk.wait(timeout=5)
        return super().get_blob(token, sha)


def _local_package_error(
    tmp_path: Path,
    *,
    board_as_directory: bool = False,
    image_as_directory: bool = False,
) -> str:
    package = tmp_path / "fixture-board"
    assets = package / "assets"
    assets.mkdir(parents=True)
    board_path = package / "board.json"
    image_path = assets / "primary.png"
    if board_as_directory:
        board_path.mkdir()
    else:
        board_path.write_bytes(_encoded_board(board_document("fixture.board")))
    if image_as_directory:
        image_path.mkdir()
    else:
        shutil.copyfile(PRIMARY_IMAGE, image_path)
    with pytest.raises(board_package.BoardPackageError) as captured:
        board_package.load_board_package(package)
    return str(captured.value)


def _primary_image_with_text_chunk(text: bytes) -> bytes:
    chunk_type = b"tEXt"
    chunk = (
        struct.pack(">I", len(text))
        + chunk_type
        + text
        + struct.pack(">I", zlib.crc32(chunk_type + text) & 0xFFFFFFFF)
    )
    image = PRIMARY_IMAGE.read_bytes()
    return image[:-12] + chunk + image[-12:]


def test_discover_and_open_remote_package_expose_the_local_editor_contract() -> None:
    client = _client(("fixture-board", board_document("fixture.board")))

    discovered = github_board_store.discover_packages(client, TOKEN, BRANCH)
    assert len(client.calls_named("get_tree")) == 1
    opened = github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")

    assert [
        (package.slug, package.board_id, package.hold_ids) for package in discovered
    ] == [("fixture-board", "fixture.board", ("hold-left",))]
    assert (opened.image_width, opened.image_height) == (1774, 457)
    assert board_package.editor_document(opened)["canvas"] == {
        "width": 1774,
        "height": 457,
    }


def test_cold_discovery_loads_completed_packages_concurrently_in_sorted_order() -> None:
    """Fails if catalog loading serializes independent package blob reads."""
    client = _OverlappingBlobClient(
        {
            **_complete_package("zeta", board_document("zeta.board")),
            **_complete_package("alpha", board_document("alpha.board")),
            **_complete_package("middle", board_document("middle.board")),
            **_complete_package("delta", board_document("delta.board")),
            **_complete_package("bravo", board_document("bravo.board")),
            **_complete_package("echo", board_document("echo.board")),
        }
    )

    packages = github_board_store.discover_packages(client, TOKEN, BRANCH)

    assert [package.board_id for package in packages] == [
        "alpha.board",
        "bravo.board",
        "delta.board",
        "echo.board",
        "middle.board",
        "zeta.board",
    ]
    assert 2 <= client.max_active_blob_reads <= 4


def test_cached_catalog_avoids_rescanning_over_capacity_images_for_open_and_image() -> None:
    """Fails if an LRU blob scan evicts catalog data before an addressed read."""
    files: dict[str, bytes] = {}
    for slug in ("alpha", "bravo", "charlie", "delta", "echo"):
        files.update(_complete_package(slug, board_document(f"{slug}.board")))
        files[f"Hangboards/{slug}/assets/primary.png"] = _primary_image_with_text_chunk(
            slug.encode("utf-8")
        )
    client = FakeGitHubClient({BRANCH: files})
    store = github_board_store.GitHubBoardStore(
        client, max_cached_blob_bytes=1, max_cached_blobs=1
    )

    listed = store.discover_packages(TOKEN, BRANCH)
    opened = store.open_package(TOKEN, BRANCH, "charlie.board")
    image = store.primary_image_bytes(TOKEN, BRANCH, "charlie.board")

    assert [package.board_id for package in listed] == [
        "alpha.board",
        "bravo.board",
        "charlie.board",
        "delta.board",
        "echo.board",
    ]
    assert opened.board_id == "charlie.board"
    assert image == files["Hangboards/charlie/assets/primary.png"]
    assert len(client.calls_named("get_blob")) == 14


def test_cached_store_reloads_a_tree_evicted_at_its_configured_capacity() -> None:
    """Fails if max_cached_trees does not evict the least-recent snapshot."""
    files = _complete_package("fixture-board", board_document("fixture.board"))
    client = FakeGitHubClient({"first": files, "second": files})
    store = github_board_store.GitHubBoardStore(client, max_cached_trees=1)

    store.discover_packages(TOKEN, "first")
    store.discover_packages(TOKEN, "second")
    store.discover_packages(TOKEN, "first")

    assert len(client.calls_named("get_tree")) == 3


def test_cached_store_skips_trees_larger_than_its_configured_byte_limit() -> None:
    """Fails if max_cached_tree_bytes retains an oversized tree payload."""
    client = _client(("fixture-board", board_document("fixture.board")))
    store = github_board_store.GitHubBoardStore(client, max_cached_tree_bytes=1)

    store.discover_packages(TOKEN, BRANCH)
    store.discover_packages(TOKEN, BRANCH)

    assert len(client.calls_named("get_tree")) == 2


def test_cached_store_skips_trees_larger_than_its_configured_entry_limit() -> None:
    """Fails if a tree-entry limit also prevents catalog caching."""
    client = _client(
        ("alpha", board_document("alpha.board")),
        ("bravo", board_document("bravo.board")),
    )
    store = github_board_store.GitHubBoardStore(client, max_cached_tree_entries=1)

    store.discover_packages(TOKEN, BRANCH)
    store.discover_packages(TOKEN, BRANCH)

    assert len(client.calls_named("get_tree")) == 2
    assert len(client.calls_named("get_blob")) == 4


def test_control_calls_progress_while_a_bulk_catalog_read_is_paused() -> None:
    """Fails if bulk catalog work consumes the control-call request budget."""
    files = _complete_package("fixture-board", board_document("fixture.board"))
    client = _PausedBulkClient(files)
    store = github_board_store.GitHubBoardStore(
        client,
        max_concurrent_package_loads=1,
        max_concurrent_control_calls=1,
    )
    catalogs: list[tuple[github_board_store.GitHubBoardPackage, ...]] = []

    def discover() -> None:
        catalogs.append(store.discover_packages(TOKEN, BRANCH))

    first = threading.Thread(target=discover)
    second = threading.Thread(target=discover)
    first.start()
    try:
        assert client.bulk_started.wait(timeout=5)
        second.start()
        assert client.second_head_completed.wait(timeout=1)
    finally:
        client.release_bulk.set()
        first.join(timeout=5)
        second.join(timeout=5)
        store.close()

    assert len(catalogs) == 2
    assert not first.is_alive()
    assert not second.is_alive()


@pytest.mark.parametrize(
    "limit",
    ["max_concurrent_package_loads", "max_concurrent_control_calls"],
)
def test_cached_store_rejects_nonpositive_request_limits(limit: str) -> None:
    """Fails if a zero request budget can deadlock store operations."""
    client = _client(("fixture-board", board_document("fixture.board")))

    with pytest.raises(ValueError, match="limits must be positive"):
        github_board_store.GitHubBoardStore(client, **{limit: 0})


def test_cached_store_reloads_a_catalog_evicted_at_its_capacity() -> None:
    """Fails if catalog capacity does not evict the least-recent commit metadata."""
    files = _complete_package("fixture-board", board_document("fixture.board"))
    branches = {"first": files, "second": files}
    client = FakeGitHubClient(branches)
    store = github_board_store.GitHubBoardStore(client, max_cached_catalogs=1)

    store.discover_packages(TOKEN, "first")
    store.discover_packages(TOKEN, "second")
    store.discover_packages(TOKEN, "first")

    assert len(client.calls_named("get_blob")) == 6


def test_cached_store_skips_catalogs_larger_than_its_configured_byte_limit() -> None:
    """Fails if max_cached_catalog_bytes retains oversized board metadata."""
    client = _client(("fixture-board", board_document("fixture.board")))
    store = github_board_store.GitHubBoardStore(client, max_cached_catalog_bytes=1)

    store.discover_packages(TOKEN, BRANCH)
    store.discover_packages(TOKEN, BRANCH)

    assert len(client.calls_named("get_blob")) == 4


def test_cached_store_evicts_old_blobs_at_its_configured_capacity() -> None:
    """Fails if cache capacity lets immutable blobs grow without eviction."""
    client = _client(("fixture-board", board_document("fixture.board")))
    store = github_board_store.GitHubBoardStore(
        client, max_cached_blobs=1, max_cached_blob_bytes=1024 * 1024
    )

    store.discover_packages(TOKEN, BRANCH)
    store.open_package(TOKEN, BRANCH, "fixture.board")
    store.primary_image_bytes(TOKEN, BRANCH, "fixture.board")

    assert len(client.calls_named("get_blob")) == 6


def test_cached_store_does_not_reuse_a_failed_blob_read() -> None:
    """Fails if a transient GitHub blob failure is retained as a cache entry."""
    client = _OneTimeMissingBlobClient(
        _complete_package("fixture-board", board_document("fixture.board"))
    )
    store = github_board_store.GitHubBoardStore(client)

    with pytest.raises(
        board_package.BoardPackageError, match="primary image is missing"
    ):
        store.discover_packages(TOKEN, BRANCH)
    packages = store.discover_packages(TOKEN, BRANCH)

    assert [package.board_id for package in packages] == ["fixture.board"]
    assert len(client.calls_named("get_blob")) == 3


def test_cached_store_partitions_immutable_reads_by_credential() -> None:
    """Fails if one credential can consume another credential's cache entries."""
    client = _client(("fixture-board", board_document("fixture.board")))
    store = github_board_store.GitHubBoardStore(client)

    store.discover_packages("first-token", BRANCH)
    store.discover_packages("second-token", BRANCH)

    assert len(client.calls_named("get_tree")) == 2
    assert len(client.calls_named("get_blob")) == 4


def test_discovery_submits_only_one_worker_window_after_an_early_failure() -> None:
    """Fails if a failed source-ordered package starts later queued packages."""
    files: dict[str, bytes] = {}
    for slug in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
        files.update(_complete_package(slug, board_document(f"{slug}.board")))
        files[f"Hangboards/{slug}/assets/primary.png"] = _primary_image_with_text_chunk(
            slug.encode("utf-8")
        )
    failing_sha = FakeGitHubClient._sha(files["Hangboards/alpha/assets/primary.png"])
    client = _FirstPackageFailureClient(files, failing_sha)
    store = github_board_store.GitHubBoardStore(client)

    with pytest.raises(board_package.BoardPackageError, match="primary image is missing"):
        store.discover_packages(TOKEN, BRANCH)
    started_before_retry = client.wait_for_started(7)
    packages = store.discover_packages(TOKEN, BRANCH)

    assert [package.board_id for package in packages] == [
        "alpha.board",
        "bravo.board",
        "charlie.board",
        "delta.board",
        "echo.board",
        "foxtrot.board",
    ]
    assert len(started_before_retry) == 7


@pytest.mark.parametrize("max_concurrent_package_loads", [0, -1])
@pytest.mark.parametrize("supply_executor", [False, True])
def test_discovery_rejects_nonpositive_package_load_limits(
    max_concurrent_package_loads: int, supply_executor: bool
) -> None:
    """Fails if the public discovery helper accepts an unusable worker budget."""
    client = _client(("fixture-board", board_document("fixture.board")))

    with ThreadPoolExecutor(max_workers=1) as pool:
        executor = pool if supply_executor else None
        with pytest.raises(ValueError, match="limits must be positive"):
            github_board_store.discover_packages(
                client,
                TOKEN,
                BRANCH,
                executor=executor,
                max_concurrent_package_loads=max_concurrent_package_loads,
            )

    assert not client.calls_named("get_tree")


def test_cached_store_submits_its_configured_smaller_package_load_window() -> None:
    """Fails if a lower configured worker limit still queues the default window."""
    files: dict[str, bytes] = {}
    for slug in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
        files.update(_complete_package(slug, board_document(f"{slug}.board")))
    store = github_board_store.GitHubBoardStore(
        FakeGitHubClient({BRANCH: files}), max_concurrent_package_loads=2
    )
    store._executor.shutdown()
    executor = _RejectingExecutor()
    store._executor = executor

    try:
        with pytest.raises(board_package.BoardPackageError, match="catalog load stopped"):
            store.discover_packages(TOKEN, BRANCH)
    finally:
        store.close()

    assert executor.submitted_slugs == ["alpha", "bravo"]


def test_cached_store_uses_its_configured_larger_package_load_window() -> None:
    """Fails if a higher configured worker limit remains capped at the default."""
    files: dict[str, bytes] = {}
    for slug in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
        files.update(_complete_package(slug, board_document(f"{slug}.board")))
        files[f"Hangboards/{slug}/assets/primary.png"] = _primary_image_with_text_chunk(
            slug.encode("utf-8")
        )
    client = _PausedConfiguredWindowClient(files)
    store = github_board_store.GitHubBoardStore(
        client, max_concurrent_package_loads=6
    )

    with ThreadPoolExecutor(max_workers=1) as requests:
        discovery = requests.submit(store.discover_packages, TOKEN, BRANCH)
        try:
            active_before_release = client.wait_for_active(6)
        finally:
            client.release.set()
        try:
            packages = discovery.result(timeout=5)
        finally:
            store.close()

    assert len(packages) == 6
    assert active_before_release == 6


def test_snapshot_rejects_a_branch_other_than_its_pinned_branch() -> None:
    """Fails if a snapshot can read or mutate a branch it did not pin."""
    client = _client(("fixture-board", board_document("fixture.board")))
    store = github_board_store.GitHubBoardStore(client)
    snapshot = store._snapshot(TOKEN, BRANCH, cache_blobs=True)

    with pytest.raises(RuntimeError, match="branch does not match"):
        snapshot.get_tree(TOKEN, "other")
    with pytest.raises(RuntimeError, match="branch does not match"):
        snapshot.put_file(TOKEN, "new.txt", "other", b"new", "Add file", None)

    store.close()


@pytest.mark.parametrize(
    "read",
    [
        lambda client: github_board_store.open_package(
            client, TOKEN, BRANCH, "fixture.board"
        ),
        lambda client: github_board_store.primary_image_bytes(
            client, TOKEN, BRANCH, "fixture.board"
        ),
    ],
    ids=["open", "primary-image"],
)
def test_id_addressed_reads_reject_a_slug_renamed_during_authoritative_reload(
    read,
) -> None:
    client = _TreeRaceClient(
        board_document("fixture.board"), board_document("different.board")
    )

    with pytest.raises(board_package.BoardNotAvailableError, match="not available"):
        read(client)


def test_id_addressed_reads_reresolve_a_board_moved_to_a_new_slug() -> None:
    open_client = _RelocatingTreeClient()

    opened = github_board_store.open_package(
        open_client, TOKEN, BRANCH, "fixture.board"
    )

    assert (opened.slug, opened.board_id) == ("moved-board", "fixture.board")
    image_client = _RelocatingTreeClient()
    assert (
        github_board_store.primary_image_bytes(
            image_client, TOKEN, BRANCH, "fixture.board"
        )
        == image_client.moved_image
    )


def test_discovery_rejects_duplicate_remote_board_ids() -> None:
    client = _client(
        ("first-board", board_document("duplicate.board")),
        ("second-board", board_document("duplicate.board")),
    )

    with pytest.raises(board_package.BoardPackageError, match="duplicate board ID"):
        github_board_store.discover_packages(client, TOKEN, BRANCH)


@pytest.mark.parametrize(
    ("path", "local_kwargs"),
    [
        ("Hangboards/fixture-board/board.json", {"board_as_directory": True}),
        (
            "Hangboards/fixture-board/assets/primary.png",
            {"image_as_directory": True},
        ),
    ],
    ids=["board-json-tree", "primary-image-tree"],
)
def test_tree_entry_type_errors_match_local_package_loading(
    path: str, local_kwargs: dict[str, bool], tmp_path: Path
) -> None:
    expected = _local_package_error(tmp_path, **local_kwargs)
    client = _EntryTypeClient(
        _complete_package("fixture-board", board_document("fixture.board")), path
    )

    with pytest.raises(board_package.BoardPackageError) as captured:
        github_board_store.discover_packages(client, TOKEN, BRANCH)

    assert str(captured.value) == expected


def test_discovery_checks_the_png_before_jointly_invalid_board_json(
    tmp_path: Path,
) -> None:
    package = tmp_path / "fixture-board"
    (package / "assets").mkdir(parents=True)
    (package / "board.json").write_bytes(b"not JSON")
    (package / "assets" / "primary.png").write_bytes(b"not a PNG")
    with pytest.raises(board_package.BoardPackageError) as local_error:
        board_package.load_board_package(package)
    client = FakeGitHubClient(
        {
            BRANCH: {
                "Hangboards/fixture-board/board.json": b"not JSON",
                "Hangboards/fixture-board/assets/primary.png": b"not a PNG",
            }
        }
    )

    with pytest.raises(board_package.BoardPackageError) as remote_error:
        github_board_store.discover_packages(client, TOKEN, BRANCH)

    assert str(remote_error.value) == str(local_error.value)


def test_discovery_rejects_a_completed_package_with_extra_remote_files() -> None:
    files = _complete_package("fixture-board", board_document("fixture.board"))
    files["Hangboards/fixture-board/notes.txt"] = b"not part of a board package"
    client = FakeGitHubClient({BRANCH: files})

    with pytest.raises(
        board_package.BoardPackageError,
        match="only board.json and assets/primary.png",
    ):
        github_board_store.discover_packages(client, TOKEN, BRANCH)


def test_open_rejects_geometry_that_header_only_discovery_defers() -> None:
    board = board_document("fixture.board")
    hold = board["holds"][0]
    assert isinstance(hold, dict)
    piece = hold["geometry"][0]
    assert isinstance(piece, dict)
    piece["shape"] = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0, 0]},
            {"command": "line", "to": [1, 1]},
            {"command": "line", "to": [1, 0]},
            {"command": "line", "to": [0, 1]},
            {"command": "close"},
        ],
    }
    client = _client(("fixture-board", board))

    assert (
        github_board_store.discover_packages(client, TOKEN, BRANCH)[0].board_id
        == "fixture.board"
    )
    with pytest.raises(
        board_package.BoardPackageError, match="must not self-intersect"
    ):
        github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")


def test_header_only_discovery_defers_post_ihdr_png_corruption() -> None:
    image = bytearray(PRIMARY_IMAGE.read_bytes())
    image[-1] ^= 0xFF
    client = FakeGitHubClient(
        {
            BRANCH: {
                **_complete_package("fixture-board", board_document("fixture.board")),
                "Hangboards/fixture-board/assets/primary.png": bytes(image),
            }
        }
    )

    assert (
        github_board_store.discover_packages(client, TOKEN, BRANCH)[0].board_id
        == "fixture.board"
    )
    with pytest.raises(board_package.BoardPackageError, match="decodable PNG"):
        github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")
    with pytest.raises(board_package.BoardPackageError, match="decodable PNG"):
        github_board_store.primary_image_bytes(client, TOKEN, BRANCH, "fixture.board")


def test_noop_save_uses_the_live_sha_without_writing_to_github() -> None:
    client = _client(("fixture-board", board_document("fixture.board")))
    opened = github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")
    document = board_package.editor_document(opened)

    saved, commit_sha = github_board_store.save_editor_document(
        client, TOKEN, BRANCH, "fixture-board", document
    )

    assert saved.board == opened.board
    assert commit_sha == opened.board_json_sha
    assert client.calls_named("put_file") == ()


def test_changed_save_merges_editor_changes_and_returns_the_commit_sha() -> None:
    board = board_document("fixture.board")
    board["holds"][0]["sizeMillimeters"] = 20
    client = _client(("fixture-board", board))
    document = board_package.editor_document(
        github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")
    )
    document = copy.deepcopy(document)
    for region in document["regions"]:
        region["type"] = "edge"

    saved, commit_sha = github_board_store.save_editor_document(
        client, TOKEN, BRANCH, "fixture-board", document
    )

    stored = json.loads(
        client.file_bytes(BRANCH, "Hangboards/fixture-board/board.json")
    )
    assert saved.board["holds"][0]["kind"] == "edge"
    assert stored["holds"][0]["name"] == "Left hold"
    assert stored["holds"][0]["sizeMillimeters"] == 20
    assert commit_sha != saved.board_json_sha
    assert (
        saved.board_json_sha
        == github_board_store.open_package(
            client, TOKEN, BRANCH, "fixture.board"
        ).board_json_sha
    )
    put = client.calls_named("put_file")
    assert len(put) == 1
    assert put[0].args[4] == "Update fixture.board"
    expected_content = (json.dumps(saved.board, indent=2) + "\n").encode("utf-8")
    expected_sha = hashlib.sha1(
        f"blob {len(expected_content)}\0".encode() + expected_content
    ).hexdigest()
    assert put[0].args[3] == expected_content
    assert saved.board_json_sha == expected_sha


def test_v2_hosted_save_preserves_unselected_holds_and_presentation_assets() -> None:
    board = board_document_v2("fixture.v2")
    files = _complete_package("fixture-v2", board)
    files["Hangboards/fixture-v2/assets/back.png"] = PRIMARY_IMAGE.read_bytes()
    client = FakeGitHubClient({BRANCH: files})
    opened = github_board_store.open_package(client, TOKEN, BRANCH, "fixture.v2")
    document = board_package.editor_document(opened, "front")
    back_before = copy.deepcopy(opened.board["holds"][1])
    assets_before = {
        path: client.file_bytes(BRANCH, path)
        for path in (
            "Hangboards/fixture-v2/assets/primary.png",
            "Hangboards/fixture-v2/assets/back.png",
        )
    }
    for region in document["regions"]:
        region["type"] = "sloper"

    saved, _commit_sha = github_board_store.save_editor_document(
        client, TOKEN, BRANCH, "fixture-v2", document
    )

    assert next(hold for hold in saved.board["holds"] if hold["id"] == "hold-back") == back_before
    assert github_board_store.presentation_image_bytes(
        client, TOKEN, BRANCH, "fixture.v2", "back"
    ) == assets_before["Hangboards/fixture-v2/assets/back.png"]
    assert {
        path: client.file_bytes(BRANCH, path) for path in assets_before
    } == assets_before


def test_stale_sha_conflict_becomes_a_board_save_conflict() -> None:
    client = _ConcurrentSaveClient(
        _complete_package("fixture-board", board_document("fixture.board"))
    )
    document = board_package.editor_document(
        github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")
    )
    document = copy.deepcopy(document)
    for region in document["regions"]:
        region["type"] = "edge"
    with pytest.raises(board_package.BoardSaveConflictError, match="file changed"):
        github_board_store.save_editor_document(
            client, TOKEN, BRANCH, "fixture-board", document
        )


def test_save_rejects_a_replaced_slug_identity_before_writing() -> None:
    original = _client(("fixture-board", board_document("fixture.board")))
    document = copy.deepcopy(
        board_package.editor_document(
            github_board_store.open_package(
                original, TOKEN, BRANCH, "fixture.board"
            )
        )
    )
    for region in document["regions"]:
        region["type"] = "edge"
    replaced = _client(("fixture-board", board_document("different.board")))

    with pytest.raises(
        board_package.BoardSaveConflictError, match="identity changed"
    ):
        github_board_store.save_editor_document(
            replaced,
            TOKEN,
            BRANCH,
            "fixture-board",
            document,
            expected_board_id="fixture.board",
        )

    assert replaced.calls_named("put_file") == ()


def test_save_propagates_non_conflict_github_errors() -> None:
    client = _ForbiddenSaveClient(
        {BRANCH: _complete_package("fixture-board", board_document("fixture.board"))}
    )
    document = copy.deepcopy(
        board_package.editor_document(
            github_board_store.open_package(client, TOKEN, BRANCH, "fixture.board")
        )
    )
    for region in document["regions"]:
        region["type"] = "edge"

    with pytest.raises(GitHubForbiddenError, match="write denied"):
        github_board_store.save_editor_document(
            client, TOKEN, BRANCH, "fixture-board", document
        )
