from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_board_catalog_module


def _evidence_map() -> dict[str, object]:
    return {"sourceIDs": ["source"], "method": "reviewed-human-authored-normalization"}


def _approved_payloads() -> dict[str, dict[str, object]]:
    evidence = _evidence_map()
    return {
        "board": {
            "schemaVersion": 1,
            "id": "approved.board",
            "manufacturer": "Example",
            "name": "Approved Board",
            "productURL": "https://example.com/board",
            "dimensions": "100 mm",
            "aspectRatio": 2.0,
            "presentation": {"assetPath": "assets/presentation.png"},
            "holds": [{"id": "hold-left", "name": "Left hold"}],
        },
        "semantics": {
            "schemaVersion": 1,
            "boardID": "approved.board",
            "semanticHolds": {"outer-holds": {"holdIDs": ["hold-left"]}},
        },
        "artwork": {
            "schemaVersion": 1,
            "boardID": "approved.board",
            "canvasFrame": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            "palette": "sculptedWood",
            "silhouette": {
                "type": "path",
                "commands": [
                    {"command": "move", "to": [0.0, 0.0]},
                    {"command": "line", "to": [1.0, 0.0]},
                    {"command": "close"},
                ],
            },
            "layers": [
                {
                    "id": "top-plane",
                    "role": "topPlane",
                    "frame": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                    "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
                }
            ],
            "holdPieces": [
                {
                    "id": "hold-left-piece",
                    "holdID": "hold-left",
                    "frame": {"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
                    "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
                    "treatment": {"type": "surface"},
                }
            ],
        },
        "evidence": {
            "schemaVersion": 1,
            "boardID": "approved.board",
            "checkedAt": "2026-08-12",
            "sources": [{"id": "source", "title": "Example", "url": "https://example.com/source"}],
            "fieldEvidence": {
                "manufacturer": evidence,
                "name": evidence,
                "productURL": evidence,
                "dimensions": evidence,
                "aspectRatio": evidence,
            },
            "holdEvidence": {"hold-left": evidence},
            "semanticEvidence": {"outer-holds": evidence},
            "artworkEvidence": {
                "silhouette": evidence,
                "layers.top-plane": evidence,
                "holdPieces.hold-left-piece": evidence,
            },
            "assetEvidence": {"assets/presentation.png": evidence},
        },
    }


def _write_approved_package(root: Path) -> Path:
    root.mkdir()
    payloads = _approved_payloads()
    for name, payload in payloads.items():
        root.joinpath(f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
    assets = root / "assets"
    assets.mkdir()
    (assets / "presentation.png").write_bytes(b"presentation")
    return root


def test_load_approved_package_validates_complete_cross_file_contract(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package = module.load_approved_package(_write_approved_package(tmp_path / "package"))

    assert package.board.id == "approved.board"
    assert package.semantics.semantic_holds["outer-holds"] == ("hold-left",)
    assert package.artwork.hold_ids == frozenset({"hold-left"})


def test_approved_package_accepts_a_named_photo_asset_without_treating_it_as_a_fact(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    board_path = root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentation"] = {
        "photoAsset": {"name": "Presentation", "path": "assets/presentation.png"}
    }
    board_path.write_text(json.dumps(board), encoding="utf-8")
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    package = module.load_approved_package(root)

    assert package.board.presentation_asset_path == "assets/presentation.png"


def test_approved_package_allows_no_presentation_asset_or_assets_directory(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    board_path = root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board.pop("presentation")
    board_path.write_text(json.dumps(board), encoding="utf-8")
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["assetEvidence"] = {}
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    (root / "assets" / "presentation.png").unlink()
    (root / "assets").rmdir()

    package = module.load_approved_package(root)

    assert package.board.presentation_asset_path is None
    assert package.evidence.asset_evidence == {}


def test_approved_package_requires_evidence_for_actual_assets_without_presentation(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    board_path = root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board.pop("presentation")
    board_path.write_text(json.dumps(board), encoding="utf-8")
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["assetEvidence"] = {}
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(ValueError, match="assetEvidence keys must equal package assets"):
        module.load_approved_package(root)


@pytest.mark.parametrize("missing", ["evidence.json", "semantics.json", "artwork.json"])
def test_approved_package_requires_each_sidecar(tmp_path: Path, missing: str) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    (root / missing).unlink()

    with pytest.raises(ValueError, match=rf"approved package .*{missing}"):
        module.load_approved_package(root)


def test_approved_package_rejects_uncovered_assets_and_path_escapes(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["assetEvidence"].pop("assets/presentation.png")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(ValueError, match="assetEvidence keys must equal package assets"):
        module.load_approved_package(root)

    evidence["assetEvidence"]["assets/presentation.png"] = _evidence_map()
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    board_path = root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentation"]["assetPath"] = "../outside.png"
    board_path.write_text(json.dumps(board), encoding="utf-8")
    with pytest.raises(ValueError, match="relative path inside the package"):
        module.load_approved_package(root)


def test_approved_package_rejects_invalid_semantics_artwork_and_symlinks(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    semantics_path = root / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    semantics["semanticHolds"]["outer-holds"]["holdIDs"] = ["missing"]
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown physical hold 'missing'"):
        module.load_approved_package(root)

    semantics["semanticHolds"]["outer-holds"]["holdIDs"] = ["hold-left"]
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")
    artwork_path = root / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    artwork["holdPieces"][0]["frame"]["x"] = float("nan")
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")
    with pytest.raises(ValueError, match="must be finite"):
        module.load_approved_package(root)

    artwork["holdPieces"][0]["frame"]["x"] = 0.2
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")
    (root / "assets" / "escaped.png").symlink_to(tmp_path / "outside.png")
    with pytest.raises(ValueError, match="symlink"):
        module.load_approved_package(root)


def test_approved_package_requires_exact_physical_artwork_and_evidence_keys(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    root = _write_approved_package(tmp_path / "package")
    artwork_path = root / "artwork.json"
    artwork = json.loads(artwork_path.read_text(encoding="utf-8"))
    artwork["holdPieces"] = []
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")
    with pytest.raises(ValueError, match="artwork hold IDs must exactly match"):
        module.load_approved_package(root)

    artwork["holdPieces"] = _approved_payloads()["artwork"]["holdPieces"]
    artwork_path.write_text(json.dumps(artwork), encoding="utf-8")
    evidence_path = root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["semanticEvidence"] = {}
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="semanticEvidence keys must equal semantic IDs"):
        module.load_approved_package(root)
