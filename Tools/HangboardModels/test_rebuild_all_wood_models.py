"""Focused filesystem guard tests for the rebuild-all package contract."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from rebuild_all_wood_models import SHIPPED_PACKAGE_FILES, require_exact_package_tree


class RebuildAllWoodModelsTests(unittest.TestCase):
    def test_unexpected_shipped_package_file_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="wood-package-tree-") as directory:
            package = Path(directory)
            for relative in SHIPPED_PACKAGE_FILES:
                path = package / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            require_exact_package_tree(package, SHIPPED_PACKAGE_FILES, label="fixture")
            (package / "assets/stale.png").write_bytes(b"unexpected")
            with self.assertRaises(ValueError):
                require_exact_package_tree(package, SHIPPED_PACKAGE_FILES, label="fixture")


if __name__ == "__main__":
    unittest.main()
