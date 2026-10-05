"""CAD CLI consumers keep authoring metadata separate from generated packages."""
from pathlib import Path
import importlib.util
import json
import sys
from types import SimpleNamespace
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board_manifest
import set_cad_authoring
from cad_authoring_fixtures import canonical_pose, write_native_authoring


def test_package_source_is_flat_and_discovery_ignores_nested_sources(tmp_path):
    root = tmp_path / "Hangboards"
    root.mkdir()
    for slug in ("example", "another"):
        (root / f"{slug}.FCStd").write_bytes(b"native source")
    nested = root / "obsolete"
    nested.mkdir()
    (nested / "obsolete.FCStd").write_bytes(b"obsolete nested source")

    assert board_manifest.package_source(tmp_path, "example") == root / "example.FCStd"
    assert board_manifest.source_backed_packages(tmp_path) == ["another", "example"]


def test_generated_board_cannot_be_written_inside_its_package(tmp_path):
    source = tmp_path / "Hangboards/example.FCStd"
    package = source.parent / source.stem
    package.mkdir(parents=True)
    with pytest.raises(board_manifest.cad_source.ManifestError, match="must not exist"):
        board_manifest.write_board_json(source, package / "board.json")


def test_textconv_pretty_prints_all_native_json_properties(tmp_path):
    source = tmp_path / "example.FCStd"
    document = b'''<Document><Properties Count="4">
      <Property name="HangTenBoardID" type="App::PropertyString"><String value="example"/></Property>
      <Property name="HangTenBoardManifest" type="App::PropertyString"><String value="{&quot;schemaVersion&quot;:3}"/></Property>
      <Property name="HangTenSuspensionAuthoring" type="App::PropertyString"><String value="{&quot;schemaVersion&quot;:1,&quot;presentationID&quot;:&quot;front&quot;}"/></Property>
      <Property name="HangTenRopePhysics" type="App::PropertyString"><String value="{&quot;bodyFeature&quot;:&quot;Solid&quot;}"/></Property>
    </Properties></Document>'''
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("Document.xml", document)
        archive.writestr("Shape.brp", b"retained shape")

    rendering = board_manifest.describe_source(source)
    assert '# HangTenSuspensionAuthoring\n{\n  "schemaVersion": 1,' in rendering
    assert '# HangTenRopePhysics\n{\n  "bodyFeature": "Solid"\n}' in rendering
    assert "HangTenSuspensionAuthoring =" not in rendering
    assert "HangTenRopePhysics =" not in rendering
    assert "Shape.brp" in rendering


@pytest.mark.parametrize("field", ["suspension", "rope-physics"])
def test_editor_preserves_untargeted_property_and_does_not_read_generated_cache(
    tmp_path, monkeypatch, field,
):
    source = tmp_path / "fixture.FCStd"
    source.write_bytes(b"native source")
    input_path = tmp_path / "input.json"
    replacement = {"schemaVersion": 1, "new": field}
    input_path.write_text(json.dumps(replacement))
    existing = {"suspension": {"authored": "suspension"},
                "rope-physics": {"authored": "physics"}}
    reads = []
    for name, loader in (("suspension", "load_suspension_authoring"),
                         ("rope-physics", "load_rope_physics_authoring")):
        def read(path, property_name=name):
            assert path == source
            reads.append(property_name)
            return existing[property_name]
        monkeypatch.setattr(board_manifest.cad_source, loader, read, raising=False)
    writes = []
    monkeypatch.setattr(board_manifest.cad_source, "embed_authoring",
                        lambda path, **kwargs: writes.append((path, kwargs)) or True,
                        raising=False)

    assert set_cad_authoring.main(["--source", str(source), f"--{field}", str(input_path)]) == 0
    expected = dict(suspension=existing["suspension"], rope_physics=existing["rope-physics"])
    expected[field.replace("-", "_")] = replacement
    assert writes == [(source, expected)]
    assert reads == (["rope-physics"] if field == "suspension" else ["suspension"])


