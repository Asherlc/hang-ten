from __future__ import annotations

import ast
from collections.abc import Mapping
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image
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
    monkeypatch: pytest.MonkeyPatch,
    product_name: str,
    color: tuple[int, int, int],
    region_keys: tuple[str, ...],
) -> None:
    service = _fixture_service(tmp_path, region_keys=region_keys)
    monkeypatch.setattr(
        workbench_module,
        "materialize_stage2_edit",
        lambda context, document, artifact_root: _materialize_fixture_edit(
            2, region_keys, context, document, artifact_root
        ),
    )
    monkeypatch.setattr(
        workbench_module,
        "materialize_stage3_edit",
        lambda context, document, artifact_root: _materialize_fixture_edit(
            3, region_keys, context, document, artifact_root
        ),
    )

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

    stage4 = _stage_document(current.run_root, 4, "stage-4-manifest.json")
    assert set(stage4) == {"canvas", "regions", "schemaVersion", "stage"}
    expected_ids = list(range(1, len(region_keys) + 1))
    assert _region_identity(stage2) == (expected_ids, list(region_keys))
    assert _region_identity(stage3) == (expected_ids, list(region_keys))
    assert _region_identity(stage4) == (expected_ids, list(region_keys))
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


def test_workbench_control_flow_contains_no_product_key_conditionals() -> None:
    python_modules = (
        Path(workbench_module.__file__).resolve(),
        Path(workbench_module.__file__).with_name("workbench_store.py").resolve(),
        Path(workbench_module.__file__).with_name("review_edits.py").resolve(),
    )
    editor_root = Path(__file__).resolve().parents[2] / "hold-highlight-editor"
    javascript_modules = tuple(editor_root.glob("workbench-*.js"))

    assert {
        path.name: _product_specific_branches(path)
        for path in (*python_modules, *javascript_modules)
        if _product_specific_branches(path)
    } == {}


def _fixture_image_bytes(color: tuple[int, int, int] = (45, 65, 85)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (512, 256), color).save(stream, format="PNG")
    return stream.getvalue()


def _fixture_service(
    root: Path, *, region_keys: tuple[str, ...] = ("grip-001",)
) -> WorkbenchService:
    return WorkbenchService(
        WorkbenchStore(root), runners=_stub_runners(region_keys)
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
) -> dict[int, _StubStageRunner]:
    return {
        stage: _StubStageRunner(stage, region_keys) for stage in range(5)
    }


def _materialize_fixture_edit(
    stage: int,
    region_keys: tuple[str, ...],
    context: RunContext,
    document: Mapping[str, object],
    artifact_root: Path,
) -> StageCheckpoint:
    return _StubStageRunner(
        stage, region_keys, document_override=document
    ).run(context, artifact_root)


class _StubStageRunner:
    def __init__(
        self,
        stage: int,
        region_keys: tuple[str, ...],
        *,
        document_override: Mapping[str, object] | None = None,
    ) -> None:
        self.stage = stage
        self.region_keys = region_keys
        self.document_override = document_override

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
            candidate["registered"] = {"fileSha256": _hash_file(registered)}
        elif self.stage == 2:
            regions = artifact_root / "stage-2-regions.json"
            labels = artifact_root / "stage-2-labels.png"
            _write_json(regions, self.document_override or self._stage2_document())
            Image.new("I;16", (128, 64), 0).save(labels)
            candidate.update(
                {
                    "regionCount": len(self.region_keys),
                    "regions": {"fileSha256": _hash_file(regions)},
                    "registered": {"fileSha256": _hash_file(labels)},
                }
            )
        elif self.stage == 3:
            regions = artifact_root / "stage-3-vector-regions.json"
            svg = artifact_root / "stage-3-vector.svg"
            _write_json(regions, self.document_override or self._stage3_document())
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            candidate.update(
                {
                    "regionCount": len(self.region_keys),
                    "vectorRegions": {"fileSha256": _hash_file(regions)},
                    "vectorSvg": {"fileSha256": _hash_file(svg)},
                }
            )
        else:
            normal = artifact_root / "stage-4-normal.png"
            product_svg = artifact_root / "stage-4-product.svg"
            manifest = artifact_root / "stage-4-manifest.json"
            highlights = artifact_root / "stage-4-highlights.json"
            Image.new("RGB", (128, 64), (1, 2, 3)).save(normal)
            product_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            _write_json(manifest, self._stage4_document())
            _write_json(
                highlights,
                {
                    "regions": [
                        {"id": index, "key": key}
                        for index, key in enumerate(self.region_keys, start=1)
                    ]
                },
            )
            candidate.update(
                {
                    "regionCount": len(self.region_keys),
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

    def _stage3_document(self) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "pieceCount": 1,
            "regions": [
                {
                    "anchor": [10 + 20 * offset, 15],
                    "displayPath": (
                        f"M {5 + 20 * offset} 10 L {15 + 20 * offset} 10 "
                        f"L {15 + 20 * offset} 20 L {5 + 20 * offset} 20 Z"
                    ),
                    "id": index,
                    "key": key,
                    "metadata": {"fixture": True},
                    "pieceIndex": 0,
                    "primitive": "fixture-polygon",
                    "type": "pocket",
                }
                for offset, (index, key) in enumerate(
                    enumerate(self.region_keys, start=1)
                )
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

    def _stage4_document(self) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "regions": [
                {"id": index, "key": key}
                for index, key in enumerate(self.region_keys, start=1)
            ],
            "schemaVersion": 1,
            "stage": 4,
        }


def _stage_document(run_root: Path, stage: int, filename: str) -> dict[str, object]:
    manifest = json.loads((run_root / "run.json").read_text(encoding="utf-8"))
    record = manifest["stages"][stage]
    document = json.loads(
        (run_root / record["artifactRoot"] / filename).read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    return document


def _region_identity(
    document: Mapping[str, object],
) -> tuple[list[object], list[object]]:
    regions = document["regions"]
    assert isinstance(regions, list)
    return (
        [region["id"] for region in regions],
        [region["key"] for region in regions],
    )


def _product_specific_branches(path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    product_keys = re.compile(
        r"beastmaker|metolius|wood[-_ ]grips|compact[-_ ]ii|simulator[-_ ]3d",
        re.IGNORECASE,
    )
    if path.suffix == ".py":
        tree = ast.parse(source)
        conditionals = (
            node.test
            for node in ast.walk(tree)
            if isinstance(node, (ast.If, ast.IfExp, ast.While))
        )
        return tuple(
            segment
            for condition in conditionals
            if (segment := ast.get_source_segment(source, condition)) is not None
            and product_keys.search(segment)
        )
    conditional = re.compile(
        r"\b(?:if|switch|case)\b[^\n{};]*(?:"
        + product_keys.pattern
        + r")",
        re.IGNORECASE,
    )
    return tuple(match.group(0) for match in conditional.finditer(source))


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
