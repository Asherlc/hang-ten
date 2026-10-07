"""Select the immutable catalog produced for a successful CI attempt."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path


def _execution_identity(job: dict) -> tuple:
    """Job IDs and attempts change on retries; execution times and runner do not."""
    start, end = job.get("started_at"), job.get("completed_at")
    runner_id, runner_name = job.get("runner_id"), job.get("runner_name")
    if (not isinstance(start, str) or not isinstance(end, str)
            or type(runner_id) is not int or runner_id < 1
            or not isinstance(runner_name, str) or not runner_name.strip()):
        raise ValueError("successful catalog producer has no valid execution identity")
    try:
        started = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
        completed = datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ValueError("successful catalog producer has no valid execution identity") from error
    if completed < started:
        raise ValueError("successful catalog producer has no valid execution identity")
    # runner_group_id changes from 0 to null for retained jobs; it is not identity.
    return job["name"], started, completed, runner_id, runner_name


def select_catalog_artifact(artifacts: list[dict], owner: str, run_id: int, run_attempt: int,
                            *, jobs: list[dict]) -> int:
    """Keep a delayed release bound to the catalog available to its tested attempt."""
    if (not isinstance(owner, str) or not owner.strip()
            or type(run_id) is not int or run_id < 1
            or type(run_attempt) is not int or run_attempt < 1):
        raise ValueError("catalog selection requires an owner and positive run/attempt")
    producers: dict[tuple, int] = {}
    for job in jobs:
        if (job.get("run_id") != run_id or not isinstance(job.get("name"), str)
                or not (job["name"] == "Assemble runtime catalog" or job["name"].endswith(" / Assemble runtime catalog"))
                or job.get("status") != "completed" or job.get("conclusion") != "success"
                or type(job.get("run_attempt")) is not int or not 1 <= job["run_attempt"] <= run_attempt):
            continue
        execution = _execution_identity(job)
        # filter=all contains new job records for retained executions. Only their
        # earliest attempt produced an artifact, even when newer tests reuse it.
        producers[execution] = min(producers.get(execution, job["run_attempt"]), job["run_attempt"])
    if not producers:
        raise ValueError("no successful catalog producer at or before the tested CI attempt")
    producer_attempt = max(producers.values())
    if sum(attempt == producer_attempt for attempt in producers.values()) != 1:
        raise ValueError("tested CI attempt has ambiguous catalog producer executions")
    name = f"{owner}-board-assets-{run_id}-{producer_attempt}"
    selected = [artifact for artifact in artifacts if artifact.get("name") == name]
    if not selected:
        raise ValueError("no catalog was produced at or before the tested CI attempt")
    if len(selected) != 1:
        raise ValueError("tested CI attempt has ambiguous catalog artifacts")
    artifact = selected[0]
    artifact_id = artifact.get("id")
    if artifact.get("expired") is not False or type(artifact_id) is not int or artifact_id < 1:
        raise ValueError("latest tested catalog is expired or has no valid immutable artifact ID")
    return artifact_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-pages", type=Path, required=True,
                        help="Paginated GitHub run-artifact response")
    parser.add_argument("--job-pages", type=Path, required=True,
                        help="Paginated GitHub job history with filter=all")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    arguments = parser.parse_args()
    artifacts = [artifact for page in json.loads(arguments.artifact_pages.read_text())
                 for artifact in page["artifacts"]]
    jobs = [job for page in json.loads(arguments.job_pages.read_text()) for job in page["jobs"]]
    print(select_catalog_artifact(artifacts, arguments.owner, arguments.run_id, arguments.run_attempt, jobs=jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
