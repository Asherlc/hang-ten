"""Bounded background jobs for per-board workbench mutations."""

from __future__ import annotations

import json
import os
from collections import deque
from collections.abc import Callable
from copy import deepcopy
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
import re
from threading import BoundedSemaphore, Lock
import tempfile
from time import monotonic
from typing import Any
from uuid import uuid4


_JOB_ID = re.compile(r"[0-9a-f]{32}\Z")


class JobConflictError(ValueError):
    """Raised when a board already has an active mutating job."""


class JobNotFoundError(ValueError):
    """Raised when a requested job identifier is unknown."""


class JobCapacityError(ValueError):
    """Raised when the bounded worker and queue capacity is exhausted."""


@dataclass(frozen=True, slots=True)
class JobRecord:
    """An immutable, JSON-safe snapshot of one background job."""

    id: str
    board_id: str
    state: str
    result: Any = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "boardId": self.board_id,
            "state": self.state,
            "result": deepcopy(self.result),
            "error": self.error,
        }


class BoardJobManager:
    """Run bounded mutations while serializing work for each board."""

    def __init__(
        self,
        *,
        max_workers: int = 4,
        result_serializer: Callable[[object], object] | None = None,
        public_error_types: tuple[type[Exception], ...] = (),
        max_queue: int | None = None,
        max_completed: int = 256,
        result_ttl_seconds: float = 3600,
        outcome_root: Path | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        queue_limit = max_workers if max_queue is None else max_queue
        if queue_limit < 0 or max_completed < 1 or result_ttl_seconds <= 0:
            raise ValueError("job capacity and retention limits must be positive")
        outcome_directory = (
            Path(outcome_root).resolve(strict=False)
            if outcome_root is not None
            else None
        )
        if outcome_directory is not None:
            outcome_directory.mkdir(parents=True, exist_ok=True)
            if not outcome_directory.is_dir():
                raise ValueError("job outcome root must be a directory")
        self.__executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="workbench"
        )
        self.__lock = Lock()
        self.__jobs: dict[str, JobRecord] = {}
        self.__active_jobs: dict[str, str] = {}
        self.__futures: dict[str, Future[None]] = {}
        self.__capacity = BoundedSemaphore(max_workers + queue_limit)
        self.__completed: deque[str] = deque()
        self.__completed_at: dict[str, float] = {}
        self.__max_completed = max_completed
        self.__result_ttl_seconds = result_ttl_seconds
        self.__result_serializer = result_serializer or (lambda result: result)
        self.__public_error_types = public_error_types
        self.__outcome_root = outcome_directory

    def submit(
        self,
        board_id: str,
        operation: Callable[[], object],
        *,
        conflict_key: str | None = None,
    ) -> JobRecord:
        if not isinstance(board_id, str) or not board_id:
            raise ValueError("board id must not be empty")
        reservation_key = conflict_key or board_id
        job_id = uuid4().hex
        record = JobRecord(id=job_id, board_id=board_id, state="queued")
        if not self.__capacity.acquire(blocking=False):
            raise JobCapacityError("job queue capacity is exhausted")
        with self.__lock:
            self.__prune_completed()
            if reservation_key in self.__active_jobs:
                self.__capacity.release()
                raise JobConflictError(f"a job is already running for board {board_id}")
            self.__jobs[job_id] = record
            self.__active_jobs[reservation_key] = job_id
            try:
                future = self.__executor.submit(
                    self.__run, job_id, reservation_key, operation
                )
                self.__futures[job_id] = future
            except Exception:
                self.__jobs.pop(job_id, None)
                self.__active_jobs.pop(reservation_key, None)
                self.__capacity.release()
                raise
        future.add_done_callback(lambda _future: self.__forget_future(job_id))
        return record

    def get(self, job_id: str) -> JobRecord:
        with self.__lock:
            self.__prune_completed()
            record = self.__jobs.get(job_id)
            if record is None:
                record = self.__read_outcome(job_id)
            if record is None:
                raise JobNotFoundError(f"unknown job: {job_id}")
            return replace(record, result=deepcopy(record.result))

    def wait(self, job_id: str, timeout: float | None = None) -> JobRecord:
        with self.__lock:
            self.__prune_completed()
            record = self.__jobs.get(job_id)
            if record is None:
                raise JobNotFoundError(f"unknown job: {job_id}")
            future = self.__futures.get(job_id)
            if future is None and record.state in {"queued", "running"}:
                raise JobNotFoundError(f"unknown job: {job_id}")
        if future is not None:
            future.result(timeout=timeout)
        return self.get(job_id)

    def shutdown(self) -> None:
        self.__executor.shutdown(wait=True)

    def __run(
        self,
        job_id: str,
        conflict_key: str,
        operation: Callable[[], object],
    ) -> None:
        with self.__lock:
            current = self.__jobs[job_id]
            self.__jobs[job_id] = replace(current, state="running")
        final = replace(current, state="failed", error="job failed")
        try:
            summary = self.__serializable_summary(operation())
            final = replace(current, state="succeeded", result=summary)
        except self.__public_error_types as error:
            final = replace(current, state="failed", error=str(error))
        except Exception:
            final = replace(current, state="failed", error="job failed")
        finally:
            try:
                self.__write_outcome(final)
            except (OSError, TypeError, ValueError):
                # The live terminal result remains available. Without a durable
                # confirmation a later restart correctly leaves the client frozen.
                pass
            with self.__lock:
                self.__jobs[job_id] = final
                if self.__active_jobs.get(conflict_key) == job_id:
                    self.__active_jobs.pop(conflict_key)
                self.__completed.append(job_id)
                self.__completed_at[job_id] = monotonic()
                self.__prune_completed()
            self.__capacity.release()

    def __serializable_summary(self, result: object) -> Any:
        summary = self.__result_serializer(result)
        try:
            encoded = json.dumps(summary, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("job result is not serializable") from error
        return json.loads(encoded)

    def __forget_future(self, job_id: str) -> None:
        with self.__lock:
            self.__futures.pop(job_id, None)

    def __write_outcome(self, record: JobRecord) -> None:
        if self.__outcome_root is None:
            return
        if _JOB_ID.fullmatch(record.id) is None:
            raise ValueError("job outcome ID is invalid")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{record.id}.", suffix=".tmp", dir=self.__outcome_root
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(record.as_dict(), stream, sort_keys=True, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.__outcome_root / f"{record.id}.json")
            directory = os.open(self.__outcome_root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def __read_outcome(self, job_id: str) -> JobRecord | None:
        if self.__outcome_root is None or _JOB_ID.fullmatch(job_id) is None:
            return None
        try:
            value = json.loads(
                (self.__outcome_root / f"{job_id}.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("id") != job_id:
            return None
        board_id = value.get("boardId")
        state = value.get("state")
        result = value.get("result")
        error = value.get("error")
        if not isinstance(board_id, str) or not board_id:
            return None
        if state == "succeeded":
            if error is not None:
                return None
        elif state == "failed":
            if result is not None or not isinstance(error, str) or not error:
                return None
        else:
            return None
        return JobRecord(
            id=job_id,
            board_id=board_id,
            state=state,
            result=deepcopy(result),
            error=error,
        )

    def __prune_completed(self) -> None:
        cutoff = monotonic() - self.__result_ttl_seconds
        while self.__completed:
            job_id = self.__completed[0]
            expired = self.__completed_at.get(job_id, 0) < cutoff
            over_limit = len(self.__completed) > self.__max_completed
            if not expired and not over_limit:
                break
            self.__completed.popleft()
            self.__completed_at.pop(job_id, None)
            self.__jobs.pop(job_id, None)
            self.__futures.pop(job_id, None)
