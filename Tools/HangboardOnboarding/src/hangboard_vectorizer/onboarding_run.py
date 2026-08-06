"""Persistent, approval-aware orchestration for generic product onboarding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType
from typing import Protocol

from PIL import Image, ImageOps

from .generic_stage0 import (
    CommercialIdentityAssertion,
    StageCheckpoint,
    commercial_identity,
    run_generic_stage0,
)
from .generic_stage1 import GenericStage1Runner
from .generic_stage2 import GenericStage2Runner
from .generic_stage3 import GenericStage3Runner
from .generic_stage4 import GenericStage4Runner
from .source_cache import CachedSource, cache_source
from .workspace_paths import default_workspace_root, resolve_workspace_path


_SCHEMA_VERSION = 1
_PROFILE_ID = "generic-commercial-source-v1"
_FINAL_STAGE = 4


@dataclass(frozen=True, slots=True)
class RunContext:
    root: Path
    manifest: Mapping[str, object]


class StageRunner(Protocol):
    stage: int

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint: ...


class OnboardingStateError(ValueError):
    """Raised when a requested transition or persisted run state is invalid."""


class GenericStage0Runner:
    stage = 0

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        return run_generic_stage0(
            _cached_source_from_manifest(context.root, context.manifest),
            _identity_from_manifest(context.manifest),
            artifact_root,
        )


DEFAULT_STAGE_RUNNERS: Mapping[int, StageRunner] = MappingProxyType(
    {
        0: GenericStage0Runner(),
        1: GenericStage1Runner(),
        2: GenericStage2Runner(),
        3: GenericStage3Runner(),
        4: GenericStage4Runner(),
    }
)


def start_run(
    product_name: str,
    source: str,
    output: Path,
    *,
    runners: Mapping[int, StageRunner] | None = None,
    workspace_root: Path | None = None,
) -> Mapping[str, object]:
    """Create and publish a new run through its first review checkpoint."""
    owned_root = default_workspace_root() if workspace_root is None else Path(workspace_root)
    output = resolve_workspace_path(Path(output), owned_root)
    lock = _start_lock_path(output)
    with _exclusive_lock(lock):
        if _lexists(output):
            raise FileExistsError(f"onboarding run already exists: {output}")
        if not output.parent.is_dir():
            raise FileNotFoundError(f"output parent does not exist: {output.parent}")
        temporary_root = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
        try:
            cached = cache_source(source, temporary_root / "inputs")
            identity = commercial_identity(product_name)
            manifest = _initial_manifest(identity, cached)
            _write_manifest(temporary_root, manifest)
            registry = _runner_registry(runners)
            runner = registry.get(0)
            if runner is None:
                raise OnboardingStateError("Stage 0 runner is not installed")
            artifact_root = temporary_root / "stages" / "00" / "attempt-0001"
            artifact_root.parent.mkdir(parents=True, exist_ok=True)
            checkpoint = runner.run(
                RunContext(temporary_root, MappingProxyType(manifest)),
                artifact_root,
            )
            if checkpoint.stage != 0 or not checkpoint.machine_passed:
                raise OnboardingStateError("Stage 0 did not publish a machine-passed checkpoint")
            _record_checkpoint(manifest, temporary_root, checkpoint, attempt=1)
            _write_manifest(temporary_root, manifest)
            temporary_root.replace(output)
        except Exception:
            shutil.rmtree(temporary_root, ignore_errors=True)
            raise
    return _checkpoint_result(output, stage=0, status="awaiting_approval")


def approve_stage(output: Path, stage: int) -> Mapping[str, object]:
    """Approve the exact hash-bound review currently awaiting approval."""
    output = Path(output)
    with _exclusive_lock(_run_lock_path(output)):
        manifest = _load_and_validate(output)
        pipeline = _mapping(manifest["pipeline"], "pipeline")
        if stage not in (0, 1, 2, 3, 4) or pipeline["status"] != "awaiting_approval" or pipeline["currentStage"] != stage:
            raise OnboardingStateError(f"Stage {stage} is not awaiting approval")
        record = _stage_record(manifest, stage)
        if record["status"] != "review_pending":
            raise OnboardingStateError(f"Stage {stage} is not awaiting approval")
        _validate_checkpoint(output, record)

        approval_relative = f"approvals/stage-{stage}.json"
        acceptance_relative = _relative_from_record(record, "acceptancePath", f"stage-{stage}-acceptance.json")
        approval_path = output / approval_relative
        acceptance_path = output / acceptance_relative
        if _lexists(approval_path) or _lexists(acceptance_path):
            raise OnboardingStateError(f"Stage {stage} approval evidence already exists")
        approval = {
            "candidateHashesSha256": record["candidateHashesSha256"],
            "decision": "approved",
            "reviewSha256": record["reviewSha256"],
            "runIdentitySha256": manifest["runIdentitySha256"],
            "schemaVersion": _SCHEMA_VERSION,
            "stage": stage,
        }
        transaction = Path(tempfile.mkdtemp(prefix=f".stage-{stage}-approval.tmp-", dir=output))
        published: list[Path] = []
        try:
            staged_approval = transaction / f"stage-{stage}.json"
            _write_json_file(staged_approval, approval)
            approval_hash = _hash_file(staged_approval)
            acceptance = _acceptance_document(
                output,
                manifest,
                record,
                approval_path=approval_relative,
                approval_sha256=approval_hash,
            )
            staged_acceptance = transaction / f"stage-{stage}-acceptance.json"
            _write_json_file(staged_acceptance, acceptance)
            acceptance_hash = _hash_file(staged_acceptance)

            approval_path.parent.mkdir(parents=True, exist_ok=True)
            staged_approval.replace(approval_path)
            published.append(approval_path)
            staged_acceptance.replace(acceptance_path)
            published.append(acceptance_path)
            record.update(
                {
                    "acceptancePath": acceptance_relative,
                    "acceptanceSha256": acceptance_hash,
                    "approvalPath": approval_relative,
                    "approvalSha256": approval_hash,
                    "status": "approved",
                }
            )
            manifest["pipeline"] = (
                {"currentStage": stage, "status": "complete"}
                if stage == _FINAL_STAGE
                else {
                    "currentStage": stage,
                    "nextAction": "resume",
                    "nextStage": stage + 1,
                    "status": "ready_for_next_stage",
                }
            )
            _write_manifest(output, manifest)
        except Exception:
            for published_path in published:
                published_path.unlink(missing_ok=True)
            _remove_empty_parent(approval_path.parent, output)
            raise
        finally:
            shutil.rmtree(transaction, ignore_errors=True)
    return _status_result(output, manifest)


def resume_run(
    output: Path,
    *,
    runners: Mapping[int, StageRunner] | None = None,
) -> Mapping[str, object]:
    """Run exactly the next registered stage after all preceding approvals."""
    output = Path(output)
    with _exclusive_lock(_run_lock_path(output)):
        manifest = _load_and_validate(output)
        pipeline = _mapping(manifest["pipeline"], "pipeline")
        if pipeline["status"] != "ready_for_next_stage":
            raise OnboardingStateError("run is not ready to resume")
        next_stage = _integer(pipeline["nextStage"], "pipeline.nextStage")
        _require_prior_approvals(manifest, next_stage)
        registry = _runner_registry(runners)
        runner = registry.get(next_stage)
        if runner is None:
            raise OnboardingStateError(f"Stage {next_stage} runner is not installed")
        if runner.stage != next_stage:
            raise OnboardingStateError(f"Stage {next_stage} runner has an inconsistent stage")

        attempt = _next_attempt(manifest, next_stage)
        artifact_relative = f"stages/{next_stage:02d}/attempt-{attempt:04d}"
        artifact_root = output / artifact_relative
        if _lexists(artifact_root):
            raise OnboardingStateError(f"Stage {next_stage} artifact root already exists")
        staging_root = Path(tempfile.mkdtemp(prefix=f".stage-{next_stage:02d}.tmp-", dir=output))
        staged_artifact = staging_root / "artifacts"
        published = False
        artifact_parent_created = not artifact_root.parent.exists()
        try:
            checkpoint = runner.run(
                RunContext(output, MappingProxyType(manifest)), staged_artifact
            )
            if checkpoint.stage != next_stage or not checkpoint.machine_passed:
                raise OnboardingStateError(f"Stage {next_stage} did not publish a machine-passed checkpoint")
            if checkpoint.artifact_root != staged_artifact:
                raise OnboardingStateError(f"Stage {next_stage} runner published an unexpected artifact root")
            staged_record = _checkpoint_record(
                output, checkpoint, attempt=attempt, artifact_relative=_relative_to_root(output, staged_artifact)
            )
            _validate_checkpoint(output, staged_record, require_artifact_layout=False)
            record = _checkpoint_record(output, checkpoint, attempt=attempt, artifact_relative=artifact_relative)
            artifact_root.parent.mkdir(parents=True, exist_ok=True)
            staged_artifact.replace(artifact_root)
            published = True
            _validate_checkpoint(output, record)
            _list(manifest["stages"], "stages").append(record)
            manifest["pipeline"] = {
                "currentStage": next_stage,
                "nextAction": f"approve-stage-{next_stage}",
                "nextStage": next_stage + 1,
                "status": "awaiting_approval",
            }
            _write_manifest(output, manifest)
        except Exception:
            if published:
                shutil.rmtree(artifact_root, ignore_errors=True)
            if artifact_parent_created:
                _remove_empty_parent(artifact_root.parent, output)
            raise
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
    return _checkpoint_result(output, stage=next_stage, status="awaiting_approval")


def replace_pending_checkpoint(
    output: Path,
    checkpoint: StageCheckpoint,
) -> Mapping[str, object]:
    """Atomically select a new immutable attempt for the pending stage."""
    output = Path(output)
    with _exclusive_lock(_run_lock_path(output)):
        manifest = _load_and_validate(output)
        pipeline = _mapping(manifest["pipeline"], "pipeline")
        current_stage = _integer(pipeline["currentStage"], "pipeline.currentStage")
        if pipeline["status"] != "awaiting_approval":
            raise OnboardingStateError(f"Stage {current_stage} is not awaiting approval")
        if checkpoint.stage != current_stage:
            raise OnboardingStateError(
                f"checkpoint stage {checkpoint.stage} does not match pending stage {current_stage}"
            )
        if not checkpoint.machine_passed:
            raise OnboardingStateError(f"Stage {current_stage} was not machine-passed")

        old_record = _stage_record(manifest, current_stage)
        if old_record["status"] != "review_pending":
            raise OnboardingStateError(f"Stage {current_stage} is not awaiting approval")
        attempt = _next_attempt(manifest, current_stage)
        artifact_relative = f"stages/{current_stage:02d}/attempt-{attempt:04d}"
        artifact_root = output / artifact_relative
        if _lexists(artifact_root):
            raise OnboardingStateError(
                f"Stage {current_stage} artifact root already exists"
            )

        staging_root = Path(
            tempfile.mkdtemp(prefix=f".stage-{current_stage:02d}-revision.tmp-", dir=output)
        )
        staged_artifact = staging_root / "artifacts"
        published = False
        artifact_parent_created = not artifact_root.parent.exists()
        try:
            source_relative = _relative_to_root(
                checkpoint.artifact_root.parent, checkpoint.artifact_root
            )
            source_record = _checkpoint_record(
                checkpoint.artifact_root.parent,
                checkpoint,
                attempt=attempt,
                artifact_relative=source_relative,
            )
            _validate_checkpoint(
                checkpoint.artifact_root.parent,
                source_record,
                require_artifact_layout=False,
            )
            try:
                review_name = checkpoint.review_path.relative_to(
                    checkpoint.artifact_root
                )
            except ValueError as error:
                raise OnboardingStateError(
                    "stage review path must be inside the artifact root"
                ) from error
            shutil.copytree(checkpoint.artifact_root, staged_artifact)
            staged_checkpoint = StageCheckpoint(
                stage=checkpoint.stage,
                artifact_root=staged_artifact,
                candidate_hashes=checkpoint.candidate_hashes,
                review_path=staged_artifact / review_name,
                machine_passed=checkpoint.machine_passed,
            )
            staged_record = _checkpoint_record(
                output,
                staged_checkpoint,
                attempt=attempt,
                artifact_relative=_relative_to_root(output, staged_artifact),
            )
            _validate_checkpoint(output, staged_record, require_artifact_layout=False)

            artifact_root.parent.mkdir(parents=True, exist_ok=True)
            staged_artifact.replace(artifact_root)
            published = True
            published_checkpoint = StageCheckpoint(
                stage=checkpoint.stage,
                artifact_root=artifact_root,
                candidate_hashes=checkpoint.candidate_hashes,
                review_path=artifact_root / review_name,
                machine_passed=checkpoint.machine_passed,
            )
            replacement_record = _checkpoint_record(
                output,
                published_checkpoint,
                attempt=attempt,
                artifact_relative=artifact_relative,
            )
            _validate_checkpoint(output, replacement_record)
            stages = _list(manifest["stages"], "stages")
            stages[current_stage] = replacement_record
            _write_manifest(output, manifest)
        except Exception:
            if published:
                shutil.rmtree(artifact_root, ignore_errors=True)
            if artifact_parent_created:
                _remove_empty_parent(artifact_root.parent, output)
            raise
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
    return _checkpoint_result(output, stage=current_stage, status="awaiting_approval")


def read_status(output: Path) -> Mapping[str, object]:
    """Validate an existing run without modifying it and return its state."""
    output = Path(output)
    manifest = _load_and_validate(output)
    return _status_result(output, manifest)


def cached_source_path(output: Path) -> Path:
    """Return the validated, run-confined source image for revision replay."""
    output = Path(output)
    manifest = _load_and_validate(output)
    source = _mapping(manifest["source"], "source")
    return _absolute_relative(output, source["cachedPath"])


def _initial_manifest(identity: CommercialIdentityAssertion, source: CachedSource) -> dict[str, object]:
    product = {
        "assertedName": identity.asserted_name,
        "assertionSource": identity.assertion_source,
        "key": identity.product_key,
        "normalizedName": identity.normalized_name,
    }
    source_record = {
        "cachedPath": f"inputs/{source.cached_path.name}",
        "decodedRgbSha256": source.decoded_rgb_sha256,
        "evidencePath": "inputs/source.json",
        "rawSha256": source.raw_sha256,
    }
    identity_hash = _canonical_hash(
        {
            "assertedName": identity.asserted_name,
            "decodedRgbSha256": source.decoded_rgb_sha256,
            "productKey": identity.product_key,
            "profileId": _PROFILE_ID,
            "rawSha256": source.raw_sha256,
            "schemaVersion": _SCHEMA_VERSION,
        }
    )
    return {
        "pipeline": {
            "currentStage": 0,
            "nextAction": "approve-stage-0",
            "nextStage": 1,
            "status": "awaiting_approval",
        },
        "product": product,
        "runIdentitySha256": identity_hash,
        "schemaVersion": _SCHEMA_VERSION,
        "source": source_record,
        "stages": [],
    }


def _record_checkpoint(
    manifest: dict[str, object], root: Path, checkpoint: StageCheckpoint, *, attempt: int
) -> None:
    _list(manifest["stages"], "stages").append(
        _checkpoint_record(root, checkpoint, attempt=attempt)
    )


def _checkpoint_record(
    root: Path,
    checkpoint: StageCheckpoint,
    *,
    attempt: int,
    artifact_relative: str | None = None,
) -> dict[str, object]:
    actual_artifact_relative = _relative_to_root(root, checkpoint.artifact_root)
    artifact_relative = artifact_relative or actual_artifact_relative
    _validate_relative(artifact_relative)
    try:
        review_name = checkpoint.review_path.relative_to(checkpoint.artifact_root).as_posix()
    except ValueError as error:
        raise OnboardingStateError("stage review path must be inside the artifact root") from error
    if not review_name or Path(review_name).name != review_name:
        raise OnboardingStateError("stage review path must name one artifact file")
    review_relative = f"{artifact_relative}/{review_name}"
    candidate_relative = f"{artifact_relative}/stage-{checkpoint.stage}-candidate.json"
    hashes_relative = f"{artifact_relative}/candidate-hashes.json"
    _validate_relative(candidate_relative)
    return {
        "artifactRoot": artifact_relative,
        "attempt": attempt,
        "candidateHashesPath": hashes_relative,
        "candidateHashesSha256": _hash_file(root / f"{actual_artifact_relative}/candidate-hashes.json"),
        "candidatePath": candidate_relative,
        "machinePassed": checkpoint.machine_passed,
        "reviewPath": review_relative,
        "reviewSha256": _hash_file(checkpoint.review_path),
        "stage": checkpoint.stage,
        "status": "review_pending",
    }


def _load_and_validate(output: Path) -> dict[str, object]:
    if not output.is_dir():
        raise FileNotFoundError(f"onboarding run does not exist: {output}")
    manifest_path = output / "run.json"
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise OnboardingStateError("run manifest must be an object")
    _validate_manifest(output, manifest)
    return manifest


def _validate_manifest(root: Path, manifest: dict[str, object]) -> None:
    if manifest.get("schemaVersion") != _SCHEMA_VERSION:
        raise OnboardingStateError("unsupported run manifest schema")
    product = _mapping(manifest.get("product"), "product")
    identity = commercial_identity(_string(product.get("assertedName"), "product.assertedName"))
    if product != {
        "assertedName": identity.asserted_name,
        "assertionSource": "caller",
        "key": identity.product_key,
        "normalizedName": identity.normalized_name,
    }:
        raise OnboardingStateError("run product identity is inconsistent")
    source = _mapping(manifest.get("source"), "source")
    for name in ("cachedPath", "evidencePath"):
        _validate_relative(_string(source.get(name), f"source.{name}"))
    evidence = _read_json(_absolute_relative(root, source["evidencePath"]))
    if not isinstance(evidence, dict):
        raise OnboardingStateError("source evidence must be an object")
    _validate_source_evidence(root, source, evidence)
    expected_identity = _canonical_hash(
        {
            "assertedName": identity.asserted_name,
            "decodedRgbSha256": source["decodedRgbSha256"],
            "productKey": identity.product_key,
            "profileId": _PROFILE_ID,
            "rawSha256": source["rawSha256"],
            "schemaVersion": _SCHEMA_VERSION,
        }
    )
    if manifest.get("runIdentitySha256") != expected_identity:
        raise OnboardingStateError("run identity hash does not match its evidence")

    pipeline = _mapping(manifest.get("pipeline"), "pipeline")
    status = _string(pipeline.get("status"), "pipeline.status")
    if status not in {"awaiting_approval", "ready_for_next_stage", "running", "failed", "complete"}:
        raise OnboardingStateError("run pipeline status is invalid")
    current_stage = _integer(pipeline.get("currentStage"), "pipeline.currentStage")
    if status == "complete":
        if "nextStage" in pipeline or "nextAction" in pipeline:
            raise OnboardingStateError("complete run must not have a next stage or action")
        next_stage = current_stage + 1
    else:
        next_stage = _integer(pipeline.get("nextStage"), "pipeline.nextStage")
        _string(pipeline.get("nextAction"), "pipeline.nextAction")
    stages = _list(manifest.get("stages"), "stages")
    if current_stage < 0 or next_stage < 0:
        raise OnboardingStateError("run pipeline stages must be nonnegative")
    if not stages:
        raise OnboardingStateError("published run must contain a stage checkpoint")
    if current_stage != len(stages) - 1 or next_stage != current_stage + 1:
        raise OnboardingStateError("run pipeline does not match published stage records")
    for expected_stage, record_object in enumerate(stages):
        record = _mapping(record_object, "stage record")
        stage = _integer(record.get("stage"), "stage.stage")
        if stage != expected_stage:
            raise OnboardingStateError("published stages must be contiguous and ordered")
        _validate_checkpoint(root, record)
        if record["status"] == "approved":
            _validate_approval(root, manifest, record)
    if status == "awaiting_approval":
        record = _stage_record(manifest, current_stage)
        if record.get("status") != "review_pending" or next_stage != current_stage + 1:
            raise OnboardingStateError("run approval checkpoint is inconsistent")
        _require_prior_approvals(manifest, current_stage)
    if status == "ready_for_next_stage":
        if next_stage != current_stage + 1:
            raise OnboardingStateError("run next stage is inconsistent")
        _require_prior_approvals(manifest, next_stage)
    if status == "complete":
        if current_stage != _FINAL_STAGE:
            raise OnboardingStateError("run completed before its final stage")
        _require_prior_approvals(manifest, _FINAL_STAGE + 1)


def _validate_source_evidence(root: Path, source: Mapping[str, object], evidence: Mapping[str, object]) -> None:
    for name in ("rawSha256", "decodedRgbSha256"):
        if source.get(name) != evidence.get(name):
            raise OnboardingStateError(f"source {name} does not match source evidence")
    cached_path = _absolute_relative(root, _string(source["cachedPath"], "source.cachedPath"))
    if not cached_path.is_file():
        raise OnboardingStateError("cached source is missing")
    raw = cached_path.read_bytes()
    if _hash_bytes(raw) != source["rawSha256"]:
        raise OnboardingStateError("cached source raw hash does not match its evidence")
    try:
        from io import BytesIO

        with Image.open(BytesIO(raw)) as image:
            if getattr(image, "is_animated", False) or getattr(image, "n_frames", 1) != 1:
                raise OnboardingStateError("cached source must not be animated")
            rgb = ImageOps.exif_transpose(image).convert("RGB")
            decoded = rgb.tobytes()
            width, height = rgb.size
    except OnboardingStateError:
        raise
    except Exception as error:
        raise OnboardingStateError("cached source is no longer decodable") from error
    if _hash_bytes(decoded) != source["decodedRgbSha256"]:
        raise OnboardingStateError("cached source pixels do not match its evidence")
    if evidence.get("width") != width or evidence.get("height") != height:
        raise OnboardingStateError("cached source dimensions do not match its evidence")


def _validate_checkpoint(
    root: Path, record: Mapping[str, object], *, require_artifact_layout: bool = True
) -> None:
    stage = _integer(record.get("stage"), "stage.stage")
    if _integer(record.get("attempt"), "stage.attempt") < 1:
        raise OnboardingStateError("stage attempt is invalid")
    if record.get("status") not in {"review_pending", "approved"}:
        raise OnboardingStateError("stage status is invalid")
    if record.get("machinePassed") is not True:
        raise OnboardingStateError("stage was not machine-passed")
    artifact = _string(record.get("artifactRoot"), "stage.artifactRoot")
    expected_prefix = f"stages/{stage:02d}/attempt-{record['attempt']:04d}"
    if require_artifact_layout and artifact != expected_prefix:
        raise OnboardingStateError("stage artifact root is inconsistent")
    for name in ("candidatePath", "candidateHashesPath", "reviewPath"):
        _validate_relative(_string(record.get(name), f"stage.{name}"))
    candidate_hashes_path = _absolute_relative(root, record["candidateHashesPath"])
    hashes = _read_json(candidate_hashes_path)
    if not isinstance(hashes, dict) or not hashes:
        raise OnboardingStateError("candidate hash manifest is invalid")
    if _hash_file(candidate_hashes_path) != record.get("candidateHashesSha256"):
        raise OnboardingStateError("candidate hash manifest does not match its recorded hash")
    for name, expected in hashes.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise OnboardingStateError("candidate hashes are invalid")
        candidate_path = _absolute_relative(root, f"{artifact}/{name}")
        if _hash_file(candidate_path) != expected:
            raise OnboardingStateError("candidate file does not match its recorded hash")
    review_path = _absolute_relative(root, record["reviewPath"])
    if _hash_file(review_path) != record.get("reviewSha256"):
        raise OnboardingStateError("review image does not match its recorded hash")
    if hashes.get(Path(_string(record["reviewPath"], "stage.reviewPath")).name) != record["reviewSha256"]:
        raise OnboardingStateError("review hash is not bound by the candidate hash manifest")
    candidate_path = _absolute_relative(root, record["candidatePath"])
    if not candidate_path.is_file():
        raise OnboardingStateError("stage candidate is missing")


def _validate_approval(root: Path, manifest: Mapping[str, object], record: Mapping[str, object]) -> None:
    for name in ("approvalPath", "acceptancePath"):
        _validate_relative(_string(record.get(name), f"stage.{name}"))
    approval_path = _absolute_relative(root, record["approvalPath"])
    acceptance_path = _absolute_relative(root, record["acceptancePath"])
    if _hash_file(approval_path) != record.get("approvalSha256"):
        raise OnboardingStateError("approval does not match its recorded hash")
    if _hash_file(acceptance_path) != record.get("acceptanceSha256"):
        raise OnboardingStateError("acceptance does not match its recorded hash")
    approval = _read_json(approval_path)
    expected_approval = {
        "candidateHashesSha256": record["candidateHashesSha256"],
        "decision": "approved",
        "reviewSha256": record["reviewSha256"],
        "runIdentitySha256": manifest["runIdentitySha256"],
        "schemaVersion": _SCHEMA_VERSION,
        "stage": record["stage"],
    }
    if approval != expected_approval:
        raise OnboardingStateError("approval does not bind the published checkpoint")
    expected_acceptance = _acceptance_document(
        root,
        manifest,
        record,
        approval_path=_string(record["approvalPath"], "stage.approvalPath"),
        approval_sha256=_string(record["approvalSha256"], "stage.approvalSha256"),
    )
    if _read_json(acceptance_path) != expected_acceptance:
        raise OnboardingStateError("acceptance does not bind the approved checkpoint")


def _acceptance_document(
    root: Path,
    manifest: Mapping[str, object],
    record: Mapping[str, object],
    *,
    approval_path: str,
    approval_sha256: str,
) -> dict[str, object]:
    candidate = _candidate_from_record(root, record)
    candidate_hashes = _read_json(_absolute_relative(root, record["candidateHashesPath"]))
    stage = _integer(record["stage"], "stage.stage")
    acceptance: dict[str, object] = {
        "approvalPath": approval_path,
        "approvalSha256": approval_sha256,
        "candidateHashes": candidate_hashes,
        "profile": candidate["profile"],
        "runIdentitySha256": manifest["runIdentitySha256"],
        "schemaVersion": _SCHEMA_VERSION,
        "stage": stage,
    }
    if stage == 0:
        source = _mapping(manifest["source"], "source")
        acceptance.update(
            {
                "identity": manifest["product"],
                "registered": candidate["registered"],
                "source": source,
                "sourceEvidence": _read_json(_absolute_relative(root, source["evidencePath"])),
            }
        )
        return acceptance
    if stage == 2:
        upstream = _stage_record(manifest, 1)
        input_acceptance = {
            "path": upstream["acceptancePath"],
            "sha256": upstream["acceptanceSha256"],
        }
        if candidate.get("inputAcceptance") != input_acceptance:
            raise OnboardingStateError("Stage 2 candidate does not bind the Stage 1 acceptance")
        regions = dict(_mapping(candidate["regions"], "stage candidate regions"))
        regions["path"] = f"{record['artifactRoot']}/stage-2-regions.json"
        if regions.get("fileSha256") != candidate_hashes.get("stage-2-regions.json"):
            raise OnboardingStateError("Stage 2 regions are not bound by its candidate hashes")
        registered = dict(_mapping(candidate["registered"], "stage candidate registered"))
        registered["path"] = f"{record['artifactRoot']}/stage-2-labels.png"
        if registered.get("fileSha256") != candidate_hashes.get("stage-2-labels.png"):
            raise OnboardingStateError("Stage 2 labels are not bound by its candidate hashes")
        acceptance.update(
            {
                "candidateHashesSha256": record["candidateHashesSha256"],
                "inputAcceptance": input_acceptance,
                "regionCount": candidate["regionCount"],
                "regions": regions,
                "registered": registered,
                "review": {"path": record["reviewPath"], "sha256": record["reviewSha256"]},
            }
        )
        return acceptance
    if stage == 3:
        upstream = _stage_record(manifest, 2)
        input_acceptance = {
            "path": upstream["acceptancePath"],
            "sha256": upstream["acceptanceSha256"],
        }
        if candidate.get("inputAcceptance") != input_acceptance:
            raise OnboardingStateError("Stage 3 candidate does not bind the Stage 2 acceptance")
        vector_regions = dict(_mapping(candidate["vectorRegions"], "stage candidate vector regions"))
        vector_regions["path"] = f"{record['artifactRoot']}/stage-3-vector-regions.json"
        if vector_regions.get("fileSha256") != candidate_hashes.get("stage-3-vector-regions.json"):
            raise OnboardingStateError("Stage 3 vector regions are not bound by its candidate hashes")
        vector_svg = dict(_mapping(candidate["vectorSvg"], "stage candidate vector SVG"))
        vector_svg["path"] = f"{record['artifactRoot']}/stage-3-vector.svg"
        if vector_svg.get("fileSha256") != candidate_hashes.get("stage-3-vector.svg"):
            raise OnboardingStateError("Stage 3 vector SVG is not bound by its candidate hashes")
        acceptance.update(
            {
                "candidateHashesSha256": record["candidateHashesSha256"],
                "inputAcceptance": input_acceptance,
                "regionCount": candidate["regionCount"],
                "review": {"path": record["reviewPath"], "sha256": record["reviewSha256"]},
                "vectorRegions": vector_regions,
                "vectorSvg": vector_svg,
            }
        )
        return acceptance
    if stage == 4:
        upstream = _stage_record(manifest, 3)
        input_acceptance = {
            "path": upstream["acceptancePath"],
            "sha256": upstream["acceptanceSha256"],
        }
        if candidate.get("inputAcceptance") != input_acceptance:
            raise OnboardingStateError("Stage 4 candidate does not bind the Stage 3 acceptance")
        outputs: dict[str, object] = {}
        for field, filename in (
            ("normal", "stage-4-normal.png"),
            ("productSvg", "stage-4-product.svg"),
            ("manifest", "stage-4-manifest.json"),
            ("highlights", "stage-4-highlights.json"),
        ):
            record_value = dict(_mapping(candidate[field], f"stage candidate {field}"))
            record_value["path"] = f"{record['artifactRoot']}/{filename}"
            if record_value.get("fileSha256") != candidate_hashes.get(filename):
                raise OnboardingStateError(f"Stage 4 {field} is not bound by its candidate hashes")
            outputs[field] = record_value
        acceptance.update(
            {
                "candidateHashesSha256": record["candidateHashesSha256"],
                "inputAcceptance": input_acceptance,
                "regionCount": candidate["regionCount"],
                "review": {"path": record["reviewPath"], "sha256": record["reviewSha256"]},
                **outputs,
            }
        )
        return acceptance
    if stage != 1:
        raise OnboardingStateError(f"Stage {stage} approval is not supported")

    upstream = _stage_record(manifest, 0)
    input_acceptance = {
        "path": upstream["acceptancePath"],
        "sha256": upstream["acceptanceSha256"],
    }
    if candidate.get("inputAcceptance") != input_acceptance:
        raise OnboardingStateError("Stage 1 candidate does not bind the Stage 0 acceptance")
    registered = dict(_mapping(candidate["registered"], "stage candidate registered"))
    registered["path"] = f"{record['artifactRoot']}/stage-1-auto-rgba.png"
    if registered.get("fileSha256") != candidate_hashes.get("stage-1-auto-rgba.png"):
        raise OnboardingStateError("Stage 1 registered image is not bound by its candidate hashes")
    acceptance.update(
        {
            "candidateHashesSha256": record["candidateHashesSha256"],
            "inputAcceptance": input_acceptance,
            "registered": registered,
            "review": {"path": record["reviewPath"], "sha256": record["reviewSha256"]},
        }
    )
    return acceptance


def _cached_source_from_manifest(root: Path, manifest: Mapping[str, object]) -> CachedSource:
    source = _mapping(manifest["source"], "source")
    evidence_path = _absolute_relative(root, source["evidencePath"])
    evidence = _read_json(evidence_path)
    if not isinstance(evidence, dict):
        raise OnboardingStateError("source evidence must be an object")
    _validate_source_evidence(root, source, evidence)
    cached_path = _absolute_relative(root, source["cachedPath"])
    return CachedSource(
        cached_path=cached_path,
        evidence_path=evidence_path,
        kind=evidence["kind"],
        image_format=evidence["imageFormat"],
        width=evidence["width"],
        height=evidence["height"],
        raw_sha256=source["rawSha256"],
        decoded_rgb_sha256=source["decodedRgbSha256"],
        sanitized_locator=evidence["sanitizedLocator"],
        locator_sha256=evidence["locatorSha256"],
    )


def _identity_from_manifest(manifest: Mapping[str, object]) -> CommercialIdentityAssertion:
    product = _mapping(manifest["product"], "product")
    return commercial_identity(_string(product["assertedName"], "product.assertedName"))


def _candidate_from_record(root: Path, record: Mapping[str, object]) -> Mapping[str, object]:
    candidate = _read_json(_absolute_relative(root, record["candidatePath"]))
    if not isinstance(candidate, Mapping):
        raise OnboardingStateError("stage candidate must be an object")
    if candidate.get("stage") != record["stage"]:
        raise OnboardingStateError("stage candidate has an inconsistent stage")
    if not isinstance(candidate.get("profile"), Mapping):
        raise OnboardingStateError("stage candidate is missing required acceptance evidence")
    if record["stage"] in (0, 1, 2) and not isinstance(candidate.get("registered"), Mapping):
        raise OnboardingStateError("stage candidate is missing required acceptance evidence")
    return candidate


def _runner_registry(runners: Mapping[int, StageRunner] | None) -> Mapping[int, StageRunner]:
    return DEFAULT_STAGE_RUNNERS if runners is None else runners


def _require_prior_approvals(manifest: Mapping[str, object], next_stage: int) -> None:
    records = {record["stage"]: record for record in _list(manifest["stages"], "stages")}
    for stage in range(next_stage):
        if records.get(stage, {}).get("status") != "approved":
            raise OnboardingStateError("all prior stages must be approved before resume")


def _next_attempt(manifest: Mapping[str, object], stage: int) -> int:
    attempts = [record["attempt"] for record in _list(manifest["stages"], "stages") if record.get("stage") == stage]
    return max(attempts, default=0) + 1


def _stage_record(manifest: Mapping[str, object], stage: int) -> dict[str, object]:
    for record in _list(manifest["stages"], "stages"):
        if isinstance(record, dict) and record.get("stage") == stage:
            return record
    raise OnboardingStateError(f"Stage {stage} checkpoint is missing")


def _checkpoint_result(output: Path, *, stage: int, status: str) -> Mapping[str, object]:
    record = _stage_record(_load_and_validate(output), stage)
    return {
        "nextAction": f"approve stage-{stage}",
        "review": record["reviewPath"],
        "run": str(output),
        "stage": stage,
        "status": status,
    }


def _status_result(output: Path, manifest: Mapping[str, object]) -> Mapping[str, object]:
    pipeline = _mapping(manifest["pipeline"], "pipeline")
    result: dict[str, object] = {
        "run": str(output),
        "stage": pipeline["currentStage"],
        "status": pipeline["status"],
    }
    if pipeline["status"] != "complete":
        result["nextAction"] = pipeline["nextAction"]
    if pipeline["status"] == "awaiting_approval":
        result["review"] = _stage_record(manifest, _integer(pipeline["currentStage"], "pipeline.currentStage"))["reviewPath"]
    return result


def _write_manifest(root: Path, manifest: Mapping[str, object]) -> None:
    _write_json_atomic(root / "run.json", manifest)


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_json_file(path: Path, value: object) -> None:
    """Write a transaction-private JSON file and flush its content to disk."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _exclusive_lock(path: Path):
    class _Lock:
        def __enter__(self):
            try:
                self._fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as error:
                raise OnboardingStateError(f"onboarding run is locked: {path}") from error
            self._inode = os.fstat(self._fd).st_ino
            return self

        def __exit__(self, _type, _value, _traceback):
            os.close(self._fd)
            try:
                if path.stat().st_ino == self._inode:
                    path.unlink()
            except FileNotFoundError:
                pass
            return False

    return _Lock()


