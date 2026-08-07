from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer.board_library import BoardLibraryError, RepositoryBoardLibrary
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboarding_run import (
    RunContext,
    approve_stage,
    read_status,
    resume_run,
    start_run,
)


def test_list_boards_returns_validated_casefold_order(tmp_path: Path) -> None:
    library = _library_with_packages(tmp_path, ("Zulu", "alpha", "Alpha"))

    assert [(item.display_name, item.board_id) for item in library.list_boards()] == [
        ("alpha", "alpha"),
        ("Alpha", "alpha-2"),
        ("Zulu", "zulu"),
    ]


@pytest.mark.parametrize("package_path", ("../outside", "/tmp/outside"))
def test_catalog_rejects_package_paths_outside_library(
    tmp_path: Path, package_path: str
) -> None:
    library = _library_with_catalog_entry(tmp_path, package_path=package_path)

    with pytest.raises(BoardLibraryError, match="packagePath"):
        library.list_boards()


def test_catalog_rejects_duplicate_ids_and_unknown_schema_versions(tmp_path: Path) -> None:
    library = _library_with_packages(tmp_path, ("Alpha",))
    catalog = _read_json(_library_root(tmp_path) / "catalog.json")
    catalog["boards"].append(dict(catalog["boards"][0]))
    _write_json(_library_root(tmp_path) / "catalog.json", catalog)

    with pytest.raises(BoardLibraryError, match="duplicate boardId"):
        library.list_boards()

    catalog["boards"] = catalog["boards"][:1]
    catalog["schemaVersion"] = 2
    _write_json(_library_root(tmp_path) / "catalog.json", catalog)
    with pytest.raises(BoardLibraryError, match="catalog schema"):
        library.list_boards()


def test_list_boards_rejects_symlinked_packages_and_bad_published_hashes(
    tmp_path: Path,
) -> None:
    library, board = _complete_library(tmp_path)
    package = board.package_path
    moved = package.with_name("moved-package")
    package.rename(moved)
    package.symlink_to(moved, target_is_directory=True)

    with pytest.raises(BoardLibraryError, match="symlink"):
        library.list_boards()

    package.unlink()
    moved.rename(package)
    published = _read_json(package / "versions" / "revision-0001" / "published.json")
    published["definition"]["sha256"] = "0" * 64
    _write_json(package / "versions" / "revision-0001" / "published.json", published)
    with pytest.raises(BoardLibraryError, match="published"):
        library.list_boards()


def test_copy_current_run_stages_then_atomically_renames(tmp_path: Path) -> None:
    library, expected = _complete_library(tmp_path)
    destination = tmp_path / "runtime" / "run"

    opened = library.copy_current_run(expected.board_id, destination)

    assert opened.current_run_path != destination
    assert {key: value for key, value in read_status(destination).items() if key != "run"} == {
        key: value
        for key, value in read_status(opened.current_run_path).items()
        if key != "run"
    }
    assert not list(destination.parent.glob(f".{destination.name}.tmp-*"))


def test_copy_current_run_rejects_an_existing_destination(tmp_path: Path) -> None:
    library, board = _complete_library(tmp_path)
    destination = tmp_path / "runtime" / "run"
    destination.mkdir(parents=True)

    with pytest.raises(BoardLibraryError, match="destination already exists"):
        library.copy_current_run(board.board_id, destination)


def test_publish_appends_version_without_mutating_previous_version(tmp_path: Path) -> None:
    library, original = _complete_library(tmp_path)
    old_hashes = _tree_hashes(original.current_run_path)

    result = library.publish(
        display_name=original.display_name,
        run_root=_complete_fixture_run(tmp_path / "new-run"),
        board_id=original.board_id,
        expected_current_version_id=original.current_version_id,
    )

    assert result.version_id == "revision-0002"
    assert _tree_hashes(original.current_run_path) == old_hashes
    assert library.get_board(original.board_id).current_version_id == "revision-0002"


