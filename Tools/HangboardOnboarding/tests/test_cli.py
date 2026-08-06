from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest

from fixtures import make_hangboard
from hangboard_vectorizer import cli as cli_module
from hangboard_vectorizer.cli import main
from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.templates import load_template_document


SVG = "{http://www.w3.org/2000/svg}"

BEASTMAKER_1000_IDS = (
    "jug-left",
    "jug-right",
    "sloper-35-left",
    "sloper-35-right",
    "sloper-center",
    "pocket-top-outer-left",
    "pocket-top-outer-right",
    "pocket-top-left",
    "pocket-top-right",
    "pocket-middle-outer-left",
    "pocket-middle-mid-left",
    "pocket-middle-inner-left",
    "pocket-middle-center",
    "pocket-middle-inner-right",
    "pocket-middle-mid-right",
    "pocket-middle-outer-right",
    "pocket-bottom-outer-left",
    "pocket-bottom-mid-left",
    "pocket-bottom-inner-left",
    "pocket-bottom-inner-right",
    "pocket-bottom-mid-right",
    "pocket-bottom-outer-right",
)


@pytest.fixture(autouse=True)
def _owned_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HANGBOARD_WORKSPACE_ROOT", str(tmp_path))


def test_main_converts_photo_to_svg_manifest_and_preview(tmp_path: Path):
    source = _write_rgb(tmp_path / "board.png", make_hangboard())
    output = tmp_path / "board.svg"
    manifest_path = tmp_path / "board.json"
    preview = tmp_path / "diagnostic.png"

    result = main(
        [
            str(source),
            "--experimental-recess-detection",
            "--output",
            str(output),
            "--manifest",
            str(manifest_path),
            "--preview",
            str(preview),
        ]
    )

    assert result == 0
    root = ET.parse(output).getroot()
    manifest = json.loads(manifest_path.read_text())
    assert len(root.findall(f".//{SVG}path[@class='grip-region']")) == 4
    assert len(manifest["openings"]) == 3
    assert len(manifest["regions"]) == 4
    assert "product" not in manifest
    assert "alignment" not in manifest
    diagnostic = cv2.imread(str(preview))
    assert diagnostic is not None
    assert diagnostic.ndim == 3
    assert {path.name for path in tmp_path.iterdir()} == {
        "board.png",
        "board.svg",
        "board.json",
        "diagnostic.png",
    }


def test_list_products_succeeds_without_conversion_paths(
    capsys: pytest.CaptureFixture[str],
):
    result = main(["--list-products"])

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == "beastmaker-1000\tBeastmaker 1000\n"
    assert captured.err == ""


def test_main_rejects_output_outside_workspace_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write_rgb(tmp_path / "board.png", make_hangboard())
    outside = tmp_path.parent / "escaped.svg"

    result = main(
        [
            str(source),
            "--experimental-recess-detection",
            "--workspace-root",
            str(tmp_path),
            "--output",
            str(outside),
            "--manifest",
            str(tmp_path / "board.json"),
        ]
    )

    assert result == 2
    assert "must stay inside workspace root" in capsys.readouterr().err
    assert not outside.exists()


def test_main_requires_exactly_one_conversion_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    source = _write_rgb(tmp_path / "board.png", make_hangboard())
    common = [
        str(source),
        "--output",
        str(tmp_path / "board.svg"),
        "--manifest",
        str(tmp_path / "board.json"),
    ]

    assert main(common) == 2
    assert "exactly one" in capsys.readouterr().err
    assert (
        main(
            [
                *common,
                "--product",
                "",
                "--experimental-recess-detection",
            ]
        )
        == 2
    )
    assert "exactly one" in capsys.readouterr().err
    assert (
        main(
            [
                *common,
                "--product",
                "beastmaker-1000",
                "--experimental-recess-detection",
            ]
        )
        == 2
    )
    assert "exactly one" in capsys.readouterr().err


