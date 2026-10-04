"""Native cord authoring and generated suspension must stay source-bound."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import use_hangboard_packages  # noqa: E402,F401
from hangboard_packages import cad_source  # noqa: E402


def native_source(tmp_path: Path, properties=()) -> Path:
    source = tmp_path / "example.FCStd"
    document = ET.Element("Document", SchemaVersion="4", FileVersion="1")
    values = ET.SubElement(document, "Properties", Count=str(len(properties)), TransientCount="0")
    for name, kind, text in properties:
        prop = ET.SubElement(values, "Property", name=name, type=kind)
        ET.SubElement(prop, "String", value=text)
    objects = ET.SubElement(document, "Objects", Count="1")
    ET.SubElement(objects, "Object", name="Body", type="PartDesign::Body")
    data = ET.SubElement(document, "ObjectData", Count="1")
    ET.SubElement(data, "Object", name="Body")
    ET.indent(document, space="    ")
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.comment = b"retained source comment"
        archive.writestr("Document.xml", ET.tostring(document, encoding="utf-8"))
        archive.writestr("Body.Shape.brp", b"exact retained geometry")
        archive.writestr("GuiDocument.xml", b"exact retained display settings")
    source.chmod(0o644)
    return source


def suspension_authoring() -> dict:
    return cad_source.loads('''{
      "schemaVersion":1,"presentationID":"primary",
      "suspension":{
        "type":"cadRoutedCord","bodyNodeID":"body",
        "strands":[{"id":"lead","kind":"lead","restLength":0.5,
          "radius":0.002,"material":"matteCord",
          "provenance":"Owner-confirmed visible lead; 0.5 m is a display estimate."}],
        "anchor":{"offsetFromBoardBounds":[0,0.08,0],"visibility":"invisible",
          "provenance":"Display estimate: support height above the board."},
        "canonicalPoses":{
          "front":{"rotation":[0,0,0,1],"offsetXZ":[0.000000000,-0.012500000],
            "camera":{"viewDirection":[0,0,-1],"fitPadding":0.1}},
          "back":{"rotation":[0,1,0,0],
            "camera":{"viewDirection":[0,0,-1],"fitPadding":0.1}}}},
      "ropeSolver":{"method":"nativeRoutes","clearance":0.0002,
        "terminalsByStrandID":{"lead":{"points":[[0,0.03,0]],"planeNormal":[1,0,0]}}}
    }''')


def physics_authoring() -> dict:
    return {
        "bodyFeature": "Body",
        "channelFeatures": {"central": "Bore"},
        "profiles": [{
            "id": "front", "presentationID": "primary",
            "boardMass": {"value": 1, "provenance": "Display estimate: 1 kg."},
            "ropes": [{
                "id": "rope", "baselineRadius": 0.002, "thicknessScale": 1,
                "radius": 0.002, "restLength": 0.5,
                "lengthProvenance": "Display estimate: 0.5 m.",
                "linearMass": {"value": 0.01, "provenance": "Display estimate: 0.01 kg/m."},
                "nodes": [{"id": "start", "kind": "support", "point": [0, 0.1, 0]},
                          {"id": "end", "kind": "attachment", "point": [0, 0, 0]}],
                "edges": [{"from": "start", "to": "end", "kind": "free"}],
            }],
        }],
    }


def archive_members(source: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(source) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def compiled_fixture(tmp_path: Path, authoring: dict | None = None):
    authored = suspension_authoring() if authoring is None else authoring
    source = native_source(tmp_path, [("HangTenBoardID", "App::PropertyString", "example")])
    cad_source.embed_authoring(source, suspension=authored)
    package = tmp_path / "example"
    (package / "assets").mkdir(parents=True)
    board = {"presentations": [{"id": "primary", "media": {
        "type": "model", "descriptorPath": "assets/primary.model.json", "orientation": {}}}]}
    (package / "assets/primary.model.json").write_text(json.dumps({"modelSHA256": "a" * 64}))
    artifact = cad_source.materialize_suspension(authored, {"primary": "a" * 64},
                                               hashlib.sha256(source.read_bytes()).hexdigest())
    entries = artifact.get("entries", [artifact])
    for entry in entries:
        setups = entry.get("instanceSuspensions", {"": entry.get("suspension")})
        for setup in setups.values():
            cache_key = "wrappedRoutes" if setup["type"] == "cadRoutedCord" else "cordContactPoints"
            identifiers = [strand["id"] for strand in setup.get("strands", [])] if cache_key == "wrappedRoutes" else [
                passage["id"] for side in setup["passages"].values() for passage in side]
            for pose in setup["canonicalPoses"].values():
                pose["translation"][1] = -0.06
                pose[cache_key] = {identifier: [[0, 0.04, 0], [0, 0.03, 0], [0, 0.02, 0]] for identifier in identifiers}
    artifact_path = package / "assets/suspension.json"
    artifact_path.write_bytes(cad_source.render_board(artifact))
    return source, package, board, artifact


def test_missing_native_authoring_is_optional(tmp_path):
    source = native_source(tmp_path)
    assert cad_source.load_suspension_authoring(source) is None
    assert cad_source.load_rope_physics_authoring(source) is None


def test_authoring_round_trip_preserves_geometry_lexemes_provenance_and_archive_metadata(tmp_path):
    source = native_source(tmp_path)
    before = archive_members(source)
    authoring = suspension_authoring()
    physics = physics_authoring()
    assert cad_source.embed_authoring(source, suspension=authoring, rope_physics=physics)
    after = archive_members(source)
    assert list(after) == list(before)
    assert {key: value for key, value in after.items() if key != "Document.xml"} == {
        key: value for key, value in before.items() if key != "Document.xml"
    }
    assert cad_source.load_suspension_authoring(source) == authoring
    assert cad_source.load_rope_physics_authoring(source) == physics
    assert "0.000000000,-0.012500000" in cad_source.render_manifest(cad_source.load_suspension_authoring(source))
    assert stat.S_IMODE(source.stat().st_mode) == 0o644
    with zipfile.ZipFile(source) as archive:
        assert archive.comment == b"retained source comment"
    document = ET.fromstring(after["Document.xml"])
    props = document.find("Properties")
    assert int(props.get("Count")) == len(props.findall("Property")) == 2


def test_embedding_is_idempotent_and_none_removes_the_property(tmp_path):
    source = native_source(tmp_path)
    authoring = suspension_authoring()
    physics = physics_authoring()
    cad_source.embed_authoring(source, suspension=authoring, rope_physics=physics)
    first = source.read_bytes()
    assert not cad_source.embed_authoring(source, suspension=authoring, rope_physics=physics)
    assert source.read_bytes() == first
    assert cad_source.embed_authoring(source, suspension=authoring)
    assert cad_source.load_rope_physics_authoring(source) is None
    assert cad_source.load_suspension_authoring(source) == authoring


def test_embedding_to_another_file_preserves_the_source(tmp_path):
    source = native_source(tmp_path)
    before = source.read_bytes()
    destination = tmp_path / "migrated.FCStd"
    cad_source.embed_authoring(source, suspension=suspension_authoring(), destination=destination)
    assert source.read_bytes() == before
    assert cad_source.load_suspension_authoring(destination) == suspension_authoring()
    assert archive_members(destination)["Body.Shape.brp"] == b"exact retained geometry"


def test_embedding_accepts_single_quoted_property_counts_and_keeps_transient_count(tmp_path):
    source = native_source(tmp_path)
    members = archive_members(source)
    members["Document.xml"] = members["Document.xml"].replace(b'Count="0"', b"Count='0'", 1)
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    cad_source.embed_authoring(source, suspension=suspension_authoring(), rope_physics=physics_authoring())
    document = ET.fromstring(archive_members(source)["Document.xml"])
    props = document.find("Properties")
    assert props.get("Count") == "2"
    assert props.get("TransientCount") == "0"


@pytest.mark.parametrize("property_name,loader", [
    ("HangTenSuspensionAuthoring", "load_suspension_authoring"),
    ("HangTenRopePhysics", "load_rope_physics_authoring"),
])
@pytest.mark.parametrize("case", ["wrong_type", "duplicate", "invalid_json", "duplicate_key", "too_large"])
def test_invalid_native_properties_are_rejected(tmp_path, property_name, loader, case):
    text = cad_source.render_manifest(suspension_authoring() if "Suspension" in property_name else physics_authoring())
    kind = "App::PropertyString"
    if case == "wrong_type": kind = "App::PropertyInteger"
    elif case == "invalid_json": text = "{broken"
    elif case == "duplicate_key": text = '{"schemaVersion":1,"schemaVersion":1}'
    elif case == "too_large": text = " " * (1024 * 1024 + 1)
    props = [(property_name, kind, text)]
    if case == "duplicate": props *= 2
    source = native_source(tmp_path, props)
    with pytest.raises(cad_source.ManifestError):
        getattr(cad_source, loader)(source)


@pytest.mark.parametrize("generated", ["modelSHA256", "sourceSHA256", "translation", "cordContactPoints", "wrappedRoutes"])
def test_suspension_source_rejects_generated_values(tmp_path, generated):
    authored = suspension_authoring()
    if generated.endswith("SHA256"):
        authored[generated] = "a" * 64
    else:
        authored["suspension"]["canonicalPoses"]["front"][generated] = [0, 0, 0] if generated == "translation" else {}
    source = native_source(tmp_path, [("HangTenSuspensionAuthoring", "App::PropertyString", cad_source.render_manifest(authored))])
    with pytest.raises(cad_source.ManifestError, match="generated|authoring"):
        cad_source.load_suspension_authoring(source)


def test_suspension_source_rejects_generated_values_outside_canonical_poses(tmp_path):
    authored = suspension_authoring()
    authored["suspension"]["modelSHA256"] = "a" * 64
    source = native_source(tmp_path, [("HangTenSuspensionAuthoring", "App::PropertyString", cad_source.render_manifest(authored))])
    with pytest.raises(cad_source.ManifestError, match="generated"):
        cad_source.load_suspension_authoring(source)


@pytest.mark.parametrize("case", ["empty_profile", "duplicate_profile", "missing_provenance", "missing_rope", "invalid_node", "broken_chain"])
def test_rope_physics_source_rejects_malformed_authored_profiles(tmp_path, case):
    authored = physics_authoring()
    profile = authored["profiles"][0]
    if case == "empty_profile": authored["profiles"] = [{}]
    elif case == "duplicate_profile": authored["profiles"].append(copy.deepcopy(profile))
    elif case == "missing_provenance": profile["boardMass"].pop("provenance")
    elif case == "missing_rope": profile["ropes"] = []
    elif case == "invalid_node": profile["ropes"][0]["nodes"][0]["kind"] = "cachedPoint"
    elif case == "broken_chain": profile["ropes"][0]["edges"][0]["to"] = "absent"
    source = native_source(tmp_path, [("HangTenRopePhysics", "App::PropertyString", cad_source.render_manifest(authored))])
    with pytest.raises(cad_source.ManifestError):
        cad_source.load_rope_physics_authoring(source)


@pytest.mark.parametrize("offset", [[0], [0, 0, 0], [True, 0], [0, float("inf")], "zero", [10**400, 0]])
def test_authored_pose_offsets_require_two_finite_coordinates(tmp_path, offset):
    authored = suspension_authoring()
    authored["suspension"]["canonicalPoses"]["front"]["offsetXZ"] = offset
    source = native_source(tmp_path, [("HangTenSuspensionAuthoring", "App::PropertyString", cad_source.render_manifest(authored))])
    with pytest.raises(cad_source.ManifestError, match="offsetXZ|finite"):
        cad_source.load_suspension_authoring(source)


def test_authored_pose_offsets_reject_precision_that_the_solver_cannot_retain(tmp_path):
    authored = suspension_authoring()
    authored["suspension"]["canonicalPoses"]["front"]["offsetXZ"] = [0.1234567891, 0]
    source = native_source(tmp_path, [("HangTenSuspensionAuthoring", "App::PropertyString", cad_source.render_manifest(authored))])
    with pytest.raises(cad_source.ManifestError, match="nine decimal"):
        cad_source.load_suspension_authoring(source)


def test_materialization_emits_precise_default_reusable_instance_offsets():
    runtime = cad_source.materialize_suspension(suspension_authoring(), {"primary": "a" * 64}, "b" * 64)
    pose = runtime["suspension"]["canonicalPoses"]["back"]
    assert cad_source.render_manifest(pose["translation"]) == "[0.000000000,0.000000000,0.000000000]"


def test_materialization_adds_hashes_and_runtime_offsets_without_mutating_authoring():
    authored = suspension_authoring()
    before = copy.deepcopy(authored)
    runtime = cad_source.materialize_suspension(authored, {"primary": "a" * 64}, "b" * 64)
    assert runtime["sourceSHA256"] == "b" * 64
    assert runtime["modelSHA256"] == "a" * 64
    poses = runtime["suspension"]["canonicalPoses"]
    assert poses["front"]["translation"] == [0, 0, -0.0125]
    assert poses["back"]["translation"] == [0, 0, 0]
    assert "offsetXZ" not in cad_source.render_manifest(runtime)
    assert "0.000000000,0.000000000,-0.012500000" in cad_source.render_manifest(runtime)
    assert authored == before


def test_native_groove_source_hash_is_generated_and_feature_selections_survive():
    authored = suspension_authoring()
    authored["ropeSolver"].update({"sectionPlane": "anchor", "grooveGuides": {
        "byPoseID": {key: {"lead": {"feature": "NativeGroove", "boreFeature": "NativeBore", "exitSign": 1}}
                     for key in ("front", "back")}}})
    authored["ropeSolver"]["terminalsByStrandID"]["lead"]["mouthAxis"] = [0, 0, 1]
    runtime = cad_source.materialize_suspension(authored, {"primary": "a" * 64}, "b" * 64)
    guides = runtime["ropeSolver"]["grooveGuides"]
    assert guides["sourceSHA256"] == "b" * 64
    assert guides["byPoseID"]["front"]["lead"]["feature"] == "NativeGroove"
    assert "sourceSHA256" not in authored["ropeSolver"]["grooveGuides"]


def test_compiled_suspension_merges_routes_and_keeps_solver_out_of_board(tmp_path):
    source, package, board, artifact = compiled_fixture(tmp_path)
    original = copy.deepcopy(board)
    merged = cad_source.merge_suspension_artifact(board, package, source)
    assert merged["presentations"][0]["media"]["suspension"] == artifact["suspension"]
    assert board == original
    assert "ropeSolver" not in cad_source.render_manifest(merged)
    assert "sourceSHA256" not in cad_source.render_manifest(merged)


@pytest.mark.parametrize("case", ["missing", "stale_source", "wrong_model", "changed_provenance", "changed_offset", "missing_routes", "extra_generated_pose_member"])
def test_compiled_suspension_rejects_missing_stale_or_changed_authoring(tmp_path, case):
    source, package, board, artifact = compiled_fixture(tmp_path)
    path = package / "assets/suspension.json"
    if case == "missing": path.unlink()
    else:
        if case == "stale_source": artifact["sourceSHA256"] = "b" * 64
        elif case == "wrong_model": artifact["modelSHA256"] = "b" * 64
        elif case == "changed_provenance": artifact["suspension"]["strands"][0]["provenance"] = "Invented evidence."
        elif case == "changed_offset": artifact["suspension"]["canonicalPoses"]["front"]["translation"][0] = 0.1
        elif case == "missing_routes": artifact["suspension"]["canonicalPoses"]["front"].pop("wrappedRoutes")
        elif case == "extra_generated_pose_member": artifact["suspension"]["canonicalPoses"]["front"]["inferred"] = True
        path.write_bytes(cad_source.render_board(artifact))
    with pytest.raises(cad_source.ManifestError):
        cad_source.merge_suspension_artifact(board, package, source)


@pytest.mark.parametrize("case", ["wrong_identifier", "extra_identifier", "one_point", "two_points", "duplicate_points", "wrong_cache"])
def test_compiled_native_routes_reject_incomplete_topology_and_short_routes(tmp_path, case):
    source, package, board, artifact = compiled_fixture(tmp_path)
    pose = artifact["suspension"]["canonicalPoses"]["front"]
    routes = pose["wrappedRoutes"]
    if case == "wrong_identifier": routes["invented"] = routes.pop("lead")
    elif case == "extra_identifier": routes["invented"] = copy.deepcopy(routes["lead"])
    elif case == "one_point": routes["lead"] = routes["lead"][:1]
    elif case == "two_points": routes["lead"] = routes["lead"][:2]
    elif case == "duplicate_points": routes["lead"][1] = routes["lead"][0]
    elif case == "wrong_cache": pose["cordContactPoints"] = copy.deepcopy(routes)
    (package / "assets/suspension.json").write_bytes(cad_source.render_board(artifact))
    with pytest.raises(cad_source.ManifestError, match="route|cache"):
        cad_source.merge_suspension_artifact(board, package, source)


@pytest.mark.parametrize("case", ["wrong_identifier", "extra_identifier", "wrong_cache"])
def test_compiled_connected_routes_require_exact_authored_passage_ids(tmp_path, case):
    authored = suspension_authoring()
    setup = authored["suspension"]
    setup["type"] = "twoBranchCord"
    setup.pop("strands")
    setup.pop("bodyNodeID")
    setup["passages"] = {"left": [{"id": "mouth-left"}, {"id": "mouth-right"}], "right": []}
    authored["ropeSolver"] = {"sectionPlane": "anchor"}
    source, package, board, artifact = compiled_fixture(tmp_path, authored)
    pose = artifact["suspension"]["canonicalPoses"]["front"]
    routes = pose["cordContactPoints"]
    if case == "wrong_identifier": routes["invented"] = routes.pop("mouth-left")
    elif case == "extra_identifier": routes["invented"] = copy.deepcopy(routes["mouth-left"])
    elif case == "wrong_cache": pose["wrappedRoutes"] = copy.deepcopy(routes)
    (package / "assets/suspension.json").write_bytes(cad_source.render_board(artifact))
    with pytest.raises(cad_source.ManifestError, match="route|cache"):
        cad_source.merge_suspension_artifact(board, package, source)


def test_collection_and_reusable_instance_scaffolds_bind_each_presentation():
    first = suspension_authoring()
    second = copy.deepcopy(first)
    second["presentationID"] = "configured"
    authored = {"schemaVersion": 2, "entries": [{key: value for key, value in entry.items() if key != "schemaVersion"}
                                               for entry in (first, second)]}
    runtime = cad_source.materialize_suspension(authored, {"primary": "a" * 64, "configured": "b" * 64}, "c" * 64)
    assert [entry["modelSHA256"] for entry in runtime["entries"]] == ["a" * 64, "b" * 64]
    assert runtime["sourceSHA256"] == "c" * 64
    instances = {"schemaVersion": 2, "presentationID": "primary", "instanceSuspensions": {
        "left": copy.deepcopy(first["suspension"]), "right": copy.deepcopy(first["suspension"])},
        "ropeSolver": first["ropeSolver"]}
    result = cad_source.materialize_suspension(instances, {"primary": "a" * 64}, "c" * 64)
    assert all(setup["canonicalPoses"]["front"]["translation"] == [0, 0, -0.0125]
               for setup in result["instanceSuspensions"].values())


def test_generate_board_defaults_to_flat_source_package_and_supports_explicit_output_root(tmp_path):
    source, package, board, artifact = compiled_fixture(tmp_path)
    board = {"schemaVersion": 3, "id": "example", **board}
    from set_board_manifest import embed
    embed(source, cad_source.board_to_manifest(board))
    # The manifest change changes the source binding, as it does in a real rebuild.
    artifact["sourceSHA256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    (package / "assets/suspension.json").write_bytes(cad_source.render_board(artifact))
    expected = cad_source.generate_board_json(source)
    alternate = tmp_path / "alternate"
    (alternate / "assets").mkdir(parents=True)
    for path in (package / "assets").iterdir():
        (alternate / "assets" / path.name).write_bytes(path.read_bytes())
    assert cad_source.generate_board_json(source, package_root=alternate) == expected
    assert json.loads(expected)["presentations"][0]["media"]["suspension"]["canonicalPoses"]["front"]["translation"][1] == -0.06
