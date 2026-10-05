"""Bind a complete generated catalog to its checked-out source revision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import prepare_assets as compiler

SCHEMA_VERSION = 1
AUXILIARY_FILES = ("HangTen/Resources/GripHand/hand-mesh.json", "HangTen/Resources/PlanLibrary.json")


def _inventory() -> tuple[dict[str, str], dict[str, str]]:
    repository = compiler.REPOSITORY
    sources, files = {}, {}
    for package in compiler.source_backed_packages():
        source = repository / "Hangboards" / f"{package}.FCStd"
        sources[source.relative_to(repository).as_posix()] = compiler.sha256(source)
        assets = repository / "Hangboards" / package / "assets"
        _, names = compiler.validate_assets(package, assets)
        if {path.name for path in assets.iterdir()} != names:
            raise ValueError(f"{package}: runtime inventory contains unexpected files")
        for name in sorted(names):
            path = assets / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"{package}: runtime artifact must be a regular file")
            files[path.relative_to(repository).as_posix()] = compiler.sha256(path)
    actual = {path.relative_to(repository).as_posix()
              for path in (repository / "Hangboards").glob("*/assets/*") if path.is_file()}
    if actual != set(files):
        raise ValueError("runtime inventory includes a missing or obsolete board")
    for relative in AUXILIARY_FILES:
        path = repository / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing regular runtime resource: {relative}")
        files[relative] = compiler.sha256(path)
    return sources, files


def create_catalog(manifest: Path, reports: Path, shard_count: int, revision: str) -> None:
    """Reject missing, overlapping, failed, or differently sourced shards."""
    fingerprint = compiler.compiler_fingerprint()
    packages = compiler.source_backed_packages()
    paths = sorted(reports.glob("shard-*.json"))
    if {path.name for path in paths} != {f"shard-{index}.json" for index in range(shard_count)}:
        raise ValueError("catalog requires exactly one report from every shard")
    seen: set[str] = set()
    for path in paths:
        report = json.loads(path.read_text())
        index = report.get("shardIndex")
        if (report.get("schemaVersion") != SCHEMA_VERSION or report.get("revision") != revision
                or report.get("compilerSHA256") != fingerprint or report.get("shardCount") != shard_count
                or type(index) is not int or not 0 <= index < shard_count or path.stem != f"shard-{index}"
                or report.get("failures")):
            raise ValueError(f"{path.name}: failed shard or mismatched compiler/source revision")
        entries = report["prepared"]
        names = [entry["package"] for entry in entries]
        if len(set(names)) != len(names) or set(names) & seen or set(names) != set(compiler.shard_packages(packages, index, shard_count)):
            raise ValueError(f"{path.name}: missing, duplicate, or incorrectly assigned board")
        for entry in entries:
            current, _ = compiler.validate_assets(entry["package"], compiler.REPOSITORY / "Hangboards" / entry["package"] / "assets")
            for key in ("sourceSHA256", "assetSHA256", "presentations"):
                if entry.get(key) != current[key]:
                    raise ValueError(f"{entry['package']}: shard artifacts do not match the current source")
        seen.update(names)
    if seen != set(packages):
        raise ValueError("catalog does not cover all current CAD sources")
    sources, files = _inventory()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "schemaVersion": SCHEMA_VERSION, "revision": revision, "compilerSHA256": fingerprint,
        "sources": sources, "files": files,
    }, indent=2, sort_keys=True) + "\n")


def validate_catalog(manifest: Path, revision: str) -> None:
    recorded = json.loads(manifest.read_text())
    if (recorded.get("schemaVersion") != SCHEMA_VERSION or recorded.get("revision") != revision
            or recorded.get("compilerSHA256") != compiler.compiler_fingerprint()):
        raise ValueError("compiled catalog does not belong to the tested source revision/compiler")
    sources, files = _inventory()
    if recorded.get("sources") != sources or recorded.get("files") != files:
        raise ValueError("compiled catalog source or output hashes do not match the tested artifacts")


def select_catalog_artifact(artifacts: list[dict], owner: str, run_id: int, run_attempt: int,
                            *, jobs: list[dict]) -> int:
    """Keep a delayed release bound to the catalog available to its tested attempt.

    Test-only retries reuse a retained producer. A later compilation cannot
    replace that producer's immutable artifact before its own tests pass.
    """
    if not owner or type(run_id) is not int or run_id < 1 or type(run_attempt) is not int or run_attempt < 1:
        raise ValueError("catalog selection requires an owner and positive run/attempt")
    producers = [job["run_attempt"] for job in jobs
                 if job.get("run_id") == run_id and isinstance(job.get("name"), str)
                 and (job["name"] == "Assemble runtime catalog" or job["name"].endswith(" / Assemble runtime catalog"))
                 and job.get("status") == "completed" and job.get("conclusion") == "success"
                 and type(job.get("run_attempt")) is int and 1 <= job["run_attempt"] <= run_attempt]
    if not producers:
        raise ValueError("no successful catalog producer at or before the tested CI attempt")
    name = f"{owner}-board-assets-{run_id}-{max(producers)}"
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
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--reports", type=Path)
    parser.add_argument("--shard-count", type=int, default=8)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--artifact-pages", type=Path, help="Paginated GitHub run-artifact response for release selection")
    parser.add_argument("--job-pages", type=Path, help="Paginated GitHub job history proving the successful catalog producer")
    parser.add_argument("--owner")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--run-attempt", type=int)
    arguments = parser.parse_args()
    if arguments.artifact_pages is not None:
        if arguments.manifest or arguments.reports or arguments.check:
            parser.error("artifact selection cannot also create or validate a catalog")
        if arguments.job_pages is None:
            parser.error("artifact selection requires --job-pages producer history")
        pages = json.loads(arguments.artifact_pages.read_text())
        artifacts = [artifact for page in pages for artifact in page["artifacts"]]
        jobs = [job for page in json.loads(arguments.job_pages.read_text()) for job in page["jobs"]]
        print(select_catalog_artifact(artifacts, arguments.owner, arguments.run_id, arguments.run_attempt, jobs=jobs))
        return 0
    if arguments.manifest is None:
        parser.error("catalog creation or validation requires --manifest")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=compiler.REPOSITORY, text=True).strip()
    if arguments.check:
        validate_catalog(arguments.manifest, revision)
    else:
        if arguments.reports is None or arguments.shard_count < 1:
            parser.error("catalog creation requires --reports and a positive --shard-count")
        create_catalog(arguments.manifest, arguments.reports, arguments.shard_count, revision)
    print(f"Verified complete runtime catalog for {revision}: {len(compiler.source_backed_packages())} boards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
