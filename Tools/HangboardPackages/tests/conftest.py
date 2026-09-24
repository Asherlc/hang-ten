from __future__ import annotations

import io
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src"


def load_board_catalog_module() -> ModuleType:
    """Return the real ``hangboard_packages.board_catalog`` module."""
    if str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))
    from hangboard_packages import board_catalog

    return board_catalog


def _encode_png(
    width: int, height: int, *, color: tuple[int, int, int] = (255, 255, 255)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _encode_transparent_png(width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), color=(255, 255, 255, 255))
    image.putpixel((0, 0), (255, 255, 255, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


PRIMARY_PNG_WIDTH = 40
PRIMARY_PNG_HEIGHT = 20
OPAQUE_PRIMARY_PNG_BYTES = _encode_png(PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT)
TRANSPARENT_PRIMARY_PNG_BYTES = _encode_transparent_png(
    PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT
)
PRIMARY_PNG_BYTES = TRANSPARENT_PRIMARY_PNG_BYTES
SECONDARY_PNG_BYTES = _encode_png(
    PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT, color=(0, 0, 0)
)
ALTERNATE_PRIMARY_PNG_BYTES = _encode_transparent_png(
    PRIMARY_PNG_WIDTH + 2, PRIMARY_PNG_HEIGHT + 2
)


def board_document(
    board_id: str = "fixture.board",
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, Any]:
    return {
        "schemaVersion": 3,
        "id": board_id,
        "revisionID": "2026-09-contact-first",
        "manufacturer": manufacturer,
        "name": name,
        "subtitle": "A physical fixture board.",
        "productURL": f"https://example.com/{board_id}",
        "dimensions": "20 x 10 cm",
        "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
        "equipmentObjects": [{"id": "primary"}],
        "presentations": [
            {
                "id": "primary",
                "name": "Primary",
                "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
                "isDefault": True,
                "derivation": {"type": "original"},
                "media": {
                    "type": "raster",
                    "assetPath": "assets/primary.png",
                    "contactGeometry": {
                        "hold-left": [
                            {
                                "frame": {
                                    "x": 0.1,
                                    "y": 0.1,
                                    "width": 0.1,
                                    "height": 0.4,
                                },
                                "shape": {
                                    "type": "roundedRect",
                                    "cornerRadiusFraction": 0.2,
                                },
                            }
                        ]
                    },
                },
            }
        ],
        "contacts": [
            {
                "id": "hold-left",
                "equipmentObjectID": "primary",
                "name": "Left hold",
                "kind": "jug",
                "gripTypes": [],
            }
        ],
    }


def multi_presentation_board_document(
    board_id: str = "fixture.board",
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, Any]:
    """Return a fixture with one hold on each declared presentation."""
    document = board_document(board_id, manufacturer=manufacturer, name=name)
    document["presentations"] = [
        {
            "id": "front",
            "name": "Front",
            "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
            "isDefault": True,
            "derivation": {"type": "original"},
            "media": {
                "type": "raster",
                "assetPath": "assets/primary.png",
                "contactGeometry": {
                    "hold-left": document["presentations"][0]["media"][
                        "contactGeometry"
                    ]["hold-left"]
                },
            },
        },
        {
            "id": "back",
            "name": "Back",
            "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
            "isDefault": False,
            "derivation": {"type": "original"},
            "media": {
                "type": "raster",
                "assetPath": "assets/back.png",
                "contactGeometry": {
                    "hold-right": [
                        {
                            "frame": {
                                "x": 0.8,
                                "y": 0.1,
                                "width": 0.1,
                                "height": 0.4,
                            },
                            "shape": {
                                "type": "roundedRect",
                                "cornerRadiusFraction": 0.2,
                            },
                        }
                    ]
                },
            },
        },
    ]
    document["contacts"].append(
        {
            "id": "hold-right",
            "equipmentObjectID": "primary",
            "name": "Right hold",
            "kind": "jug",
            "gripTypes": [],
        }
    )
    return document


def write_board_package(
    root: Path,
    *,
    board_id: str = "fixture.board",
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    """Write a complete direct-child board package at *root* and return it."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    document = board_document(board_id, manufacturer=manufacturer, name=name)
    (root / "board.json").write_text(
        __import__("json").dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    return root


def write_multi_presentation_board_package(
    root: Path,
    *,
    board_id: str = "fixture.board",
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    """Write a complete package with its declared presentation assets."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    (assets / "back.png").write_bytes(SECONDARY_PNG_BYTES)
    document = multi_presentation_board_document(
        board_id, manufacturer=manufacturer, name=name
    )
    (root / "board.json").write_text(
        __import__("json").dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    return root


def write_primary_only_draft(root: Path) -> Path:
    """Write a primary-only migration draft at *root* and return it."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    return root


def write_cad_source(package_root: Path, *, remove_board_json: bool = True) -> Path:
    """Turn a hand-authored fixture package into a CAD-backed one.

    Embeds the package's ``board.json`` (minus ``id``) as the
    ``HangTenBoardManifest`` of a minimal FCStd that satisfies the archive
    contract, then removes ``board.json``: a CAD-backed package's board.json is
    generated from its FCStd. Returns the FCStd path.
    """
    import xml.etree.ElementTree as ET
    import zipfile

    if str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))
    from hangboard_packages import cad_source

    package_root = Path(package_root)
    board_path = package_root / "board.json"
    board = cad_source.loads(board_path.read_text(encoding="utf-8"))
    manifest = cad_source.render_manifest(cad_source.board_to_manifest(board))
    document = ET.Element("Document", SchemaVersion="4", FileVersion="1")
    properties = ET.SubElement(document, "Properties", Count="2", TransientCount="0")
    for name, value in (("HangTenBoardID", board["id"]), ("HangTenBoardManifest", manifest)):
        prop = ET.SubElement(properties, "Property", name=name, type="App::PropertyString")
        ET.SubElement(prop, "String", value=value)
    objects = ET.SubElement(document, "Objects", Count="1")
    ET.SubElement(objects, "Object", type="PartDesign::Body", name="Body")
    data = ET.SubElement(document, "ObjectData", Count="1")
    ET.SubElement(data, "Object", name="Body")
    source = cad_source.package_source_path(package_root)
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Document.xml", ET.tostring(document, xml_declaration=True, encoding="utf-8"))
        archive.writestr("Body.Shape.brp", b"fixture geometry")
    if remove_board_json:
        board_path.unlink()
    return source


def package_board_text(package_root: Path) -> str:
    """A package's board.json text, generated from the FCStd for a CAD-backed
    package (whose board.json is never on disk), read from disk otherwise."""
    return load_board_catalog_module().read_board_json(Path(package_root)).decode("utf-8")


def package_roots(hangboards_root: Path) -> list[Path]:
    """Every board package directory: hand-authored (board.json) or CAD-backed."""
    board_catalog = load_board_catalog_module()
    return sorted(
        path
        for path in Path(hangboards_root).iterdir()
        if path.is_dir()
        and ((path / "board.json").is_file() or board_catalog.cad_source.is_cad_package(path))
    )