def test_editor_removes_only_the_selected_authoring_property(tmp_path, monkeypatch):
    source = tmp_path / "fixture.FCStd"
    retained_physics = {"bodyFeature": "Solid", "channelFeatures": {}, "profiles": []}
    monkeypatch.setattr(board_manifest.cad_source, "load_rope_physics_authoring",
                        lambda path: retained_physics, raising=False)
    writes = []
    monkeypatch.setattr(board_manifest.cad_source, "embed_authoring",
                        lambda path, **kwargs: writes.append((path, kwargs)) or True,
                        raising=False)
    assert set_cad_authoring.main(["--source", str(source), "--remove-suspension"]) == 0
    assert writes == [(source, {"suspension": None, "rope_physics": retained_physics})]


def test_editor_rejects_an_empty_package_name(capsys):
    with pytest.raises(SystemExit) as raised:
        set_cad_authoring.main(["--package", "", "--remove-suspension"])
    assert raised.value.code == 2
    assert "invalid package name" in capsys.readouterr().err


@pytest.mark.parametrize("board_id, expected_id", [
    ("review.board", "review.board"),
    ('board&<>"\'', 'board&<>"\''),
    (None, "fixture.board"),
])
def test_native_authoring_fixture_preserves_board_identity(tmp_path, board_id, expected_id):
    board = {"name": "Fixture board"}
    if board_id is not None:
        board["id"] = board_id
    authoring = {"schemaVersion": 1, "presentationID": "primary", "suspension": {
        "type": "twoBranchCord", "canonicalPoses": {"front": canonical_pose()},
    }}
    source = write_native_authoring(tmp_path / "fixture", board, authoring)

    assert board_manifest.cad_source.load_board(source) == {
        "schemaVersion": 3, "id": expected_id, "name": "Fixture board",
    }


def test_dump_and_editor_round_trip_embedded_authoring_without_a_generated_package(
    tmp_path, capsys,
):
    package = tmp_path / "Hangboards/fixture"
    package.mkdir(parents=True)
    authoring = {"schemaVersion": 1, "presentationID": "front", "suspension": {
        "type": "twoBranchCord", "canonicalPoses": {
            "upright": {**canonical_pose(), "offsetXZ": [.02, -.03]},
        },
    }}
    board = {"presentations": [{"id": "front", "media": {
        "type": "model", "descriptorPath": "assets/primary.model.json",
    }}]}
    source = write_native_authoring(package, board, authoring)
    assert not (package / "assets").exists()
    assert board_manifest.main([
        "--root", str(tmp_path), "--package", "fixture", "--dump-authoring", "suspension",
    ]) == 0
    assert json.loads(capsys.readouterr().out) == authoring
    edited = tmp_path / "edited.json"
    authoring["suspension"]["canonicalPoses"]["upright"]["offsetXZ"] = [.04, -.01]
    edited.write_text(json.dumps(authoring))
    assert set_cad_authoring.main(["--source", str(source), "--suspension", str(edited)]) == 0
    assert board_manifest.cad_source.load_suspension_authoring(source) == authoring
    assert set_cad_authoring.main(["--source", str(source), "--remove-suspension"]) == 0
    assert board_manifest.cad_source.load_suspension_authoring(source) is None


def test_channel_measurement_selects_authored_multi_presentation_instances(monkeypatch):
    monkeypatch.setitem(sys.modules, "FreeCAD", SimpleNamespace())
    import measure_channel_spines
    first, second = {"label": "left"}, {"label": "right"}
    data = {"schemaVersion": 2, "entries": [
        {"presentationID": "pair", "equipmentObjectID": "left", "suspension": first},
        {"presentationID": "pair", "equipmentObjectID": "right", "suspension": second},
        {"presentationID": "single", "suspension": {"label": "single"}},
    ]}
    assert measure_channel_spines.selected_suspension(data, "pair", "left") is first
    assert measure_channel_spines.selected_suspension(data, "pair", "right") is second
    assert measure_channel_spines.selected_suspension(data, "single") == {"label": "single"}
    with pytest.raises(ValueError, match="select exactly one"):
        measure_channel_spines.selected_suspension(data)


@pytest.fixture
def reusable_instance_authoring():
    def setup(offset):
        return {"type": "twoBranchCord", "canonicalPoses": {
            "front": {**canonical_pose(), "offsetXZ": offset},
        }}

    return board_manifest.cad_source.validate_suspension_authoring({
        "schemaVersion": 2, "entries": [
            {"presentationID": "pair", "instanceSuspensions": {
                "left": setup([-.02, 0]), "right": setup([.02, 0]),
            }},
            {"presentationID": "back", "instanceSuspensions": {
                "left": setup([0, -.01]),
            }},
            {"presentationID": "single", "suspension": setup([0, 0])},
        ],
    })


