### Task 3: Terra — compile, reimport, and verify both packages

**Files:**
- Create: `Tools/HangboardModels/verify_beastmaker_1000.py`
- Modify: `Tools/HangboardModels/verify_wood_grips_compact_ii.py`, `Tools/HangboardModels/test_model_reports.py`, `Tools/HangboardModels/README.md`
- Create owned outputs in both `.context/shaky-rat-*` directories.

**Interfaces:**
- Consumes approved `.blend`, package logical inventory, and generic `compile_model_package.py`.
- Produces exact package-ready `primary.usdz`, `primary.model.json`, `export-verification.json`, and actual-export roundtrip renders.

**Beastmaker compiler-input ruling:** `beastmaker-1000-compiler-input.blend` is
the generator-emitted, audited rigid coordinate-frame transport input for the
generic compiler. The editable Blender scene uses X-width/Y-depth/Z-height;
the package board frame uses X-right/Y-up/Z-toward-climber. The transport must
preserve every mesh name, role, hold ID, material, local vertex, and topology,
and may apply only the documented rigid transform. It is not alternate
geometry, an editable-shape change, or a compiler behavior change.

- [ ] **Step 1: Write failing Beastmaker verifier expectations**

```python
def test_beastmaker_report_requires_22_hold_ids_and_no_hardware():
    report = verify_report(load_report("fixture-report.json"), expected_ids=BEASTMAKER_IDS)
    assert report["hold_ids_preserved"] == 22
    assert report["hardware_mesh_count"] == 0
```

- [ ] **Step 2: Run model report test**

Run: `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py`

Expected: FAIL until the Beastmaker verifier/report family is registered.

- [ ] **Step 3: Compile and verify Beastmaker actual export**

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/shaky-rat-beastmaker-1000/beastmaker-1000-compiler-input.blend --board-json Hangboards/beastmaker-1000/board.json --output-directory .context/shaky-rat-beastmaker-1000/package`

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_beastmaker_1000.py -- --output .context/shaky-rat-beastmaker-1000/package`

Expected: both exit 0; reimported USDZ has 580 × 150 × 58 mm bounds within one micrometre, all 22 hold IDs, all geometry bound, no hardware meshes, texture/material on every mesh, explicit triangles, below recorded triangle ceiling, and actual-export review renders.

- [ ] **Step 4: Recompile Compact without lower-cost shape changes**

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/shaky-rat-metolius-wood-grips-compact-ii/wood-grips-compact-ii.blend --board-json Hangboards/metolius-wood-grips-compact-ii/board.json --output-directory .context/shaky-rat-metolius-wood-grips-compact-ii/package`

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_wood_grips_compact_ii.py -- --format usdz --skip-renders .context/shaky-rat-metolius-wood-grips-compact-ii/package`

Expected: exit 0 with 19 IDs, all material/node/hash checks, and no geometry edit. If the official comparison reveals a physical defect, stop and dispatch only that correction to Astra, regenerate all exports/views, and repeat this task.

- [ ] **Step 5: Run report tests and commit deterministic tooling**

Run: `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py`

Expected: PASS.

Run: `git add Tools/HangboardModels/verify_beastmaker_1000.py Tools/HangboardModels/verify_wood_grips_compact_ii.py Tools/HangboardModels/test_model_reports.py Tools/HangboardModels/README.md && git commit -m "feat: verify model-first board exports"`

Review gate: fresh Terra reviewer verifies compiler/verifier never modifies authored vertex shape and output descriptor hashes exact USDZ bytes.
