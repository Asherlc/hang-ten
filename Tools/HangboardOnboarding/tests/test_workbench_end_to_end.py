from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import numpy as np
import pytest

import hangboard_vectorizer.workbench as workbench_module
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboard_cli import main
from hangboard_vectorizer.onboarding_run import RunContext, start_run
from hangboard_vectorizer.workbench import WorkbenchService
from hangboard_vectorizer.workbench_store import WorkbenchStore


_BOARD_FIXTURES = (
    ("Beastmaker 1000", (77, 52, 34), ("grip-001", "grip-002")),
    (
        "Metolius Wood Grips Compact II",
        (103, 70, 42),
        ("grip-001", "grip-002", "grip-003"),
    ),
    (
        "Metolius Simulator 3D",
        (64, 82, 96),
        ("grip-001", "grip-002", "grip-003", "grip-004"),
    ),
)


def test_ui_created_run_is_resumable_by_cli_and_cli_run_is_listed_by_ui(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    service = _fixture_service(tmp_path)
    created = service.create_from_upload("Example Board", _fixture_image_bytes())

    assert (
        main(
            [
                "--output",
                str(created.run_root),
                "--workspace-root",
                str(tmp_path),
                "--status",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "awaiting_approval"

    cli_run = _create_cli_fixture_run(tmp_path / "cli-run")
    imported = service.import_run(cli_run)
    assert imported.run_root == cli_run
    assert any(board.board_id == imported.board_id for board in service.list_boards())


@pytest.mark.parametrize(("product_name", "color", "region_keys"), _BOARD_FIXTURES)
def test_product_neutral_workflow_preserves_stable_ids_through_local_save(
    tmp_path: Path,
    product_name: str,
    color: tuple[int, int, int],
    region_keys: tuple[str, ...],
) -> None:
    service = _fixture_service(tmp_path, region_keys=region_keys)
    stage3_decoy = _downstream_decoy_keys(3, len(region_keys))
    stage4_decoy = _downstream_decoy_keys(4, len(region_keys))

    current = service.create_from_upload(
        product_name, _fixture_image_bytes(color=color)
    )
    revision_id = current.revision_id
    for stage in (0, 1):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=revision_id,
            expected_stage=stage,
        )

    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    assert set(stage2) == {
        "canvas",
        "labelEncoding",
        "regions",
        "schemaVersion",
        "stage",
    }
    stage2["regions"][0]["metadata"]["mode"] = "aperture"
    service.save_draft(
        current.board_id,
        stage2,
        expected_revision_id=revision_id,
        expected_stage=2,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=revision_id,
        expected_stage=2,
    )
    manifest = json.loads((current.run_root / "run.json").read_text())
    assert manifest["stages"][2]["attempt"] == 2
    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    assert stage2["regions"][0]["metadata"]["mode"] == "aperture"

    stage3 = _stage_document(
        current.run_root, 3, "stage-3-vector-regions.json"
    )
    assert set(stage3) == {
        "canvas",
        "pieceCount",
        "regions",
        "schemaVersion",
        "silhouettePaths",
        "stage",
    }
    stage3["regions"][0]["metadata"]["mode"] = "surface"
    service.save_draft(
        current.board_id,
        stage3,
        expected_revision_id=revision_id,
        expected_stage=3,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=revision_id,
        expected_stage=3,
    )
    manifest = json.loads((current.run_root / "run.json").read_text())
    assert manifest["stages"][3]["attempt"] == 2
    stage3 = _stage_document(
        current.run_root, 3, "stage-3-vector-regions.json"
    )
    assert stage3["regions"][0]["metadata"]["mode"] == "surface"
    assert set(_region_identity(stage3)[1]).isdisjoint(stage3_decoy)

    stage4 = _stage_document(current.run_root, 4, "stage-4-manifest.json")
    assert set(stage4) == {"canvas", "regions", "schemaVersion", "stage"}
    assert set(_region_identity(stage4)[1]).isdisjoint(stage4_decoy)
    _assert_stable_identity_chain(stage2, stage3, stage4)
    assert _region_identity(stage2) == (
        list(range(1, len(region_keys) + 1)),
        list(region_keys),
    )
    assert current.revision_id == revision_id

    complete = service.approve_and_advance(
        current.board_id,
        expected_revision_id=revision_id,
        expected_stage=4,
    )
    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )
    board_manifest = json.loads(
        (
            tmp_path / "boards" / saved.board_id / "board.json"
        ).read_text(encoding="utf-8")
    )
    assert saved.saved is True
    assert board_manifest["savedRevisionId"] == revision_id


@pytest.mark.parametrize("mutation", ("mutate", "drop", "reorder"))
def test_identity_propagation_assertion_rejects_a_changed_upstream_inventory(
    tmp_path: Path, mutation: str
) -> None:
    service = _fixture_service(
        tmp_path,
        region_keys=("grip-001", "grip-002", "grip-003"),
        stage3_identity_mutation=mutation,
    )
    current = service.create_from_upload("Fixture Board", _fixture_image_bytes())
    for stage in (0, 1):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=stage,
        )
    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    service.save_draft(
        current.board_id,
        stage2,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    stage3 = _stage_document(
        current.run_root, 3, "stage-3-vector-regions.json"
    )

    with pytest.raises(AssertionError, match="stable region identity"):
        _assert_stable_identity_chain(stage2, stage3)


def test_production_workbench_surface_contains_no_product_tokens() -> None:
    onboarding_modules = (
        Path(workbench_module.__file__).resolve(),
        Path(workbench_module.__file__).with_name("workbench_store.py").resolve(),
        Path(workbench_module.__file__).with_name("review_edits.py").resolve(),
        Path(workbench_module.__file__).with_name("onboarding_run.py").resolve(),
        Path(workbench_module.__file__).with_name("onboard_cli.py").resolve(),
    )
    editor_root = Path(__file__).resolve().parents[2] / "hold-highlight-editor"
    editor_modules = tuple(
        editor_root / name
        for name in (
            "server.py",
            "job_manager.py",
            "app.js",
            "editor-model.js",
            "vector-path-model.js",
            "workbench-client.js",
            "workbench-controller.js",
            "workbench-model.js",
        )
    )

    violations: dict[str, list[str]] = {}
    for path in (*onboarding_modules, *editor_modules):
        normalized = "".join(
            character
            for character in path.read_text(encoding="utf-8").lower()
            if character.isalnum()
        )
        matches = [
            token
            for token in (
                "beastmaker",
                "metolius",
                "woodgrips",
                "compactii",
                "simulator3d",
            )
            if token in normalized
        ]
        if matches:
            violations[str(path)] = matches

    assert violations == {}


def _fixture_image_bytes(color: tuple[int, int, int] = (45, 65, 85)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (512, 256), color).save(stream, format="PNG")
    return stream.getvalue()


def _fixture_service(
    root: Path,
    *,
    region_keys: tuple[str, ...] = ("grip-001",),
    stage3_identity_mutation: str | None = None,
) -> WorkbenchService:
    return WorkbenchService(
        WorkbenchStore(root),
        runners=_stub_runners(
            region_keys, stage3_identity_mutation=stage3_identity_mutation
        ),
    )


def _create_cli_fixture_run(path: Path) -> Path:
    source = path.parent / "cli-source.png"
    source.write_bytes(_fixture_image_bytes())
    start_run(
        "CLI Fixture Board",
        str(source),
        path,
        runners=_stub_runners(),
        workspace_root=path.parent,
    )
    return path


def _stub_runners(
    region_keys: tuple[str, ...] = ("grip-001",),
    *,
    stage3_identity_mutation: str | None = None,
) -> dict[int, _StubStageRunner]:
    stage3_runner: _StubStageRunner = _StubStageRunner(
        3, _downstream_decoy_keys(3, len(region_keys))
    )
    if stage3_identity_mutation is not None:
        stage3_runner = _BrokenStage3Runner(
            _downstream_decoy_keys(3, len(region_keys)),
            stage3_identity_mutation,
        )
    return {
        0: _StubStageRunner(0, ()),
        1: _StubStageRunner(1, ()),
        2: _StubStageRunner(2, region_keys),
        3: stage3_runner,
        4: _StubStageRunner(4, _downstream_decoy_keys(4, len(region_keys))),
    }


def _downstream_decoy_keys(stage: int, count: int) -> tuple[str, ...]:
    return tuple(f"stage-{stage}-decoy-{index:03d}" for index in range(1, count + 1))


class _StubStageRunner:
    def __init__(
        self,
        stage: int,
        region_keys: tuple[str, ...],
    ) -> None:
        self.stage = stage
        self.region_keys = region_keys

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        Image.new("RGB", (128, 64), (120, 80, 40)).save(review)
        candidate = self._candidate(context, artifact_root)
        candidate_path = artifact_root / f"stage-{self.stage}-candidate.json"
        _write_json(candidate_path, candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        _write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(
            stage=self.stage,
            artifact_root=artifact_root,
            candidate_hashes=hashes,
            review_path=review,
            machine_passed=True,
        )

    def _candidate(
        self, context: RunContext, artifact_root: Path
    ) -> dict[str, object]:
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
            return candidate

        stages = context.manifest["stages"]
        assert isinstance(stages, list)
        upstream = stages[self.stage - 1]
        assert isinstance(upstream, dict)
        candidate["inputAcceptance"] = {
            "path": upstream["acceptancePath"],
            "sha256": upstream["acceptanceSha256"],
        }
        if self.stage == 1:
            registered = artifact_root / "stage-1-auto-rgba.png"
            Image.new("RGBA", (128, 64), (10, 20, 30, 255)).save(registered)
            with Image.open(registered) as image:
                rgba = np.asarray(image, dtype=np.uint8)
            candidate["registered"] = {
                "alphaSha256": sha256(rgba[..., 3].tobytes()).hexdigest(),
                "fileSha256": _hash_file(registered),
                "height": 64,
                "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
                "width": 128,
            }
        elif self.stage == 2:
            regions = artifact_root / "stage-2-regions.json"
            labels = artifact_root / "stage-2-labels.png"
            _write_json(regions, self._stage2_document())
            Image.new("I;16", (128, 64), 0).save(labels)
            candidate.update(
                {
                    "regionCount": len(self.region_keys),
                    "regions": {"fileSha256": _hash_file(regions)},
                    "registered": {"fileSha256": _hash_file(labels)},
                }
            )
        elif self.stage == 3:
            stage2 = _accepted_stage_document(
                context, 2, "regions", "stage-2-regions.json"
            )
            vector_document = self._stage3_document(stage2["regions"])
            regions = artifact_root / "stage-3-vector-regions.json"
            svg = artifact_root / "stage-3-vector.svg"
            _write_json(regions, vector_document)
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            candidate.update(
                {
                    "regionCount": len(vector_document["regions"]),
                    "vectorRegions": {"fileSha256": _hash_file(regions)},
                    "vectorSvg": {"fileSha256": _hash_file(svg)},
                }
            )
        else:
            stage3 = _accepted_stage_document(
                context, 3, "vectorRegions", "stage-3-vector-regions.json"
            )
            stage4_document = self._stage4_document(stage3["regions"])
            normal = artifact_root / "stage-4-normal.png"
            product_svg = artifact_root / "stage-4-product.svg"
            manifest = artifact_root / "stage-4-manifest.json"
            highlights = artifact_root / "stage-4-highlights.json"
            Image.new("RGB", (128, 64), (1, 2, 3)).save(normal)
            product_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            _write_json(manifest, stage4_document)
            _write_json(
                highlights,
                {
                    "regions": [
                        {"id": region["id"], "key": region["key"]}
                        for region in stage4_document["regions"]
                    ]
                },
            )
            candidate.update(
                {
                    "regionCount": len(stage4_document["regions"]),
                    "normal": {"fileSha256": _hash_file(normal)},
                    "productSvg": {"fileSha256": _hash_file(product_svg)},
                    "manifest": {"fileSha256": _hash_file(manifest)},
                    "highlights": {"fileSha256": _hash_file(highlights)},
                }
            )
        return candidate

    def _stage2_document(self) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "labelEncoding": "uint16-region-id",
            "regions": [
                {
                    "anchor": [10 + 20 * offset, 15],
                    "areaPixels": 100,
                    "bounds": [5 + 20 * offset, 10, 16 + 20 * offset, 21],
                    "contour": [
                        [5 + 20 * offset, 10],
                        [15 + 20 * offset, 10],
                        [15 + 20 * offset, 20],
                        [5 + 20 * offset, 20],
                    ],
                    "id": index,
                    "key": key,
                    "metadata": {"fixture": True},
                    "type": "pocket",
                }
                for offset, (index, key) in enumerate(
                    enumerate(self.region_keys, start=1)
                )
            ],
            "schemaVersion": 1,
            "stage": 2,
        }

    def _stage3_document(
        self, source_regions: list[Mapping[str, object]]
    ) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "pieceCount": 1,
            "regions": [
                {
                    "anchor": list(region["anchor"]),
                    "displayPath": _contour_display_path(region["contour"]),
                    "id": region["id"],
                    "key": region["key"],
                    "metadata": dict(region["metadata"]),
                    "pieceIndex": 0,
                    "primitive": "fixture-polygon",
                    "type": region["type"],
                }
                for region in source_regions
            ],
            "schemaVersion": 1,
            "silhouettePaths": [
                {
                    "displayPath": "M 0 0 L 128 0 L 128 64 L 0 64 Z",
                    "id": "piece-01-silhouette",
                    "pieceIndex": 0,
                    "primitive": "fixture-polygon",
                }
            ],
            "stage": 3,
        }

    def _stage4_document(
        self, source_regions: list[Mapping[str, object]]
    ) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "regions": [
                {"id": region["id"], "key": region["key"]}
                for region in source_regions
            ],
            "schemaVersion": 1,
            "stage": 4,
        }