def test_main_reports_unknown_product_and_supported_ids(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    source = _write_rgb(tmp_path / "board.png", _semantic_hangboard())

    result = main(
        [
            str(source),
            "--product",
            "missing-board",
            "--output",
            str(tmp_path / "board.svg"),
            "--manifest",
            str(tmp_path / "board.json"),
        ]
    )

    assert result == 2
    error = capsys.readouterr().err
    assert "unknown product" in error
    assert "beastmaker-1000" in error


def test_main_resolves_unknown_product_before_loading_image(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_if_called(source):
        raise AssertionError(f"loader called for {source}")

    monkeypatch.setattr(cli_module, "load_image", fail_if_called)

    result = main(
        [
            "https://example.test/should-not-be-read.png",
            "--product",
            "missing-board",
            "--output",
            str(tmp_path / "board.svg"),
            "--manifest",
            str(tmp_path / "board.json"),
        ]
    )

    assert result == 2
    error = capsys.readouterr().err
    assert "unknown product" in error
    assert "beastmaker-1000" in error


def test_semantic_mode_exports_all_template_regions_with_matching_svg_ids(
    tmp_path: Path,
):
    source = _write_rgb(tmp_path / "board.png", _semantic_hangboard())
    output = tmp_path / "board.svg"
    manifest_path = tmp_path / "board.json"

    result = main(
        [
            str(source),
            "--product",
            "beastmaker-1000",
            "--output",
            str(output),
            "--manifest",
            str(manifest_path),
        ]
    )

    assert result == 0
    root = ET.parse(output).getroot()
    manifest = json.loads(manifest_path.read_text())
    assert root.findall(f".//{SVG}path[@class='board-silhouette']") == []
    (product_render,) = root.findall(f".//{SVG}image[@class='product-render']")
    assert product_render.attrib["href"].startswith("data:image/png;base64,")
    svg_regions = root.findall(f".//{SVG}path[@class='grip-region']")
    root_children = list(root)
    assert root_children.index(product_render) < min(
        root_children.index(region) for region in svg_regions
    )
    svg_region_ids = tuple(element.attrib["id"] for element in svg_regions)
    manifest_region_ids = tuple(region["id"] for region in manifest["regions"])
    assert len(svg_regions) == 22
    assert all("C" in item.attrib["d"] or "Q" in item.attrib["d"] for item in svg_regions)
    assert Counter(item.attrib["data-type"] for item in svg_regions) == {
        "pocket": 17,
        "sloper": 3,
        "jug": 2,
    }
    assert root.findall(f".//{SVG}path[@class='opening']") == []
    assert manifest["openings"] == []
    assert len(manifest["regions"]) == 22
    assert svg_region_ids == manifest_region_ids == BEASTMAKER_1000_IDS
    assert svg_region_ids.count("sloper-center") == 1
    assert {"sloper-20-left", "sloper-20-right"}.isdisjoint(svg_region_ids)
    assert all(region["openingId"] is None for region in manifest["regions"])
    assert all(region["source"] == "template" for region in manifest["regions"])
    assert manifest["product"] == {
        "id": "beastmaker-1000",
        "displayName": "Beastmaker 1000",
        "templateSchemaVersion": 1,
    }
    assert manifest["alignment"]["confidence"] == "high"


@pytest.mark.parametrize(
    "operation",
    [
        {"rename": {"pocket-top-left": "warmup-pocket"}},
        {"disable": ["pocket-top-left"]},
        {
            "split": {
                "sloper-center": [
                    {"id": "sloper-20-left", "xRange": [0.0, 0.5]},
                    {"id": "sloper-20-right", "xRange": [0.5, 1.0]},
                ]
            }
        },
        {
            "merge": [
                {
                    "ids": ["pocket-top-left", "pocket-top-right"],
                    "id": "top-pair",
                }
            ]
        },
    ],
    ids=("rename", "disable", "split-center", "merge"),
)
def test_beastmaker_topology_breaking_overrides_publish_no_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    operation: dict[str, object],
):
    source = _write_rgb(tmp_path / "board.png", _semantic_hangboard())
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"version": 1, **operation}))
    output = tmp_path / "board.svg"
    manifest = tmp_path / "board.json"

    result = main(
        [
            str(source),
            "--product",
            "beastmaker-1000",
            "--overrides",
            str(overrides),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
        ]
    )

    assert result == 2
    assert "canonical" in capsys.readouterr().err
    assert not output.exists()
    assert not manifest.exists()


