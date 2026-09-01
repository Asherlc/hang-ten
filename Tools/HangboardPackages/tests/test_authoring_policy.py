from __future__ import annotations

import ast
from pathlib import Path
import tomllib


TOOL_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PYTHON_ROOTS = (TOOL_ROOT / "src", TOOL_ROOT / "scripts")
FORBIDDEN_IMPORT_ROOTS = frozenset({"PIL", "cv2", "rembg", "skimage"})
FORBIDDEN_DEPENDENCY_PREFIXES = (
    "opencv",
    "pillow",
    "rembg",
    "scikit-image",
)


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            roots.add(node.module.partition(".")[0])
    return roots


def test_production_tooling_has_no_image_driven_authoring_capability() -> None:
    """Keep raster segmentation, masks, contours, and cropping out of tooling."""
    violations: list[str] = []
    for root in PRODUCTION_PYTHON_ROOTS:
        for path in sorted(root.rglob("*.py")):
            forbidden = sorted(_imported_roots(path) & FORBIDDEN_IMPORT_ROOTS)
            if forbidden:
                violations.append(
                    f"{path.relative_to(TOOL_ROOT)} imports {', '.join(forbidden)}"
                )

    pyproject = tomllib.loads(
        (TOOL_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    optional_dependencies = pyproject["project"].get("optional-dependencies", {})
    for extra, dependencies in sorted(optional_dependencies.items()):
        if extra == "dev":
            continue
        for dependency in dependencies:
            normalized = dependency.casefold()
            if normalized.startswith(FORBIDDEN_DEPENDENCY_PREFIXES):
                violations.append(f"optional extra {extra} includes {dependency}")

    assert violations == []
