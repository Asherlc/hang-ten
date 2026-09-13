"""Focused tests for lossless text-USDA to binary-USDC USDZ optimization."""

from __future__ import annotations

import contextlib
import hashlib
import io
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import optimize_usdz as optimizer
from optimize_usdz import optimize_usdz
import compile_model_package as compiler


USDA = """#usda 1.0
(
    defaultPrim = "Board"
    upAxis = "Y"
)

def Xform "Board"
{
    custom string nodeLabel = "Board Root"
    string[] authoredNames = ["Body", "Hold"]
    def Mesh "Hold"
    {
        custom string logicalHoldID = "left"
        int[] faceVertexCounts = [3]
        int[] faceVertexIndices = [0, 1, 2]
        point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (0, 1)] (
            interpolation = "vertex"
        )
        rel material:binding = </Board/Materials/Wood>
    }
    def Scope "Materials"
    {
        def Material "Wood"
        {
            custom asset sourceTexture = @textures/wood.png@
            token purpose = "full"
        }
    }
}
"""


def _run_usdcat(*arguments: str) -> None:
    result = subprocess.run(
        ["/usr/bin/usdcat", *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _write_fixture(path: Path, *, layer_name: str = "scene.usda") -> tuple[bytes, bytes]:
    texture = b"PNG bytes are opaque to this serialization test\x00\x01"
    note = b"unchanged non-USD member"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("notes.bin", note)
        archive.writestr("textures/wood.png", texture)
        archive.writestr(layer_name, USDA.encode("utf-8"))
    return texture, note


class OptimizeUSDZTests(unittest.TestCase):
    def test_optimizer_emits_deterministic_binary_layer_and_preserves_usd_semantics(self) -> None:
        with _workspace("optimizer-fixture-") as raw_path:
            tmp_path = Path(raw_path)
            source = tmp_path / "source.usdz"
            first = tmp_path / "optimized-1.usdz"
            second = tmp_path / "optimized-2.usdz"
            texture, note = _write_fixture(source)
            source_bytes = source.read_bytes()

            optimize_usdz(source, first)
            optimize_usdz(source, second)

            self.assertEqual(source.read_bytes(), source_bytes)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertNotEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(source_bytes).hexdigest(),
            )

            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.namelist(), ["scene.usdc", "notes.bin", "textures/wood.png"]
                )
                self.assertEqual(archive.read("notes.bin"), note)
                self.assertEqual(archive.read("textures/wood.png"), texture)
                binary_layer = archive.read("scene.usdc")
                self.assertTrue(binary_layer.startswith(b"PXR-USDC"))
                self.assertTrue(
                    all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist())
                )
                self.assertTrue(
                    all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
                )
                self.assertTrue(
                    all(
                        (
                            info.header_offset
                            + 30
                            + len(info.filename.encode("utf-8"))
                            + len(info.extra)
                        )
                        % 64
                        == 0
                        for info in archive.infolist()
                    )
                )
                extracted_binary = tmp_path / "scene.usdc"
                extracted_binary.write_bytes(binary_layer)

            source_normalized = tmp_path / "source-normalized.usd"
            optimized_normalized = tmp_path / "optimized-normalized.usd"
            source_layer = tmp_path / "scene.usda"
            source_layer.write_text(USDA, encoding="utf-8")
            _run_usdcat("--usdFormat", "usda", "-o", str(source_normalized), str(source_layer))
            _run_usdcat("--usdFormat", "usda", "-o", str(optimized_normalized), str(extracted_binary))
            self.assertEqual(optimized_normalized.read_bytes(), source_normalized.read_bytes())
            _run_usdcat("--loadOnly", str(first))


    def test_optimizer_rejects_unsafe_archive_member_paths(self) -> None:
        with _workspace("unsafe-fixture-") as raw_path:
            tmp_path = Path(raw_path)
            source = tmp_path / "unsafe.usdz"
            output = tmp_path / "optimized.usdz"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../scene.usda", USDA)

            with self.assertRaisesRegex(ValueError, "unsafe member paths"):
                optimize_usdz(source, output)

    def test_optimizer_rejects_noncanonical_member_aliases(self) -> None:
        with _workspace("alias-fixture-") as raw_path:
            tmp_path = Path(raw_path)
            source = tmp_path / "alias.usdz"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("a//scene.usda", USDA)

            with self.assertRaisesRegex(ValueError, "unsafe member paths"):
                optimize_usdz(source, tmp_path / "optimized.usdz")

    def test_optimizer_requires_text_usda_layer(self) -> None:
        for suffix in (".usd", ".usdc"):
            with self.subTest(suffix=suffix), _workspace("suffix-fixture-") as raw_path:
                tmp_path = Path(raw_path)
                source = tmp_path / "source.usdz"
                _write_fixture(source, layer_name=f"scene{suffix}")
                with self.assertRaisesRegex(ValueError, "text USDA"):
                    optimize_usdz(source, tmp_path / "optimized.usdz")

    def test_compiler_canonicalizes_existing_usdc_without_path_collision(self) -> None:
        class FakeRoot:
            def ListInfoKeys(self):
                return []

        class FakeLayer:
            source_path: Path | None = None
            created_paths: list[Path] = []

            def __init__(self, path: str):
                self.path = Path(path)
                self.pseudoRoot = FakeRoot()
                self.rootPrims = []

            def Save(self):
                self.path.write_bytes(b"PXR-USDC direct-canonicalization-fixture")

        class FakeLayerAPI:
            @staticmethod
            def FindOrOpen(path: str):
                FakeLayer.source_path = Path(path)
                return FakeLayer(path)

            @staticmethod
            def CreateNew(path: str):
                candidate = Path(path)
                FakeLayer.created_paths.append(candidate)
                return FakeLayer(path)

        fake_pxr = types.ModuleType("pxr")
        fake_pxr.Sdf = types.SimpleNamespace(Layer=FakeLayerAPI)
        with _workspace("compiler-usdc-fixture-") as raw_path:
            tmp_path = Path(raw_path)
            model = tmp_path / "model.usdz"
            with zipfile.ZipFile(model, "w") as archive:
                archive.writestr("aaa.bin", b"first lexical non-layer")
                archive.writestr("texture.bin", b"texture")
                archive.writestr("canonical.usdc", b"source-usdc")
            with patch.dict(sys.modules, {"pxr": fake_pxr}):
                compiler._canonicalize_usdz(model)

            self.assertEqual(FakeLayer.created_paths[0].suffix, ".usdc")
            self.assertNotEqual(FakeLayer.created_paths[0], FakeLayer.source_path)
            with zipfile.ZipFile(model) as archive:
                self.assertEqual(
                    archive.namelist(), ["canonical.usdc", "aaa.bin", "texture.bin"]
                )

    def test_cli_reports_value_errors_without_traceback(self) -> None:
        with _workspace("cli-error-fixture-") as raw_path:
            tmp_path = Path(raw_path)
            source = tmp_path / "unsafe.usdz"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../scene.usda", USDA)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = optimizer.main(
                    ["--input", str(source), "--output", str(tmp_path / "out.usdz")]
                )

            self.assertEqual(status, 2)
            self.assertEqual(stderr.getvalue(), "error: USDZ export contains unsafe member paths\n")


def _workspace(prefix: str):
    context = ROOT / ".context"
    context.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=context)


if __name__ == "__main__":
    unittest.main()
