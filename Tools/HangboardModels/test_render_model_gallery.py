from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from migration_manifest import load_migration_manifest
from model_verification import VerificationReport
from render_model_gallery import ReviewArtifact, _fixed_view_names, cleanup_gallery_output, render_model_gallery


def _manifest_document(model_hash: str, descriptor_hash: str) -> dict[str, object]:
    return {
        "schemaVersion": 1, "boardID": "fixture", "revision": "r1",
        "boardJSON": "board.json", "evidencePacket": "evidence.json",
        "sourceBlend": {"path": "source.blend", "sha256": "a" * 64},
        "logicalHoldIDs": ["left"],
        "presentation": {"id": "primary", "type": "model", "assetPath": "assets/primary.usdz", "descriptorPath": "assets/primary.model.json"},
        "positions": [{"id": "default", "activeHoldIDs": ["left"]}],
        "suspensionProfile": "none",
        "deliberateOmissions": ["screw holes", "mounting hardware"],
        "verification": {"triangleCeiling": 10, "probeIDs": []},
        "reviewViews": ["front", "three-quarter"],
        "artifacts": {"packageSHA256": model_hash, "descriptorSHA256": descriptor_hash},
    }


class GalleryTests(unittest.TestCase):
    def package(self, root: Path) -> tuple[Path, object]:
        package = root / "package"
        (package / "assets").mkdir(parents=True)
        model = b"model-bytes"
        descriptor = json.dumps({"modelSHA256": hashlib.sha256(model).hexdigest()}).encode()
        with zipfile.ZipFile(package / "assets/primary.usdz", "w") as archive:
            archive.writestr("canonical-neutral-wood.png", b"texture")
        (package / "assets/primary.model.json").write_bytes(descriptor)
        (package / "board.json").write_text(json.dumps({"holds": [{"id": "left"}]}), encoding="utf-8")
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(_manifest_document(
            hashlib.sha256((package / "assets/primary.usdz").read_bytes()).hexdigest(),
            hashlib.sha256(descriptor).hexdigest(),
        )), encoding="utf-8")
        return package, load_migration_manifest(manifest_path)

    def test_gallery_requires_owned_context_output_and_records_stable_artifacts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, manifest = self.package(root)
            owner = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).name
            output = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())) / ".context" / f"{owner}-gallery-{uuid.uuid4().hex}"
            report = VerificationReport("fixture", {"status": "passed"})
            def fake_render(_package, _manifest, destination):
                paths = (destination / "front.png", destination / "three-quarter.png")
                for path in paths:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(path.name.encode())
                return paths
            try:
                with patch("render_model_gallery.verify_model_package", return_value=report) as verify, patch(
                    "render_model_gallery._render_fixed_views",
                    side_effect=fake_render,
                ):
                    artifacts = render_model_gallery(package, manifest, output)
            finally:
                cleanup_gallery_output(output)
            verify.assert_called_once()
            self.assertEqual(tuple(item.view for item in artifacts), ("front", "three-quarter"))
            self.assertTrue(all(item.provenance == "verified-package; fixed-view" for item in artifacts))
            self.assertTrue(all(len(item.sha256) == 64 for item in artifacts))

    def test_verification_failure_prevents_any_render(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, manifest = self.package(root)
            owner = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).name
            output = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())) / ".context" / f"{owner}-gallery-{uuid.uuid4().hex}"
            with patch("render_model_gallery.verify_model_package", side_effect=ValueError("not verified")), patch(
                "render_model_gallery._render_fixed_views"
            ) as render:
                with self.assertRaisesRegex(ValueError, "not verified"):
                    render_model_gallery(package, manifest, output)
            render.assert_not_called()

    def test_cleanup_only_removes_exact_owned_output_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            owner = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).name
            context = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())) / ".context"
            output = context / f"{owner}-gallery-{uuid.uuid4().hex}"
            output.mkdir(parents=True)
            (output / "render.png").write_bytes(b"x")
            sentinel = context / f"{owner}-keep-{uuid.uuid4().hex}.txt"
            sentinel.write_bytes(b"keep")
            try:
                cleanup_gallery_output(output)
                self.assertFalse(output.exists())
                self.assertTrue(sentinel.exists())
                with self.assertRaisesRegex(ValueError, "owner-prefixed"):
                    cleanup_gallery_output(context / "other-gallery")
            finally:
                sentinel.unlink(missing_ok=True)

    def test_arbitrary_tmp_context_is_rejected_even_with_owner_prefix(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            owner = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).name
            output = root / ".context" / f"{owner}-gallery"
            with self.assertRaisesRegex(ValueError, "workspace-owned"):
                cleanup_gallery_output(output)

    def test_symlinked_workspace_context_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "workspace"
            outside = Path(raw) / "outside"
            workspace.mkdir()
            outside.mkdir()
            (workspace / ".context").symlink_to(outside, target_is_directory=True)
            owner = workspace.name
            output = workspace / ".context" / f"{owner}-gallery"
            with patch.dict(os.environ, {"PASEO_WORKTREE_PATH": str(workspace)}):
                with self.assertRaisesRegex(ValueError, "canonical"):
                    cleanup_gallery_output(output)

    def test_unknown_review_view_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            package, manifest = self.package(Path(raw))
            manifest = manifest.__class__(
                **{**manifest.__dict__, "review_views": ("front", "unknown")}
            )
            owner = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())).name
            output = Path(os.environ.get("PASEO_WORKTREE_PATH", os.getcwd())) / ".context" / f"{owner}-gallery-{uuid.uuid4().hex}"
            with self.assertRaisesRegex(ValueError, "unsupported"):
                _fixed_view_names(manifest)


if __name__ == "__main__":
    unittest.main()
