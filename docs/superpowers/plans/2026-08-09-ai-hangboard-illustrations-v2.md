# AI Hangboard Illustrations V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a separate 32-board AI illustration V2 set with better polish and deterministic-reference geometry fidelity.

**Architecture:** Use the built-in image tool once per board with two local references: deterministic preview for geometry and original render for physical character. Save results to a sibling directory and build a labeled review contact sheet.

**Tech Stack:** Built-in image generation, local image inspection, PNG assets, Pillow contact sheet.

## Global Constraints

- Keep the deterministic preview set unchanged.
- Save exactly 32 `<stem>-ai-v2.png` files under `docs/hangboard-generative-catalog/ai-illustrations-v2/`.
- Use one built-in image-generation call per distinct board; do not use CLI fallback.
- Preserve outer silhouette, disconnected pieces, center gaps, and major hold count and placement.
- Use a warm editorial illustration style with crisp contours, simple color-blocked planes, restrained depth, and a uniform parchment background.
- Add no text, logos, bolts, hands, wall scene, photographic texture, or dramatic shadow.

---

### Task 1: Generate and review AI illustration V2 catalog

**Files:**
- Read: `docs/hangboard-generative-catalog/*.png`
- Read: `docs/hangboard-generative-catalog/flat-illustrations/*-flat.png`
- Create: `docs/hangboard-generative-catalog/ai-illustrations-v2/*-ai-v2.png`
- Create: `docs/hangboard-generative-catalog/ai-illustrations-v2-contact-sheet.png`
- Create: `.context/flat-hangboard-illustrations/ai-v2-review.md`

**Interfaces:**
- Consumes: one deterministic geometry reference and one original source reference per board.
- Produces: 32 versioned V2 PNGs and one labeled contact sheet.

- [ ] **Step 1: Generate and inspect a pilot.**

  Use `metolius-project-flat.png` as the geometry reference and
  `metolius-project.png` as the physical-character reference. Require geometry
  preservation and the shared warm editorial style. Inspect silhouette, side
  groups, center rails, background uniformity, and prohibited details. Apply at
  most one targeted shared-prompt adjustment.

- [ ] **Step 2: Generate the remaining 31 boards.**

  Issue one built-in call per board with its paired references. Save each result
  as `<stem>-ai-v2.png`; do not overwrite deterministic or original images.

- [ ] **Step 3: Build and inspect the contact sheet.**

  Create a four-column labeled contact sheet in catalog order. Inspect all 32
  tiles, then inspect individual images for any material silhouette/layout
  failures. Regenerate only those material failures.

- [ ] **Step 4: Verify inventory and report.**

  Confirm 32 source stems map to 32 V2 outputs, all PNGs are readable, and the
  deterministic/source files are unchanged. Record the final prompt, inventory,
  targeted regenerations, weak-but-usable boards, and PASS/NEEDS_REVIEW verdict
  in `.context/flat-hangboard-illustrations/ai-v2-review.md`.

- [ ] **Step 5: Commit scoped artifacts.**

  Commit only the new V2 directory, contact sheet, and review note. Preserve all
  unrelated working-tree changes.
