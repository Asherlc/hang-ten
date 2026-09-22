"""Round-trip tests for the direct USDZ writer (host interpreter, no FreeCAD)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usdz_writer import Material, Mesh, read_usdz, write_usdz  # noqa: E402

TRIANGLE = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 20.0, 0.0))
# An asymmetric fixture: any scale, axis swap, or reflection error changes it.
ASYMMETRIC = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 20.0, 0.0), (0.0, 0.0, 30.0))
ASYMMETRIC_TRIANGLES = ((0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2))


def _mesh(node_id="body", points=ASYMMETRIC, triangles=ASYMMETRIC_TRIANGLES, material=None):
    return Mesh(
        node_id=node_id,
        points_mm=points,
        triangles=triangles,
        material=material or Material(name="wood"),
    )


def test_single_triangle_round_trip(tmp_path):
    target = tmp_path / "model.usdz"
    write_usdz(target, [_mesh(points=TRIANGLE, triangles=((0, 1, 2),))])
    result = read_usdz(target)
    assert result["up_axis"] == "Y"
    assert result["meters_per_unit"] == 1.0
    assert result["defaultPrim"] == "root"
    assert list(result["nodes"]) == ["body"]
    node = result["nodes"]["body"]
    assert node["path"] == "/root/body"
    assert node["triangles"] == [(0, 1, 2)]
    assert node["material"] == "wood"
    assert len(node["points_m"]) == 3
    for actual, expected in zip(
        node["points_m"], [(0.0, 0.0, 0.0), (0.01, 0.0, 0.0), (0.0, 0.0, -0.02)]
    ):
        assert actual == pytest.approx(expected, rel=0, abs=1e-9)


def test_basis_conversion_is_exact_and_orientation_preserving(tmp_path):
    target = tmp_path / "model.usdz"
    write_usdz(target, [_mesh()])
    points = read_usdz(target)["nodes"]["body"]["points_m"]
    # native +Z (up) becomes runtime +Y
    assert points[3] == pytest.approx((0.0, 0.03, 0.0), rel=0, abs=1e-9)
    # native -Y (front) becomes runtime +Z
    assert points[2] == pytest.approx((0.0, 0.0, -0.02), rel=0, abs=1e-9)
    # native +X stays runtime +X at 1/1000 scale
    assert points[1] == pytest.approx((0.01, 0.0, 0.0), rel=0, abs=1e-9)


def test_triangle_order_is_preserved(tmp_path):
    target = tmp_path / "model.usdz"
    write_usdz(target, [_mesh()])
    assert read_usdz(target)["nodes"]["body"]["triangles"] == list(ASYMMETRIC_TRIANGLES)


def test_materials_bind_to_the_right_nodes(tmp_path):
    target = tmp_path / "model.usdz"
    write_usdz(
        target,
        [
            _mesh("alpha", points=TRIANGLE, triangles=((0, 1, 2),), material=Material(name="first")),
            _mesh("beta", material=Material(name="second", base_color=(0.1, 0.2, 0.3))),
        ],
    )
    result = read_usdz(target)
    assert result["nodes"]["alpha"]["material"] == "first"
    assert result["nodes"]["beta"]["material"] == "second"
    assert sorted(result["materials"]) == ["first", "second"]
    assert result["materials"]["second"]["shaderId"] == "UsdPreviewSurface"
    assert result["materials"]["second"]["diffuseColor"] == pytest.approx((0.1, 0.2, 0.3), rel=0, abs=1e-6)


def test_embedded_texture_is_packaged_and_connected(tmp_path):
    from PIL import Image

    texture = tmp_path / "grain.png"
    Image.new("RGB", (4, 4), (120, 90, 60)).save(texture)
    target = tmp_path / "model.usdz"
    material = Material(
        name="wood",
        texture_archive_path="textures/grain.png",
        texture_source=texture,
    )
    write_usdz(target, [_mesh(material=material)])
    result = read_usdz(target)
    material = result["materials"]["wood"]
    assert material["diffuseColor"] == "<Image_Texture>"
    # The texture must be a real member of the package and the recorded asset
    # reference must resolve inside it.
    assert material["diffuseColorAssetResolves"] is True
    assert material["diffuseColorAsset"] in result["members"]


def test_normals_and_uvs_round_trip(tmp_path):
    target = tmp_path / "model.usdz"
    mesh = Mesh(
        node_id="body",
        points_mm=ASYMMETRIC,
        triangles=ASYMMETRIC_TRIANGLES,
        material=Material(name="wood"),
        normals_mm=((0.0, 0.0, -1.0),) * 4,
        uvs=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)),
    )
    write_usdz(target, [mesh])
    node = read_usdz(target)["nodes"]["body"]
    assert node["normals"] == 4
    assert node["uvs"] == 4


def test_duplicate_node_ids_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate node id"):
        write_usdz(tmp_path / "model.usdz", [_mesh("body"), _mesh("body")])


def test_out_of_range_triangle_index_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="out-of-range triangle index"):
        write_usdz(
            tmp_path / "model.usdz",
            [_mesh(points=TRIANGLE, triangles=((0, 1, 3),))],
        )


def test_repeat_write_is_reproducible(tmp_path):
    first = tmp_path / "one.usdz"
    second = tmp_path / "two.usdz"
    write_usdz(first, [_mesh()])
    write_usdz(second, [_mesh()])
    assert first.read_bytes() == second.read_bytes()


def test_failed_write_leaves_no_partial_file(tmp_path):
    target = tmp_path / "model.usdz"
    with pytest.raises(ValueError):
        write_usdz(target, [_mesh("body"), _mesh("body")])
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