def test_asset_backed_split_without_native_geometry_publishes_no_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    source = _write_rgb(tmp_path / "board.png", _semantic_hangboard())
    overrides = tmp_path / "overrides.json"
    overrides.write_text(
        json.dumps(
            {
                "version": 1,
                "split": {
                    "pocket-top-left": [
                        {"id": "pocket-left-half", "xRange": [0.0, 0.5]},
                        {"id": "pocket-right-half", "xRange": [0.5, 1.0]},
                    ]
                },
            }
        )
    )
    output = tmp_path / "board.svg"
    manifest = tmp_path / "board.json"
    preview = tmp_path / "preview.png"
    product = replace(
        cli_module.get_product_template("beastmaker-1000"),
        product_id="generic-asset-board",
    )
    monkeypatch.setattr(cli_module, "get_product_template", lambda _: product)

    result = main(
        [
            str(source),
            "--product",
            "generic-asset-board",
            "--overrides",
            str(overrides),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--preview",
            str(preview),
        ]
    )

    assert result == 2
    assert "native display geometry" in capsys.readouterr().err
    assert not output.exists()
    assert not manifest.exists()
    assert not preview.exists()


def test_main_does_not_publish_outputs_when_svg_rendering_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    source = _write_rgb(tmp_path / "board.png", _semantic_hangboard())
    output = tmp_path / "board.svg"
    manifest = tmp_path / "board.json"

    def fail_render(*args, **kwargs):
        raise ConversionError("render failed")

    monkeypatch.setattr(cli_module, "render_svg", fail_render)

    result = main(
        [
            str(source),
            "--product",
            "beastmaker-1000",
            "--output",
            str(output),
            "--manifest",
            str(manifest),
        ]
    )

    assert result == 2
    assert capsys.readouterr().err == "error: render failed\n"
    assert not output.exists()
    assert not manifest.exists()


@pytest.mark.parametrize("region_type", ["pocket", "edge", "rail", "jug", "sloper"])
def test_semantic_template_schema_accepts_every_supported_grip_type(region_type: str):
    """Dropping a supported semantic type would break product-template onboarding."""
    template = load_template_document(
        {
            "schemaVersion": 1,
            "productId": "schema-acceptance-board",
            "displayName": "Schema acceptance board",
            "canonicalViewBox": [0, 0, 100, 25],
            "outline": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]],
            "regions": [
                {
                    "id": "test-region",
                    "type": region_type,
                    "label": "Test region",
                    "polygons": [
                        [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
                    ],
                }
            ],
        }
    )

    assert template.regions[0].type == region_type


def test_semantic_mode_rejects_large_aspect_error_unless_explicitly_allowed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    source = _write_rgb(tmp_path / "board.png", make_hangboard())
    output = tmp_path / "board.svg"
    manifest = tmp_path / "board.json"
    arguments = [
        str(source),
        "--product",
        "beastmaker-1000",
        "--output",
        str(output),
        "--manifest",
        str(manifest),
    ]

    assert main(arguments) == 2
    assert "aspect ratio" in capsys.readouterr().err
    assert not output.exists()
    assert not manifest.exists()

    preview = tmp_path / "diagnostic.png"
    preview_warnings: list[tuple[str, ...]] = []
    real_render_preview = cli_module.render_preview

    def record_preview_warnings(board, openings, regions):
        preview_warnings.append(board.warnings)
        return real_render_preview(board, openings, regions)

    monkeypatch.setattr(cli_module, "render_preview", record_preview_warnings)
    assert (
        main(
            [
                *arguments,
                "--allow-low-confidence",
                "--preview",
                str(preview),
            ]
        )
        == 0
    )
    document = json.loads(manifest.read_text())
    assert document["alignment"]["confidence"] == "low"
    assert "low alignment confidence" in document["warnings"]
    assert preview_warnings == [("low alignment confidence",)]
    assert cv2.imread(str(preview)) is not None


