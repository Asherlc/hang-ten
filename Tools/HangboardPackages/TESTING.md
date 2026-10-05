# Testing the hangboard package validator

The catalog tests read real generated packages. Before running them from a
fresh checkout, fetch the CAD LFS objects and build the runtime resources as
described in [generated artifacts](../../docs/GENERATED_ARTIFACTS.md).
Compilation requires the pinned FreeCAD/Blender tools; the scripts install
them into owned scratch when no suitable installed tool is configured.

From the repository root, create an owned test environment and run the suite:

```sh
(
  set -eu
  package_owner=$(basename "${PASEO_WORKTREE_PATH:-$PWD}")
  rtk proxy mkdir -p .context
  package_scratch=$(mktemp -d "$PWD/.context/$package_owner-package-tests-XXXXXX")
  trap 'rm -rf "$package_scratch"; test ! -e "$package_scratch"' EXIT
  printf '%s\n' "$package_owner" > "$package_scratch/owner"
  rtk proxy python3 -m venv "$package_scratch/venv"
  rtk proxy "$package_scratch/venv/bin/python" -m pip install \
    -e 'Tools/HangboardPackages[dev]'
  rtk git lfs pull
  rtk proxy env HANGBOARD_PYTHON="$package_scratch/venv/bin/python" \
    bash scripts/build-runtime-assets.sh
  rtk proxy "$package_scratch/venv/bin/python" -m pytest \
    Tools/HangboardPackages/tests -q
)
```

Generated resources remain in their ignored local paths for later builds.
When source and generated assets are already current, reuse an existing
supported Python environment and run just the pytest command.

Exercise discovery through the read-only package commands:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
```

Discovery starts from the flat CAD sources and supported non-CAD package
directories. Final-inventory validation requires every discovered package to
be complete and schema-valid; status reports the same inventory and draft paths.
