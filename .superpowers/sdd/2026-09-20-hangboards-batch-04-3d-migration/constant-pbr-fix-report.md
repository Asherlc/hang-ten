# Constant PBR importer validation fix

## Scope and root cause

`_require_image_materials` rejected every importer-visible material without a
`TEX_IMAGE` node. Blender 5.2 reimports a texture-free USD Preview Surface as
an unlinked `Principled BSDF` (`BSDF_PRINCIPLED`) with finite constant inputs,
so the image-only rule rejected valid authored constant PBR materials.

The fix keeps the image path authoritative whenever an image node exists:
broken or data-less image nodes still fail. Only an image-less material may
instead pass as a constant Principled material, and only when Base Color (RGBA),
Roughness, Metallic, and Alpha are unlinked, finite, within `[0, 1]`, and both
alpha values are nonzero. Missing materials, materialless slots, no faces,
absent/empty node trees, linked inputs, nonfinite values, out-of-range values,
and fully transparent materials fail closed.

## RED

Command:

```sh
rtk python3 -m unittest discover -s Tools/HangboardModels -p test_contact_model_package.py -v
```

Result before the production change: 7 tests ran; 3 failures and 1 error.
The constant-unit test errored exactly with `ValueError: imported mesh body has
no image material`; malformed constant branches still returned that obsolete
error; and the real Blender test could not launch in the managed sandbox.

The sandbox Blender smoke command:

```sh
rtk blender --background --factory-startup --python-expr "print('BLENDER_SMOKE_OK')"
```

terminated with signal 11 before Python (`blender.crash.txt` was written). This
is recorded separately from compiler behavior. The same command in authorized
host context printed `BLENDER_SMOKE_OK` and quit normally.

## Blender 5.2 importer evidence

An authorized host-context texture-free export/reimport emitted material
`constant_pbr` with `Principled BSDF`, node type `BSDF_PRINCIPLED`, and unlinked
inputs: Base Color RGB approximately `(0.2, 0.4, 0.6)`, Base Color alpha `1.0`,
Roughness approximately `0.55`, Metallic approximately `0.1`, and Alpha `1.0`.
The integration test pins these importer-visible input names and values after
the compiler's actual USDZ export/reimport round trip.

## GREEN

Focused semantic branches:

```sh
rtk python3 -m unittest discover -s Tools/HangboardModels -p test_contact_model_package.py -k imported -v
```

Result: 4 tests passed.

Focused compiler suite (authorized host context because Blender cannot launch
inside the managed sandbox):

```sh
rtk python3 -m unittest discover -s Tools/HangboardModels -p test_contact_model_package.py -v
```

Result: 7 tests passed, including the real Blender USDZ round trip.

Relevant full model-tool collection (authorized host context):

```sh
rtk python3 -m unittest discover -s Tools/HangboardModels -p 'test_*.py' -v
```

Result: 28 tests passed.

Additional checks:

```sh
rtk python3 -m py_compile Tools/HangboardModels/contact_model_package.py Tools/HangboardModels/test_contact_model_package.py
rtk git diff --check -- Tools/HangboardModels/contact_model_package.py Tools/HangboardModels/test_contact_model_package.py
```

Result: both passed. The temporary workspace-owned Blender probe
`.context/learned-giraffe-constant-pbr-probe.usdz` was removed and its absence
verified before completion.

## Concurrent-file safeguards

Base HEAD was `adc875d95c80f2e509d4ac403f93f30795d17350`. Known concurrent Task
8 changes were already present in
`Tools/HangboardPackages/tests/test_approved_board_packages.py` and
`Tools/HangboardPackages/tests/test_cord_audit.py`; further Task 8 paths may
appear while its owner works. No concurrent content was inspected, edited,
reverted, diffed, staged, committed, or otherwise included here. The staged
file list was checked and contains only the compiler, its focused test file,
and this report.
