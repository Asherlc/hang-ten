"""Focused tests for lossless text-USDA to binary-USDC USDZ optimization."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from optimize_usdz import optimize_usdz


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


def _write_fixture(path: Path) -> tuple[bytes, bytes]:
    texture = b"PNG bytes are opaque to this serialization test\x00\x01"
    note = b"unchanged non-USD member"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("notes.bin", note)
        archive.writestr("textures/wood.png", texture)
        archive.writestr("scene.usda", USDA.encode("utf-8"))
    return texture, note


class OptimizeUSDZTests(unittest.TestCase):
    def test_optimizer_emits_deterministic_binary_layer_and_preserves_usd_semantics(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="optimizer-fixture-",
            dir=ROOT / ".context" / "exotic-swan-task-a-work",
        ) as raw_path:
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
                    archive.namelist(), ["notes.bin", "scene.usdc", "textures/wood.png"]
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


    def test_optimizer_rejects_unsafe_archive_member_paths(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="unsafe-fixture-",
            dir=ROOT / ".context" / "exotic-swan-task-a-work",
        ) as raw_path:
            tmp_path = Path(raw_path)
            source = tmp_path / "unsafe.usdz"
            output = tmp_path / "optimized.usdz"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../scene.usda", USDA)

            with self.assertRaisesRegex(ValueError, "unsafe member paths"):
                optimize_usdz(source, output)


if __name__ == "__main__":
    unittest.main()
