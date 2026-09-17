"""Transform-chain-aware USD mesh extent extraction.

USDZ assets in this repo nest each mesh under one or more parent ``Xform``
prims that carry their own ``rotateXYZ``/``translate``/``scale`` ops (for
example a root ``rotateXYZ(-90, 0, 0)`` converting a Blender Z-up, front -Y
source into this repo's Y-up, front +Z model space per
``docs/3D_SUSPENSION_AND_ODR.md``). Reading a mesh's raw ``extent`` without
composing that chain silently mixes up axes whenever the parent transform is
anything other than the identity — most dangerously when the mesh's local
bounding box happens to be symmetric enough (e.g. a square cross-section)
that a naive axis-aligned guess still reproduces the same overall bounds.
This module composes the full chain so every extraction lands in the same
model space the board.json ``canonicalPoses``/descriptor ``modelBounds`` use.
"""
from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Mapping, Sequence


class UsdcatUnavailable(RuntimeError):
    """Raised when a USDZ's payload is a binary .usdc crate and no usdcat
    binary is on PATH to convert it to readable text."""


def read_usda_text(usdz_path: Path) -> str:
    """Return the root layer of *usdz_path* as USDA text.

    Most packages here store an ASCII ``.usda``/``.usd`` payload, readable
    directly. A few store the binary ``.usdc`` crate format instead; those
    require converting through ``usdcat`` (shipped with macOS as part of the
    system AR/USDZ tooling) since this module has no pure-Python crate
    reader.
    """
    with zipfile.ZipFile(usdz_path) as archive:
        names = archive.namelist()
        text_name = next(
            (name for name in names if name.endswith(".usda") or name.endswith(".usd")),
            None,
        )
        if text_name is not None:
            return archive.read(text_name).decode("utf-8", errors="replace")
        crate_name = next(name for name in names if name.endswith(".usdc"))
        usdcat = shutil.which("usdcat")
        if usdcat is None:
            raise UsdcatUnavailable(
                f"{usdz_path} stores a binary {crate_name}; converting it needs "
                "the usdcat binary (shipped with macOS's USDZ tooling), which "
                "is not on PATH"
            )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            crate_path = tmp_path / Path(crate_name).name
            crate_path.write_bytes(archive.read(crate_name))
            usda_path = tmp_path / "converted.usda"
            subprocess.run(
                [usdcat, str(crate_path), "-o", str(usda_path)],
                check=True,
                capture_output=True,
            )
            return usda_path.read_text(encoding="utf-8", errors="replace")

_STR = re.compile(r'"(?:[^"\\]|\\.)*"')
_DEF = re.compile(r'def (Xform|Mesh|Scope) "([^"]+)"')
_ROT = re.compile(r"xformOp:rotateXYZ\s*=\s*\(([^)]*)\)")
_TRA = re.compile(r"xformOp:translate\s*=\s*\(([^)]*)\)")
_SCA = re.compile(r"xformOp:scale\s*=\s*\(([^)]*)\)")
_ORD = re.compile(r"xformOpOrder\s*=\s*\[(.*?)\]")
_EXT = re.compile(r"float3\[\] extent = \[(.*?)\]")

Vec3 = tuple[float, float, float]
Mat4 = list[list[float]]


def _nums(text: str) -> list[float]:
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", text)]


def _identity() -> Mat4:
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def _matmul(a: Mat4, b: Mat4) -> Mat4:
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def _op_matrix(name: str, link: dict) -> Mat4:
    if name == "xformOp:translate":
        matrix = _identity()
        for i in range(3):
            matrix[i][3] = link["translate"][i]
        return matrix
    if name == "xformOp:scale":
        matrix = _identity()
        for i in range(3):
            matrix[i][i] = link["scale"][i]
        return matrix
    if name == "xformOp:rotateXYZ":
        rx, ry, rz = (math.radians(a) for a in link["rotate"])
        mat_x = _identity()
        mat_x[1][1] = math.cos(rx)
        mat_x[1][2] = -math.sin(rx)
        mat_x[2][1] = math.sin(rx)
        mat_x[2][2] = math.cos(rx)
        mat_y = _identity()
        mat_y[0][0] = math.cos(ry)
        mat_y[0][2] = math.sin(ry)
        mat_y[2][0] = -math.sin(ry)
        mat_y[2][2] = math.cos(ry)
        mat_z = _identity()
        mat_z[0][0] = math.cos(rz)
        mat_z[0][1] = -math.sin(rz)
        mat_z[1][0] = math.sin(rz)
        mat_z[1][1] = math.cos(rz)
        return _matmul(_matmul(mat_x, mat_y), mat_z)
    raise ValueError(name)