@pytest.mark.parametrize("presentation_id,equipment_id,expected_offset", [
    ("pair", "left", [-.02, 0]),
    ("pair", "right", [.02, 0]),
    (None, "right", [.02, 0]),
    ("back", "left", [0, -.01]),
])
def test_channel_measurement_selects_instance_maps_inside_collections(
    monkeypatch, reusable_instance_authoring, presentation_id, equipment_id, expected_offset,
):
    monkeypatch.setitem(sys.modules, "FreeCAD", SimpleNamespace())
    import measure_channel_spines

    setup = measure_channel_spines.selected_suspension(
        reusable_instance_authoring, presentation_id, equipment_id,
    )
    assert setup["canonicalPoses"]["front"]["offsetXZ"] == expected_offset


@pytest.mark.parametrize("presentation_id,equipment_id", [
    (None, None), ("pair", None), ("back", None), (None, "left"),
    ("pair", "missing"), ("missing", "right"),
])
def test_channel_measurement_rejects_missing_or_ambiguous_instance_map_selections(
    monkeypatch, reusable_instance_authoring, presentation_id, equipment_id,
):
    monkeypatch.setitem(sys.modules, "FreeCAD", SimpleNamespace())
    import measure_channel_spines

    with pytest.raises(ValueError, match="HANGTEN_CHANNEL_"):
        measure_channel_spines.selected_suspension(
            reusable_instance_authoring, presentation_id, equipment_id,
        )


@pytest.mark.parametrize("target", ["xcode", "android"])
def test_staging_delivers_merged_metadata_without_native_source_or_generated_cache(
    tmp_path, monkeypatch, target,
):
    script = Path(__file__).resolve().parents[3] / "scripts/stage-board-packages.py"
    spec = importlib.util.spec_from_file_location("cad_consumer_staging", script)
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    repository = tmp_path / "repository"
    package_root = repository / "Hangboards/fixture"
    assets = package_root / "assets"
    assets.mkdir(parents=True)
    (repository / "Hangboards/fixture.FCStd").write_bytes(b"retained native source")
    (assets / "primary.usdz").write_bytes(b"generated model")
    (assets / "primary.model.json").write_text("{}")
    (assets / "suspension.json").write_text('{"generatedRoutes":"cache"}')
    generated_board = b'{"id":"fixture","suspension":{"type":"twoBranchCord"}}\n'
    class ModelMedia:
        asset_path = "assets/primary.usdz"
    package = SimpleNamespace(
        root=package_root,
        board=SimpleNamespace(presentations=[SimpleNamespace(media=ModelMedia())]),
        generated_board_json=generated_board,
    )
    package_module = SimpleNamespace(
        discover_board_packages=lambda root: SimpleNamespace(packages=[package]),
        PresentationMediaModel=ModelMedia,
    )
    monkeypatch.setattr(staging, "load_board_package_module", lambda root: package_module)
    if target == "xcode":
        destination = tmp_path / "build/Resources/Hangboards"
        monkeypatch.setenv("TARGET_BUILD_DIR", str(tmp_path / "build"))
        monkeypatch.setenv("UNLOCALIZED_RESOURCES_FOLDER_PATH", "Resources")
        monkeypatch.setenv("DERIVED_FILE_DIR", str(tmp_path / "derived"))
    else:
        destination = tmp_path / "android/Hangboards"

    staging.stage_board_packages(repository, destination, target=target)
    assert (destination / "fixture/board.json").read_bytes() == generated_board
    staged_files = {path.relative_to(destination).as_posix()
                    for path in destination.rglob("*") if path.is_file()}
    assert "fixture/assets/suspension.json" not in staged_files
    assert not any(path.endswith(".FCStd") for path in staged_files)
    assert ("fixture/assets/primary.usdz" in staged_files) == (target == "android")
    if target == "xcode":
        odr_files = {path.name for path in (tmp_path / "derived").rglob("*") if path.is_file()}
        assert odr_files == {"primary.usdz"}
