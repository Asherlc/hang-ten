"""Small genuine archives for metadata consumer tests; no FreeCAD runtime needed."""
import copy
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import quoteattr
import zipfile

from hangboard_packages import cad_source


def canonical_pose() -> dict:
    return {"rotation": [0, 0, 0, 1],
            "camera": {"viewDirection": [0, 0, -1], "fitPadding": .1}}


def source_pose_fields(runtime: dict) -> dict:
    result = copy.deepcopy(runtime)
    for pose in result.get("canonicalPoses", {}).values():
        for generated in ("translation", "wrappedRoutes", "cordContactPoints"):
            pose.pop(generated, None)
    return result


def write_native_authoring(package_root: Path, board: dict, authoring: dict) -> Path:
    source = package_root.parent / f"{package_root.name}.FCStd"
    manifest = {"schemaVersion": 3, **board}
    manifest.pop("id", None)
    text = cad_source.render_manifest(manifest)
    document = f'''<Document>
  <Properties Count="2">
    <Property name="HangTenBoardID" type="App::PropertyString"><String value={quoteattr(board.get("id", "fixture.board"))}/></Property>
    <Property name="HangTenBoardManifest" type="App::PropertyString"><String value={quoteattr(text)}/></Property>
  </Properties>
  <Objects Count="1"><Object type="Part::Feature" name="Solid"/></Objects>
  <ObjectData Count="1"><Object name="Solid"><Properties Count="0"/></Object></ObjectData>
</Document>'''
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("Document.xml", document)
        archive.writestr("Solid.brp", b"retained geometry fixture")
    cad_source.embed_authoring(source, suspension=authoring)
    return source


def merge_native_artifact(package_root: Path, board: dict, authored: dict,
                          requested_hashes=None) -> dict:
    """Exercise real native property, descriptor and artifact binding together."""
    source = write_native_authoring(package_root, board, authored)
    hashes = {
        presentation["id"]: json.loads(
            (package_root / presentation["media"]["descriptorPath"]).read_text()
        )["modelSHA256"]
        for presentation in board["presentations"]
    }
    artifact = cad_source.materialize_suspension(
        authored, hashes, hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    for entry in artifact.get("entries", [artifact]):
        setups = entry.get("instanceSuspensions", {"": entry.get("suspension")})
        for setup in setups.values():
            if not isinstance(setup, dict):
                continue
            for pose in setup.get("canonicalPoses", {}).values():
                if setup["type"] == "cadRoutedCord":
                    pose["wrappedRoutes"] = {
                        strand["id"]: [[0, 0, 0], [0, .01, 0], [0, .02, 0]]
                        for strand in setup["strands"]
                    }
                else:
                    pose["cordContactPoints"] = {
                        passage["id"]: [passage["pointInModel"]]
                        for passages in setup["passages"].values() for passage in passages
                    }
                    if "meshWrap" in setup:
                        pose["wrappedRoutes"] = {
                            branch["id"]: [[0, 0, 0], [0, .01, 0], [0, .02, 0]]
                            for branch in setup["branches"]
                        }
    if requested_hashes is not None:
        if "entries" in artifact:
            for entry, requested in zip(artifact["entries"], requested_hashes):
                entry["modelSHA256"] = requested
        else:
            artifact["modelSHA256"] = requested_hashes[0]
    (package_root / "assets/suspension.json").write_text(json.dumps(artifact))
    return cad_source.merge_suspension_artifact(board, package_root, source)


def authored_runtime_setup(runtime: dict) -> dict:
    """Convert a synthetic solver fixture's zero-height poses to authored input."""
    authored = copy.deepcopy(runtime)
    for pose in authored["suspension"].get("canonicalPoses", {}).values():
        if "translation" in pose:
            x, _, z = pose.pop("translation")
            pose["offsetXZ"] = [x, z]
    return authored