def _apply(matrix: Mat4, point: Sequence[float]) -> Vec3:
    x, y, z = point
    return (
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3],
    )


def extract_world_extents(
    text: str,
) -> tuple[Mapping[str, object], dict[str, tuple[Vec3, Vec3]], dict[str, list[dict]]]:
    """Return (header, {meshName: (min, max)}, {meshName: xformChain}).

    ``min``/``max`` are the mesh's axis-aligned bounding box corners after
    composing every enclosing ``Xform``'s ops, in the order given by each
    Xform's own ``xformOpOrder`` (defaulting to translate, rotate, scale).
    """
    header_text = text[:1200]
    meters_match = re.search(r"metersPerUnit\s*=\s*(\S+)", header_text)
    up_match = re.search(r'upAxis\s*=\s*"(\w)"', header_text)
    header = {
        "metersPerUnit": float(meters_match.group(1)) if meters_match else None,
        "upAxis": up_match.group(1) if up_match else None,
    }

    raw_extents: dict[str, tuple[Vec3, Vec3]] = {}
    for match in re.finditer(r'def Mesh "([^"]+)"', text):
        extent_match = _EXT.search(text, match.start())
        assert extent_match, match.group(1)
        nums = _nums(extent_match.group(1))
        assert len(nums) == 6, (match.group(1), nums)
        raw_extents[match.group(1)] = ((nums[0], nums[1], nums[2]), (nums[3], nums[4], nums[5]))

    stack: list[list] = []  # [frame, braceDepthAtOpen]
    mesh_chain: dict[str, list[dict]] = {}
    pending: dict | None = None
    brace_depth = 0
    paren_depth = 0
    for line in text.splitlines():
        def_match = _DEF.search(line)
        if def_match:
            pending = {
                "kind": def_match.group(1),
                "name": def_match.group(2),
                "rotate": None,
                "translate": None,
                "scale": None,
                "order": None,
            }
        code = _STR.sub("", line)
        code = code.split("#", 1)[0]
        for char in code:
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "{":
                brace_depth += 1
                if pending is not None and paren_depth == 0:
                    stack.append([pending, brace_depth])
                    if pending["kind"] == "Mesh":
                        mesh_chain[pending["name"]] = [
                            dict(frame) for frame, _ in stack if frame["kind"] == "Xform"
                        ]
                    pending = None
            elif char == "}":
                brace_depth -= 1
                while stack and stack[-1][1] > brace_depth:
                    stack.pop()
        host = pending if pending is not None and paren_depth == 0 else (
            stack[-1][0] if stack else None
        )
        if host is not None:
            rotate_match = _ROT.search(line)
            if rotate_match:
                host["rotate"] = _nums(rotate_match.group(1))
            translate_match = _TRA.search(line)
            if translate_match:
                host["translate"] = _nums(translate_match.group(1))
            scale_match = _SCA.search(line)
            if scale_match:
                host["scale"] = _nums(scale_match.group(1))
            order_match = _ORD.search(line)
            if order_match:
                host["order"] = re.findall(r'"([^"]+)"', order_match.group(1))

    meshes: dict[str, tuple[Vec3, Vec3]] = {}
    for name, (raw_min, raw_max) in raw_extents.items():
        matrix = _identity()
        for link in mesh_chain.get(name, []):
            order = link["order"] or [
                "xformOp:translate",
                "xformOp:rotateXYZ",
                "xformOp:scale",
            ]
            for op in order:
                if op == "xformOp:translate" and link["translate"] is None:
                    continue
                if op == "xformOp:rotateXYZ" and link["rotate"] is None:
                    continue
                if op == "xformOp:scale" and link["scale"] is None:
                    continue
                matrix = _matmul(matrix, _op_matrix(op, link))
        corners = [
            (
                raw_min[0] if i & 1 == 0 else raw_max[0],
                raw_min[1] if i & 2 == 0 else raw_max[1],
                raw_min[2] if i & 4 == 0 else raw_max[2],
            )
            for i in range(8)
        ]
        world_corners = [_apply(matrix, corner) for corner in corners]
        meshes[name] = (
            tuple(min(c[axis] for c in world_corners) for axis in range(3)),
            tuple(max(c[axis] for c in world_corners) for axis in range(3)),
        )
    return header, meshes, mesh_chain