def test_list_boards_rejects_a_corrupted_noncurrent_published_version(
    tmp_path: Path,
) -> None:
    library, original = _complete_library(tmp_path)
    library.publish(
        display_name=original.display_name,
        run_root=_complete_fixture_run(tmp_path / "new-run"),
        board_id=original.board_id,
        expected_current_version_id=original.current_version_id,
    )
    published_path = (
        original.package_path / "versions" / "revision-0001" / "published.json"
    )
    published = _read_json(published_path)
    published["definition"]["sha256"] = "0" * 64
    _write_json(published_path, published)

    with pytest.raises(BoardLibraryError, match="published"):
        library.list_boards()


def test_publish_conflict_leaves_current_pointer_unchanged(tmp_path: Path) -> None:
    library, original = _complete_library(tmp_path)

    with pytest.raises(BoardLibraryError, match="expected revision-0000.*revision-0001"):
        library.publish(
            display_name=original.display_name,
            run_root=_complete_fixture_run(tmp_path / "new-run"),
            board_id=original.board_id,
            expected_current_version_id="revision-0000",
        )

    assert library.get_board(original.board_id).current_version_id == "revision-0001"


@pytest.mark.parametrize("failure", ("version", "board", "catalog"))
def test_publish_failures_preserve_prior_visibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    library, original = _complete_library(tmp_path)
    new_board = failure == "catalog"
    run = _complete_fixture_run(tmp_path / "new-run")
    actual_replace = __import__("os").replace

    def fail_selected_replace(source: object, destination: object) -> None:
        target = Path(destination)
        if (
            failure == "version" and target.name == "revision-0002"
        ) or (failure == "board" and target.name == "board.json") or (
            failure == "catalog" and target.name == "catalog.json"
        ):
            raise OSError(f"{failure} replacement interrupted")
        actual_replace(source, destination)

    monkeypatch.setattr("hangboard_vectorizer.board_library.os.replace", fail_selected_replace)
    with pytest.raises(OSError, match=f"{failure} replacement interrupted"):
        library.publish(
            display_name="New Board" if new_board else original.display_name,
            run_root=run,
            board_id=None if new_board else original.board_id,
            expected_current_version_id=None if new_board else original.current_version_id,
        )

    if new_board:
        assert [item.board_id for item in library.list_boards()] == [original.board_id]
    else:
        assert library.get_board(original.board_id).current_version_id == "revision-0001"


def _library_with_packages(root: Path, names: tuple[str, ...]) -> RepositoryBoardLibrary:
    library_root = _library_root(root)
    boards: list[dict[str, str]] = []
    for name in names:
        board_id = _slug(name)
        suffix = 2
        while any(entry["boardId"] == board_id for entry in boards):
            board_id = f"{_slug(name)}-{suffix}"
            suffix += 1
        _write_package(root, board_id=board_id, display_name=name)
        boards.append(
            {
                "boardId": board_id,
                "displayName": name,
                "packagePath": f"boards/{board_id}",
            }
        )
    _write_json(library_root / "catalog.json", {"schemaVersion": 1, "boards": boards})
    return RepositoryBoardLibrary(root)


def _library_with_catalog_entry(root: Path, *, package_path: str) -> RepositoryBoardLibrary:
    library_root = _library_root(root)
    library_root.mkdir(parents=True)
    _write_json(
        library_root / "catalog.json",
        {
            "schemaVersion": 1,
            "boards": [
                {
                    "boardId": "example-board",
                    "displayName": "Example Board",
                    "packagePath": package_path,
                }
            ],
        },
    )
    return RepositoryBoardLibrary(root)


def _complete_library(root: Path) -> tuple[RepositoryBoardLibrary, object]:
    library = _library_with_packages(root, ("Example Board",))
    return library, library.get_board("example-board")


