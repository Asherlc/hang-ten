"""Generate settled cord routes from the authoring metadata in a native CAD source.

Run with pinned FreeCAD Python and the pinned cord solver dependencies. The
output is an ignored runtime artifact, merged into board.json during staging.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

# FreeCAD executes this through a workspace-owned wrapper, whose directory is
# unrelated to the tool imports, and does not inherit PYTHONPATH.
sys.path[:0] = [part for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep) if part]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import use_hangboard_packages  # noqa: E402,F401
from hangboard_packages import cad_source  # noqa: E402


def selected_body(document, setup: dict, presentation_id: str, solver: dict):
    """Use the bound native body, or an explicitly selected native collision solid."""
    if name := solver.get("collisionFeature"):
        feature = document.getObject(name)
        if feature is None:
            raise ValueError(f"declared collision feature {name!r} is missing")
        candidates = [feature]
    else:
        candidates = [feature for feature in document.Objects
                      if getattr(feature, "NodeRole", None) == "body"
                      and getattr(feature, "NodeID", None)
                      and ("bodyNodeID" not in setup or feature.NodeID == setup["bodyNodeID"])
                      and (getattr(feature, "HangTenPresentationID", "") or document.HangTenPresentationID)
                      == presentation_id]
    candidates = [feature for feature in candidates if hasattr(feature, "Shape")
                  and feature.Shape.isValid() and len(feature.Shape.Solids) == 1 and feature.Shape.Volume > 0]
    if len(candidates) != 1:
        raise ValueError("cord solving requires one bound positive-volume native solid; "
                         "a renderer shell needs an explicit ropeSolver.collisionFeature")
    return candidates[0]


def _models(board: dict, assets: Path) -> tuple[dict, dict]:
    models, hashes = {}, {}
    for presentation in board["presentations"]:
        media = presentation["media"]
        if media["type"] != "model":
            continue
        paths = [cad_source.safe_member(media[key]) for key in ("assetPath", "descriptorPath")]
        if any(not path.startswith("assets/") or len(Path(path).parts) != 2 for path in paths):
            raise ValueError("compiled model files must be directly inside assets")
        model = json.loads((assets / Path(paths[1]).name).read_text())
        digest = hashlib.sha256((assets / Path(paths[0]).name).read_bytes()).hexdigest()
        if model.get("modelSHA256") != digest:
            raise ValueError("cord solving model descriptor does not match its USDZ")
        models[presentation["id"]] = model
        hashes[presentation["id"]] = digest
    return models, hashes


def compile_suspension(source: Path, assets: Path) -> dict | None:
    authoring = cad_source.load_suspension_authoring(source)
    if authoring is None:
        return None
    import FreeCAD as App
    import trimesh
    from export_rope_collision_solid import native_mesh
    from native_cord_features import extract_native_cord_features
    from native_cord_routes import solve_native_routes
    from solve_threaded_rope import solve_package

    source = Path(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    board = cad_source.load_board(source)
    models, hashes = _models(board, Path(assets))
    output = cad_source.materialize_suspension(authoring, hashes, source_hash)
    document = App.openDocument(str(source.resolve()))
    meshes = {}
    try:
        for entry in output.get("entries", [output]):
            solver = entry.get("ropeSolver", {})
            native_routes = solver.get("method") == "nativeRoutes"
            for equipment_id, setup in entry.get("instanceSuspensions", {"single": entry.get("suspension")}).items():
                feature = selected_body(document, setup, entry["presentationID"], solver)
                if feature.Name not in meshes:
                    meshes[feature.Name] = native_mesh(feature.Shape, canonical=False)
                collision = {"sourcePackage": source.stem, "sourceFeature": feature.Name,
                             "sourceSHA256": source_hash, **meshes[feature.Name]}
                guides = solver.get("grooveGuides", {}).get("byPoseID", {})
                if guides:
                    bindings = [binding for pose in guides.values() for binding in pose.values()]
                    collision["nativeCordFeatures"] = extract_native_cord_features(
                        document, feature.Shape,
                        sorted({binding["feature"] for binding in bindings}),
                        sorted({binding["boreFeature"] for binding in bindings}),
                    )
                mesh = trimesh.Trimesh(vertices=collision["vertices"], faces=collision["triangles"], process=False)
                if setup["type"] == "threadedLoopCord":
                    mesh.metadata["nativeSolid"] = feature.Shape
                local_data = {**entry, "suspension": setup}
                model = models[entry["presentationID"]]
                solved = (solve_native_routes(mesh, local_data, model, source_metadata=collision)
                          if native_routes else solve_package(source.stem, mesh, local_data, model))
                cache_key, result_key = ("wrappedRoutes", "routes") if native_routes else ("cordContactPoints", "contacts")
                for pose_id, result in solved.items():
                    pose = setup["canonicalPoses"][pose_id]
                    pose["translation"][1] = result["height"]
                    pose["translation"] = [cad_source.LexemeFloat(f"{coordinate:.9f}")
                                           for coordinate in pose["translation"]]
                    pose[cache_key] = result[result_key]
                print(f"{source.stem}/{entry['presentationID']}/{equipment_id}: generated {len(solved)} cord poses", flush=True)
    finally:
        App.closeDocument(document.Name)
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise ValueError("cord compilation changed the authored CAD source")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    generated = compile_suspension(args.source, args.assets)
    if generated is not None:
        output = args.output or args.assets / "suspension.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(cad_source.render_board(generated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