class _BrokenStage3Runner(_StubStageRunner):
    def __init__(self, decoy_keys: tuple[str, ...], mutation: str) -> None:
        super().__init__(3, decoy_keys)
        assert mutation in {"mutate", "drop", "reorder"}
        self.mutation = mutation

    def _stage3_document(
        self, source_regions: list[Mapping[str, object]]
    ) -> dict[str, object]:
        corrupted = deepcopy(source_regions)
        if self.mutation == "mutate":
            corrupted[0]["key"] = "changed-key"
        elif self.mutation == "drop":
            corrupted.pop()
        else:
            corrupted[0], corrupted[1] = corrupted[1], corrupted[0]
        return super()._stage3_document(corrupted)


def _stage_document(run_root: Path, stage: int, filename: str) -> dict[str, object]:
    manifest = json.loads((run_root / "run.json").read_text(encoding="utf-8"))
    record = manifest["stages"][stage]
    document = json.loads(
        (run_root / record["artifactRoot"] / filename).read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    return document


def _accepted_stage_document(
    context: RunContext,
    stage: int,
    acceptance_field: str,
    filename: str,
) -> dict[str, object]:
    record = context.manifest["stages"][stage]
    assert record["status"] == "approved"
    acceptance_path = context.root / record["acceptancePath"]
    assert _hash_file(acceptance_path) == record["acceptanceSha256"]
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    binding = acceptance[acceptance_field]
    artifact_path = context.root / binding["path"]
    assert artifact_path.name == filename
    assert _hash_file(artifact_path) == binding["fileSha256"]
    document = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _contour_display_path(contour: object) -> str:
    assert isinstance(contour, list) and len(contour) >= 3
    first, *remaining = contour
    commands = [f"M {first[0]} {first[1]}"]
    commands.extend(f"L {point[0]} {point[1]}" for point in remaining)
    return " ".join((*commands, "Z"))


def _region_identity(
    document: Mapping[str, object],
) -> tuple[list[object], list[object]]:
    regions = document["regions"]
    assert isinstance(regions, list)
    return (
        [region["id"] for region in regions],
        [region["key"] for region in regions],
    )


def _assert_stable_identity_chain(*documents: Mapping[str, object]) -> None:
    identities = [_region_identity(document) for document in documents]
    assert all(identity == identities[0] for identity in identities[1:]), (
        "stable region identity did not propagate between stages"
    )


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
