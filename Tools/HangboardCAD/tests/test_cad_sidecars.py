"""Authoring overlays must survive multi-asset and reusable-instance staging."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import use_hangboard_packages  # noqa: E402,F401
from hangboard_packages import cad_source  # noqa: E402


def package(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    for name, digest in (("primary", "a" * 64), ("configured", "b" * 64)):
        (assets / f"{name}.model.json").write_text(json.dumps({"modelSHA256": digest}))
    board = cad_source.loads('''{"presentations":[
      {"id":"pair","media":{"type":"model","descriptorPath":"assets/primary.model.json",
       "instances":[{"equipmentObjectID":"left","translation":[-0.100000000,0.000000000,0.000000000]},
                    {"equipmentObjectID":"right","translation":[0.100000000,0.000000000,0.000000000]}]}},
      {"id":"configured","media":{"type":"model","descriptorPath":"assets/configured.model.json"}}]}''')
    entries = [
        {"presentationID": "pair", "equipmentObjectID": "left", "modelSHA256": "a" * 64, "suspension": {"tag": "left"}},
        {"presentationID": "pair", "equipmentObjectID": "right", "modelSHA256": "a" * 64, "suspension": {"tag": "right"}},
        {"presentationID": "configured", "modelSHA256": "b" * 64, "suspension": {"tag": "configured"}},
    ]
    return board, entries


def merge(tmp_path, board, entries):
    (tmp_path / "suspension.json").write_text(json.dumps({"schemaVersion": 2, "entries": entries}))
    return cad_source.merge_suspension_sidecar(board, tmp_path)


def test_two_instances_and_another_asset_keep_distinct_hash_bound_overlays(tmp_path):
    board, entries = package(tmp_path)
    original = copy.deepcopy(board)
    merged = merge(tmp_path, board, entries)
    instances = merged["presentations"][0]["media"]["instances"]
    assert [item["suspension"]["tag"] for item in instances] == ["left", "right"]
    assert "suspension" not in merged["presentations"][0]["media"]
    assert merged["presentations"][1]["media"]["suspension"]["tag"] == "configured"
    assert board == original, "merging must leave native metadata unmodified"
    rendered = cad_source.render_board(merged).decode()
    assert "-0.100000000" in rendered and "0.000000000" in rendered
    assert "ropeSolver" not in rendered


def test_secondary_asset_cannot_use_the_primary_model_hash(tmp_path):
    board, entries = package(tmp_path)
    entries[-1]["modelSHA256"] = "a" * 64
    with pytest.raises(cad_source.ManifestError, match="does not match"):
        merge(tmp_path, board, entries)


def test_duplicate_instance_overlay_is_rejected(tmp_path):
    board, entries = package(tmp_path)
    entries.append(copy.deepcopy(entries[0]))
    with pytest.raises(cad_source.ManifestError, match="duplicate"):
        merge(tmp_path, board, entries)


@pytest.mark.parametrize("change", [
    {"schemaVersion": 1}, {"presentationID": []}, {"equipmentObjectID": []},
])
def test_invalid_entry_identity_is_a_manifest_error(tmp_path, change):
    board, entries = package(tmp_path)
    entries[0].update(change)
    with pytest.raises(cad_source.ManifestError):
        merge(tmp_path, board, entries)


@pytest.mark.parametrize("points,normal", [
    ([[0, 0, float("nan")]], [1, 0, 0]),
    ([[0, 0]], [1, 0, 0]),
    ([[0, 0, 0]], [0, 0, 0]),
    ([[0, 0, 0]], [True, 0, 0]),
])
def test_native_route_stations_require_finite_vectors_and_a_real_plane(tmp_path, points, normal):
    board, entries = package(tmp_path)
    entries[0]["ropeSolver"] = {"method": "nativeRoutes", "clearance": .0002,
        "terminalsByStrandID": {"lead": {"points": points, "planeNormal": normal}}}
    with pytest.raises(cad_source.ManifestError):
        merge(tmp_path, board, entries)


@pytest.mark.parametrize("terminal_id,kind,points", [
    ("undeclared", "lead", [[0, 0, 0]]),
    ("lead", "lead", [[0, 0, 0], [0, 1, 0]]),
    ("lead", "loop", [[0, 0, 0]]),
])
def test_native_authoring_cannot_hide_a_mismatched_terminal_graph(tmp_path, terminal_id, kind, points):
    board, entries = package(tmp_path)
    entries[0]["suspension"] = {"type": "cadRoutedCord", "strands": [{"id": "lead", "kind": kind}]}
    entries[0]["ropeSolver"] = {"method": "nativeRoutes", "clearance": .0002,
        "terminalsByStrandID": {terminal_id: {"points": points, "planeNormal": [1, 0, 0]}}}
    with pytest.raises(cad_source.ManifestError, match="terminals|stations"):
        merge(tmp_path, board, entries)


def test_matching_native_authoring_graph_merges_without_runtime_solver_settings(tmp_path):
    board, entries = package(tmp_path)
    entries[0]["suspension"] = {"type": "cadRoutedCord", "strands": [{"id": "lead", "kind": "lead"}]}
    entries[0]["ropeSolver"] = {"method": "nativeRoutes", "clearance": .0002, "sectionPlane": "anchor",
        "terminalsByStrandID": {"lead": {"points": [[0, 0, 0]], "planeNormal": [1, 0, 0], "planeAxis": [0, 0, 1]}}}
    merged = merge(tmp_path, board, entries)
    assert merged["presentations"][0]["media"]["instances"][0]["suspension"]["strands"][0]["id"] == "lead"
    assert "ropeSolver" not in cad_source.render_board(merged).decode()


def front_entry_authoring(entries):
    entries[0]["suspension"] = {"type": "cadRoutedCord", "strands": [{"id": "lead", "kind": "lead"}]}
    entries[0]["ropeSolver"] = {"method": "nativeRoutes", "clearance": .0002,
        "sectionPlane": "anchor", "tightening": "coupled3D",
        "terminalsByStrandID": {"lead": {"points": [[0, 0, 0]],
            "planeNormal": [1, 0, 0], "mouthAxis": [0, 0, 1]}}}
    return entries[0]["ropeSolver"]


def test_native_coupled_tightening_is_authoring_only(tmp_path):
    board, entries = package(tmp_path)
    front_entry_authoring(entries)
    merged = merge(tmp_path, board, entries)
    assert merged["presentations"][0]["media"]["instances"][0]["suspension"] == entries[0]["suspension"]
    assert "coupled3D" not in cad_source.render_board(merged).decode()
    assert "ropeSolver" not in cad_source.render_board(merged).decode()


@pytest.mark.parametrize("selector", [None, True, 1, {}, "unknown"])
def test_native_tightening_rejects_unknown_or_non_string_selectors(tmp_path, selector):
    board, entries = package(tmp_path)
    front_entry_authoring(entries)["tightening"] = selector
    with pytest.raises(cad_source.ManifestError, match="tightening"):
        merge(tmp_path, board, entries)


@pytest.mark.parametrize("unsupported", ["fixed-section", "missing-mouth-axis", "loop", "segment"])
def test_native_tightening_rejects_unsupported_entry_topologies(tmp_path, unsupported):
    board, entries = package(tmp_path)
    solver = front_entry_authoring(entries)
    terminal = solver["terminalsByStrandID"]["lead"]
    if unsupported == "fixed-section":
        solver["sectionPlane"] = "fixed"
        del terminal["mouthAxis"]
    elif unsupported == "missing-mouth-axis":
        del terminal["mouthAxis"]
    else:
        entries[0]["suspension"]["strands"][0]["kind"] = unsupported
        terminal["points"].append([0, 1, 0])
        del terminal["mouthAxis"]
    with pytest.raises(cad_source.ManifestError, match="tightening"):
        merge(tmp_path, board, entries)
