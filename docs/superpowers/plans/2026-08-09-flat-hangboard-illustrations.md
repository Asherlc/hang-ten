# Flat Hangboard Illustrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a preview-only set of 32 warm, flattened, symbolic hangboard illustrations that are easier to trace than the current semi-realistic renders.

**Architecture:** Keep the existing PNG catalog as immutable visual references. Generate one new PNG per source image with the built-in image-generation tool, save the results under a new `flat-illustrations/` directory, and create a non-runtime contact sheet for visual QA.

**Tech Stack:** Codex built-in image generation, local image inspection, PNG assets, and a lightweight contact-sheet utility.

## Global Constraints

- Cover the 32 individual PNG board renders currently in the catalog.
- Keep the existing realistic renders and normalized outline JSON unchanged.
- Save the new images as a sibling preview set under `docs/hangboard-generative-catalog/flat-illustrations/`.
- Do not add or modify Swift assets, `BoardDesign`, `BoardCatalog`, hit testing, or runtime app rendering.
- Do not treat generated pixels as authoritative interaction geometry.
- Use a small warm palette: parchment background, light wood or clay board planes, one darker warm contour/shadow color, and a restrained accent for cavity depth where useful.
- Avoid photographic grain, wood pores, glossy highlights, realistic cast shadows, mounting hardware, logos, product text, hands, wall scenes, and decorative objects.
- Name each result with the existing source stem plus `-flat.png`.

---

### Task 1: Generate and review a representative pilot

**Files:**
- Read: `docs/hangboard-generative-catalog/metolius-project.png`
- Create: `docs/hangboard-generative-catalog/flat-illustrations/metolius-project-flat.png`
- Create: `.context/flat-hangboard-illustrations/pilot-review.md`

**Interfaces:**
- Consumes: the existing `metolius-project.png` reference image and the shared prompt contract in the design spec.
- Produces: one accepted pilot PNG and a short review note stating whether the silhouette, major hold groups, palette, and traceability criteria pass.

- [ ] **Step 1: Prepare the shared generation prompt.**

  Use the pilot source image as a visual reference and generate a single centered, front-facing illustration on a consistent landscape canvas. The prompt must require a flattened symbolic product diagram, a small warm palette, clean outer silhouette, simplified major rails and cavities, generous padding, and no texture, photorealistic lighting, hardware, branding, lettering, hands, or scene context.

- [ ] **Step 2: Generate the pilot with the built-in image tool.**

  Save the selected result into `docs/hangboard-generative-catalog/flat-illustrations/metolius-project-flat.png`. Do not overwrite the source PNG.

- [ ] **Step 3: Inspect the pilot image.**

  Verify: the board remains recognizable; the two side pocket groups and long center rails remain distinct; the warm flat palette is consistent; the image has no accidental text or realistic texture; and the padding makes the result easy to trace.

- [ ] **Step 4: Record the pilot verdict.**

  Write `.context/flat-hangboard-illustrations/pilot-review.md` with the chosen prompt, the five review checks, and either `PASS` or a concrete single prompt adjustment followed by a regenerated pilot. Keep the note workspace-owned and do not add it to the app target.

- [ ] **Step 5: Verify the pilot artifact.**

  Confirm the PNG exists, is readable, and the source catalog file and outline JSON remain unchanged. Report the exact output path and verdict.

---

### Task 2: Generate the remaining 31 illustrations and QA sheet

**Files:**
- Read: all 31 remaining `docs/hangboard-generative-catalog/*.png` source images, excluding `contact-sheet-primary.png` and the pilot source.
- Create: `docs/hangboard-generative-catalog/flat-illustrations/*-flat.png` for every remaining source stem.
- Create: `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png`
- Create: `.context/flat-hangboard-illustrations/batch-review.md`

**Interfaces:**
- Consumes: the accepted pilot prompt and review note from Task 1.
- Produces: a complete 32-image flat preview set and a contact sheet with one labeled tile per board.

- [ ] **Step 1: Enumerate the source set.**

  Derive the source stems from the 32 individual PNGs in `docs/hangboard-generative-catalog/`, excluding only `contact-sheet-primary.png`. Do not use the existing outline JSON files as image sources and do not alter the source catalog.

- [ ] **Step 2: Generate one image per source.**

  Issue one built-in image-generation call per board, using the accepted pilot prompt as the shared style contract and the board's own PNG as the reference. Preserve unusual structures such as split boards, paired palm boards, curved boards, center openings, deep rails, and asymmetric silhouettes when present. Save each result as `<source-stem>-flat.png` under `docs/hangboard-generative-catalog/flat-illustrations/`.

- [ ] **Step 3: Validate the output inventory.**

  Confirm that exactly 32 `*-flat.png` files exist, that every source stem has one output, and that no source PNG or outline JSON changed.

- [ ] **Step 4: Build the contact sheet.**

  Create `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png` with all 32 flat illustrations in the same catalog order, labeled by board stem or existing board name, on a neutral light background. Keep it as a review artifact only.

- [ ] **Step 5: Inspect and record batch QA.**

  Review the contact sheet and representative individual images for silhouette retention, major hold-row preservation, warm flat style consistency, absence of unwanted text/texture/objects, and tracing-friendly contrast. Record counts, any known weak images, and the final `PASS`/`NEEDS_REVIEW` verdict in `.context/flat-hangboard-illustrations/batch-review.md`.

- [ ] **Step 6: Run final repository checks.**

  Verify the changed-file list contains only the new preview directory, the contact sheet, and workspace-owned review notes. Do not stage or modify unrelated user worktree changes. Report the full output inventory and any images that need a later regeneration.
