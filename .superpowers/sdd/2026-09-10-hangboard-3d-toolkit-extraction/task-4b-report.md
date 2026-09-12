# Task 4B report

## Result

Canonical semantic topology now binds each orientation-preserving, positioned
coordinate face cycle to both its polygon material index and resolved material
name before canonical sorting and hashing. This preserves vertex permutation,
face-order permutation, and loop-rotation tolerance while detecting material
swaps between positioned faces. The change is limited to
`geometry_primitives.py` and its semantic regression test.

## Verification

- `python3 -m py_compile Tools/HangboardModels/geometry_primitives.py Tools/HangboardModels/test_geometry_primitives.py` — passed.
- Focused Blender semantic regression command:
  `blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/test_geometry_primitives.py`
  — blocked before Python execution by Blender 5.2.0 startup signal 11 in
  Metal backend initialization (`/var/folders/.../blender.crash.txt`).
- No generated Task 4B resources were created under `.context`; existing
  unrelated `.context` resources were left untouched.

## Commit

Local commit: created locally (not pushed).