def _write_package(root: Path, *, board_id: str, display_name: str) -> None:
    package = _library_root(root) / "boards" / board_id
    run = _complete_fixture_run(package / "versions" / "revision-0001" / "run")
    acceptance = _stage4_acceptance(run)
    published = {
        "schemaVersion": 1,
        "runIdentitySha256": _read_json(run / "run.json")["runIdentitySha256"],
        "definition": _published_output(acceptance["manifest"]),
        "image": _published_output(acceptance["normal"]),
        "selectableSvg": _published_output(acceptance["productSvg"]),
        "highlights": _published_output(acceptance["highlights"]),
    }
    _write_json(package / "versions" / "revision-0001" / "published.json", published)
    _write_json(
        package / "board.json",
        {
            "schemaVersion": 1,
            "boardId": board_id,
            "displayName": display_name,
            "currentVersionId": "revision-0001",
            "versions": [
                {
                    "versionId": "revision-0001",
                    "parentVersionId": None,
                    "publishedAt": "2026-08-07T00:00:00Z",
                    "publishedPath": "versions/revision-0001",
                }
            ],
        },
    )


def _complete_fixture_run(run: Path) -> Path:
    source = run.parent / f"{run.name}-source.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    runners = {stage: _StubStageRunner(stage) for stage in range(5)}
    start_run("Example Board", str(source), run, runners=runners, workspace_root=run.parent)
    for stage in range(5):
        approve_stage(run, stage)
        if stage < 4:
            resume_run(run, runners=runners)
    assert read_status(run)["status"] == "complete"
    return run


def _stage4_acceptance(run: Path) -> dict[str, object]:
    manifest = _read_json(run / "run.json")
    stage = manifest["stages"][4]
    return _read_json(run / stage["acceptancePath"])


def _published_output(value: object) -> dict[str, str]:
    assert isinstance(value, dict)
    return {"path": f"run/{value['path']}", "sha256": value["fileSha256"]}


def _library_root(root: Path) -> Path:
    return root / "Tools" / "HangboardOnboarding" / "board-library"


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _slug(value: str) -> str:
    return "-".join(value.lower().split())


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _StubStageRunner:
    def __init__(self, stage: int) -> None:
        self.stage = stage

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        Image.new("RGB", (4, 4), (120, 80, 40)).save(review)
        candidate = self._candidate(context, artifact_root)
        _write_json(artifact_root / f"stage-{self.stage}-candidate.json", candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        _write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(self.stage, artifact_root, hashes, review, True)

    def _candidate(self, context: RunContext, root: Path) -> dict[str, object]:
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
            return candidate
        stages = context.manifest["stages"]
        assert isinstance(stages, list) and isinstance(stages[-1], dict)
        candidate["inputAcceptance"] = {
            "path": stages[-1]["acceptancePath"],
            "sha256": stages[-1]["acceptanceSha256"],
        }
        if self.stage == 1:
            path = root / "stage-1-auto-rgba.png"
            Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(path)
            candidate["registered"] = {"fileSha256": _hash(path)}
        elif self.stage == 2:
            regions, labels = root / "stage-2-regions.json", root / "stage-2-labels.png"
            _write_json(regions, {"canvas": {"width": 4, "height": 4}, "regions": []})
            Image.new("I;16", (4, 4), 0).save(labels)
            candidate.update({"regionCount": 0, "regions": {"fileSha256": _hash(regions)}, "registered": {"fileSha256": _hash(labels)}})
        elif self.stage == 3:
            regions, svg = root / "stage-3-vector-regions.json", root / "stage-3-vector.svg"
            _write_json(regions, {"canvas": {"width": 4, "height": 4}, "regions": []})
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
            candidate.update({"regionCount": 0, "vectorRegions": {"fileSha256": _hash(regions)}, "vectorSvg": {"fileSha256": _hash(svg)}})
        else:
            candidate["regionCount"] = 0
            for field, name in (("normal", "stage-4-normal.png"), ("productSvg", "stage-4-product.svg"), ("manifest", "stage-4-manifest.json"), ("highlights", "stage-4-highlights.json")):
                path = root / name
                if path.suffix == ".png":
                    Image.new("RGB", (4, 4), (1, 2, 3)).save(path)
                elif path.suffix == ".svg":
                    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
                else:
                    _write_json(path, {})
                candidate[field] = {"fileSha256": _hash(path)}
        return candidate


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
