# Stage 2 Treated Anchor Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every exported Stage 2 anchor remains valid after corner treatments alter the authoritative contour and raster labels.

**Architecture:** Share the product-neutral corner-treatment geometry semantics at the browser model boundary, then validate/pick the exported anchor against the treated contour rather than the untreated control contour. The Python materializer remains the authoritative independent validator.

**Tech Stack:** Browser JavaScript model, Python Stage 2 materialization, Node.js test runner, pytest.

## Global Constraints

- This branch changes only local workbench correctness; do not tune smoothing, materials, or visual appearance.
- All logic must be programmatic, repeatable, scalable, product-neutral, and valid for unseen commercial boards.
- Do not add product-specific code, coordinates, masks, templates, inventories, or tuning.
- Preserve the three protected PNG hashes exactly.
- Prefix every shell command with `rtk`; use `apply_patch` for edits.

---

### Task 1: Validate Export Anchors Against Treated Geometry

**Files:**
- Modify: `Tools/hold-highlight-editor/editor-model.js`
- Modify if needed to share existing semantics without duplication: `Tools/hold-highlight-editor/vector-path-model.js`
- Modify: `Tools/hold-highlight-editor/tests/editor_model.test.js`
- Modify if shared behavior changes: `Tools/hold-highlight-editor/tests/vector_path_model.test.js`
- Test: `Tools/HangboardOnboarding/tests/test_review_edits.py`

**Interfaces:**
- Consumes: a Stage 2 region with contour, anchor, contour styling, and `cornerTreatments` metadata.
- Produces: an exported anchor whose rounded raster pixel is occupied by the same treated authoritative contour that Python materialization constructs.

- [ ] **Step 1: Add a failing browser regression**

Use a simple square with anchor `[0, 0]` and a rounded treatment at corner `0`. Assert that export does not preserve `[0, 0]` after the rounded cut removes that raster pixel, that the fallback is deterministic, and that the original region is not mutated. Derive the expected literal independently from the production helper.

- [ ] **Step 2: Add a failing Python contract regression**

Materialize the browser-shaped export fixture with the rounded treatment and assert the exported anchor owns the region label after treatment. Verify RED against current code because the untreated-contour anchor is preserved and later rejected or unoccupied.

- [ ] **Step 3: Run RED**

```bash
rtk node --test --test-name-pattern='treated anchor' Tools/hold-highlight-editor/tests/editor_model.test.js
rtk pytest -q Tools/HangboardOnboarding/tests/test_review_edits.py -k treated_anchor
```

- [ ] **Step 4: Implement the minimal product-neutral fix**

Make browser export derive the same treated contour semantics used for authoritative Stage 2 materialization before deciding whether to preserve an anchor or choose the deterministic interior fallback. Reuse shared geometry logic where practical; do not duplicate a second divergent corner-treatment algorithm and do not add DOM-only hooks. Keep Python validation independent.

- [ ] **Step 5: Run GREEN and regressions**

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js Tools/hold-highlight-editor/tests/vector_path_model.test.js
rtk pytest -q Tools/HangboardOnboarding/tests/test_review_edits.py
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
rtk pytest -q Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests
rtk node --check Tools/hold-highlight-editor/editor-model.js
rtk node --check Tools/hold-highlight-editor/vector-path-model.js
rtk git diff --check
```

- [ ] **Step 6: Commit**

```bash
rtk git add Tools/hold-highlight-editor/editor-model.js Tools/hold-highlight-editor/vector-path-model.js Tools/hold-highlight-editor/tests/editor_model.test.js Tools/hold-highlight-editor/tests/vector_path_model.test.js Tools/HangboardOnboarding/tests/test_review_edits.py
rtk git commit -m "Validate anchors against treated geometry"
```