@pytest.mark.parametrize(
    ("case", "arguments"),
    [
        ("missing input", lambda root: [str(root / "missing.png")]),
        ("uniform image", lambda root: [str(root / "uniform.png")]),
        (
            "malformed override",
            lambda root: [
                str(root / "board.png"),
                "--overrides",
                str(root / "bad.json"),
            ],
        ),
        (
            "unwritable output parent",
            lambda root: [
                str(root / "board.png"),
                "--output",
                str(root / "not-a-dir" / "board.svg"),
            ],
        ),
        (
            "out-of-range threshold",
            lambda root: [str(root / "board.png"), "--min-area-ratio", "1.1"],
        ),
    ],
)
def test_main_reports_conversion_errors_without_partial_text_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: str,
    arguments,
):
    _write_rgb(tmp_path / "board.png", make_hangboard())
    _write_rgb(tmp_path / "uniform.png", np.full((100, 100, 3), 255, dtype=np.uint8))
    (tmp_path / "bad.json").write_text("{not-json")
    (tmp_path / "not-a-dir").write_text("file blocks directory creation")
    output = tmp_path / "result.svg"
    manifest = tmp_path / "result.json"

    result = main(
        [
            "--experimental-recess-detection",
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            *arguments(tmp_path),
        ]
    )

    assert result == 2, case
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert "Traceback" not in captured.err
    assert not output.exists()
    assert not manifest.exists()


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--width", "0"),
        ("--width", "nan"),
        ("--background-tolerance", "-1"),
        ("--contrast-threshold", "-1"),
        ("--min-area-ratio", "-0.1"),
        ("--rail-aspect-ratio", "0"),
        ("--rail-width-ratio", "1.1"),
        ("--row-tolerance-ratio", "1.1"),
    ],
)
def test_main_rejects_invalid_numeric_options(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flag: str,
    value: str,
):
    source = _write_rgb(tmp_path / "board.png", make_hangboard())
    output = tmp_path / "result.svg"
    manifest = tmp_path / "result.json"

    result = main(
        [
            str(source),
            "--experimental-recess-detection",
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            flag,
            value,
        ]
    )

    assert result == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert not output.exists()
    assert not manifest.exists()


@pytest.mark.parametrize("preexisting", [False, True])
@pytest.mark.parametrize("semantic", [False, True])
def test_main_rolls_back_every_destination_when_publication_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    preexisting: bool,
    semantic: bool,
):
    source = _write_rgb(
        tmp_path / "board.png",
        _semantic_hangboard() if semantic else make_hangboard(),
    )
    output = tmp_path / "board.svg"
    manifest = tmp_path / "board.json"
    preview = tmp_path / "diagnostic.png"
    original_contents = {
        output: b"original svg",
        manifest: b"original manifest",
        preview: b"original preview",
    }
    if preexisting:
        for path, content in original_contents.items():
            path.write_bytes(content)

    original_replace = Path.replace

    def fail_manifest_publication(self: Path, target: Path) -> Path:
        target = Path(target)
        is_staged_manifest = (
            target == manifest
            and self.name.startswith(f".{manifest.name}.")
            and self.suffix == ".tmp"
        )
        if is_staged_manifest:
            raise OSError("simulated manifest publication failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_manifest_publication)

    result = main(
        [
            str(source),
            *(
                ["--product", "beastmaker-1000"]
                if semantic
                else ["--experimental-recess-detection"]
            ),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--preview",
            str(preview),
        ]
    )

    assert result == 2
    assert "simulated manifest publication failure" in capsys.readouterr().err
    for path, content in original_contents.items():
        if preexisting:
            assert path.read_bytes() == content
        else:
            assert not path.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        [
            "board.png",
            *([path.name for path in original_contents] if preexisting else []),
        ]
    )


@pytest.mark.parametrize(
    ("output", "manifest", "preview"),
    [
        ("same.out", "same.out", None),
        ("same.out", "manifest.json", "same.out"),
        ("board.svg", "same.out", "same.out"),
        ("nested/../same.out", "same.out", None),
    ],
)
def test_main_rejects_exact_and_normalized_destination_collisions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    output: str,
    manifest: str,
    preview: str | None,
):
    output_path = tmp_path / output
    manifest_path = tmp_path / manifest
    preview_path = tmp_path / preview if preview is not None else None
    arguments = [
        str(tmp_path / "missing.png"),
        "--experimental-recess-detection",
        "--output",
        str(output_path),
        "--manifest",
        str(manifest_path),
    ]
    if preview_path is not None:
        arguments.extend(("--preview", str(preview_path)))

    result = main(arguments)

    assert result == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("error: ")
    assert "distinct" in captured.err
    for path in (output_path, manifest_path, preview_path):
        if path is not None:
            assert not path.resolve().exists()


def _write_rgb(path: Path, rgb: np.ndarray) -> Path:
    assert cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return path


def _semantic_hangboard() -> np.ndarray:
    image = np.full((359, 1100, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (50, 50), (1050, 309), (196, 148, 94), thickness=-1)
    return image