def _start_lock_path(output: Path) -> Path:
    return output.parent / f".{output.name}.lock"


def _run_lock_path(output: Path) -> Path:
    if not output.is_dir():
        raise FileNotFoundError(f"onboarding run does not exist: {output}")
    return output / ".onboarding.lock"


def _canonical_hash(value: object) -> str:
    return _hash_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _hash_file(path: Path) -> str:
    try:
        return _hash_bytes(path.read_bytes())
    except FileNotFoundError as error:
        raise OnboardingStateError(f"required evidence is missing: {path.name}") from error


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OnboardingStateError(f"invalid JSON evidence: {path.name}") from error


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as error:
        raise OnboardingStateError("stage artifact path must be inside the run root") from error
    _validate_relative(relative)
    return relative


def _relative_from_record(record: Mapping[str, object], _name: str, filename: str) -> str:
    return f"{_string(record['artifactRoot'], 'stage.artifactRoot')}/{filename}"


def _absolute_relative(root: Path, value: object) -> Path:
    relative = _string(value, "relative path")
    _validate_relative(relative)
    return root / relative


def _lexists(path: Path) -> bool:
    """Return true for every directory entry, including a dangling symlink."""
    return os.path.lexists(path)


def _remove_empty_parent(path: Path, boundary: Path) -> None:
    """Remove a newly-created empty directory without traversing past boundary."""
    if path == boundary:
        return
    try:
        path.rmdir()
    except OSError:
        pass


def _validate_relative(value: str) -> None:
    path = Path(value)
    if not value or path.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise OnboardingStateError("run manifest paths must be relative and contained")


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise OnboardingStateError(f"{name} must be an object")
    return value


def _list(value: object, name: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise OnboardingStateError(f"{name} must be a list of objects")
    return value


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise OnboardingStateError(f"{name} must be text")
    return value


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OnboardingStateError(f"{name} must be an integer")
    return value
