"""Bounded background jobs for per-board workbench mutations."""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from threading import Lock
from typing import Any
from uuid import uuid4


class JobConflictError(ValueError):
    """Raised when a board already has an active mutating job."""


class JobNotFoundError(ValueError):
    """Raised when a requested job identifier is unknown."""


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
            "result": self.result,
            "error": self.error,
        }


class BoardJobManager:
    """Run bounded mutations while serializing work for each board."""

    def __init__(
        self,
        *,
        max_workers: int = 4,
        result_serializer: Callable[[object], object] | None = None,
    ) -> None:
        self.__executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="workbench"
        )
        self.__lock = Lock()
        self.__jobs: dict[str, JobRecord] = {}
        self.__active_jobs: dict[str, str] = {}
        self.__futures: dict[str, Future[None]] = {}
        self.__result_serializer = result_serializer or (lambda result: result)

    def submit(self, board_id: str, operation: Callable[[], object]) -> JobRecord:
        if not isinstance(board_id, str) or not board_id:
            raise ValueError("board id must not be empty")
        job_id = uuid4().hex
        record = JobRecord(id=job_id, board_id=board_id, state="queued")
        with self.__lock:
            if board_id in self.__active_jobs:
                raise JobConflictError(f"a job is already running for board {board_id}")
            self.__jobs[job_id] = record
            self.__active_jobs[board_id] = job_id
            try:
                self.__futures[job_id] = self.__executor.submit(
                    self.__run, job_id, operation
                )
            except Exception:
                self.__jobs.pop(job_id, None)
                self.__active_jobs.pop(board_id, None)
                raise
        return record

    def get(self, job_id: str) -> JobRecord:
        with self.__lock:
            try:
                return self.__jobs[job_id]
            except KeyError as error:
                raise JobNotFoundError(f"unknown job: {job_id}") from error

    def wait(self, job_id: str, timeout: float | None = None) -> JobRecord:
        with self.__lock:
            try:
                future = self.__futures[job_id]
            except KeyError as error:
                raise JobNotFoundError(f"unknown job: {job_id}") from error
        future.result(timeout=timeout)
        return self.get(job_id)

    def shutdown(self) -> None:
        self.__executor.shutdown(wait=True)

    def __run(self, job_id: str, operation: Callable[[], object]) -> None:
        with self.__lock:
            current = self.__jobs[job_id]
            self.__jobs[job_id] = replace(current, state="running")
        final = replace(current, state="failed", error="job failed")
        try:
            summary = self.__serializable_summary(operation())
            final = replace(current, state="succeeded", result=summary)
        except ValueError as error:
            final = replace(current, state="failed", error=str(error))
        except Exception:
            final = replace(current, state="failed", error="job failed")
        finally:
            with self.__lock:
                self.__jobs[job_id] = final
                if self.__active_jobs.get(current.board_id) == job_id:
                    self.__active_jobs.pop(current.board_id)

    def __serializable_summary(self, result: object) -> Any:
        summary = self.__result_serializer(result)
        try:
            json.dumps(summary, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("job result is not serializable") from error
        return summary
