# Suspended Hangboard Migration Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the 3D hangboard migration skill so compatible portable boards can use one USDZ with canonical face poses and a deterministic, physically plausible, presentation-only hanging cord.

**Architecture:** Keep the product USDZ as the sole board/contact geometry. Package-level suspension metadata describes the cord attachment and canonical pose per existing position; the app derives an invisible-anchor cord and camera framing at runtime. The skill establishes evidence, validation, interaction, and cost-routing requirements without prescribing a Flash Board implementation before its evidence gate passes.

**Tech Stack:** Markdown skill instructions, schema/package validators, USDZ/descriptor tooling, SceneKit/SwiftUI runtime, XCTest, existing iOS migration validation.

**Spec:** `docs/superpowers/specs/2026-09-09-suspended-hangboard-presentation-design.md`

## Global Constraints

- Preserve one model-only USDZ and descriptor per compatible board; never duplicate models or retain a raster fallback for face/position changes.
- The board USDZ may include physical attachment hardware supported by evidence, but never a baked display cord, visible nail, hook, ceiling, or anchor.
- Treat physical attachment facts and position availability as source-backed; label model coordinates, anchor, cord, pose, and camera values as estimates unless direct evidence supports them.
- Use a deterministic static catenary or physically necessary taut segment, not rope simulation; cord presentation is non-pickable and non-accessible.
- Manual interaction orbits the camera only; selecting a hold/workout position resets board and camera to that position's canonical pose.
- Use Luna for routine evidence, schema, cord math, tests, and reviews; Terra only for unresolved intricate non-geometry work; Astra only for final physical board geometry after human approval of the multi-angle evidence packet.
- Keep all generated review output workspace-owned and clean it before handoff.

---

### Task 1: Add the portable-suspension authoring and evidence contract

**Files:**
- Modify: `.codex/skills/migrate-hangboard-to-3d/SKILL.md:24-46`

**Interfaces:**
- Consumes: existing `board.json` schema v2 model media, model descriptor node IDs, existing logical `positions`, and the approved design spec.
- Produces: a reusable optional `suspension` model-presentation contract for a future parser/runtime implementation; it does not modify a board package in this task.

- [ ] **Step 1: Add a failing forward-use checklist to the skill draft**

  Insert a concise `## Suspended portable presentations` section after `## Separate logical data from model geometry` that states a future migration must be rejected unless all of these are decidable from package data:

  ```text
  - exactly one model USDZ and descriptor;
  - an optional, explicitly tagged `singleCord` suspension declaration;
  - one physical attachment point bound to an importer-visible descriptor node;
  - exactly one finite canonical pose for every supported position, and no pose for an unknown position;
  - a display-only invisible anchor plus positive cord length and radius; and
  - no baked cord/anchor mesh, second face model, raster fallback, hand-authored hold bounds, or hold-node attachment shortcut.
  ```

- [ ] **Step 2: Review the draft against existing model-only language**

  Run:

  ```bash
  rtk rg -n -C 2 "model-only|raster fallback|sole geometry|Suspended portable" .codex/skills/migrate-hangboard-to-3d/SKILL.md
  ```

  Expected: the new section reinforces—not weakens—the existing sole-geometry and model-only rules.

- [ ] **Step 3: Write the complete authoring/evidence requirements**

  In that section, require `attachment.nodeID`, model-frame `pointInModel`, invisible-anchor display estimate, cord rest length/radius/material estimates, and normalized canonical pose transforms keyed by existing `positionID`. State that logical holds remain metadata-only, positions select faces rather than create duplicate contacts, and unsupported cord dimensions or knot details must remain labeled estimates. Require the retained packet to record exact revision, each usable face/position, attachment evidence, a position-to-hold mapping, two approved distinct visual snapshots including an attachment-region view when available, and all deliberate display simplifications. Explicitly preserve the current multi-angle human approval gate before Astra.

- [ ] **Step 4: Verify the authoring contract is discriminating**

  Run:

  ```bash
  rtk rg -n "singleCord|positionID|attachment.nodeID|invisible anchor|baked" .codex/skills/migrate-hangboard-to-3d/SKILL.md
  ```

  Expected: each required concept appears in the new section and does not name Flash Board as a universal convention.

- [ ] **Step 5: Commit**

  ```bash
  git add .codex/skills/migrate-hangboard-to-3d/SKILL.md
  git commit -m "Document suspended portable hangboard migration contract"
  git push
  ```

### Task 2: Add deterministic cord, interaction, and validation requirements

**Files:**
- Modify: `.codex/skills/migrate-hangboard-to-3d/SKILL.md:66-98`

**Interfaces:**
- Consumes: the `singleCord` contract defined in Task 1 and the existing exporter/native-picking/application integration requirements.
- Produces: implementation-ready requirements for validators and `BoardModelView` integration, without changing their code in this skill-only update.

- [ ] **Step 1: Add the failing behavior cases to the integration instructions**

  Add explicit required failure outcomes: rest length shorter than anchor-to-attachment separation, nonfinite or nonpositive cord parameters, invalid/nonunit pose transform, missing attachment node, unsolved curve, cord collision with the board away from the attachment, and cord becoming a selectable/nearer pick. Each must end in the current explicit unavailable state; none may fall back to a line, another orientation model, raster rendering, or visible anchor.

- [ ] **Step 2: Verify existing failure behavior is not contradicted**

  Run:

  ```bash
  rtk rg -n -C 2 "unavailable|picking|camera|hit test|fallback" .codex/skills/migrate-hangboard-to-3d/SKILL.md
  ```

  Expected: the new rules extend the existing explicit-unavailable and nearest-triangle-picking requirements.

- [ ] **Step 3: Write the deterministic presentation and interaction contract**

  Require the runtime to transform the local attachment with the selected canonical board pose, derive a uniform-cord catenary in the gravity plane when slack exists, and use a straight segment only at the physical minimum-length tolerance. Require endpoint continuity, finite samples, stable sampling/material settings, non-pickability/accessibility, mesh/ray clearance checks, and camera-space framing checks. State that changing a selected hold or workout position smoothly restores its board/camera canonical state; manual gestures orbit camera azimuth/elevation/zoom only and never independently rotate the suspended board. Do not permit a visible nail, hook, or surrounding mounting environment.

- [ ] **Step 4: Add per-pose acceptance instructions**

  Require front, oblique, and active-hold captures for every canonical pose; native picking proof that the active board contact is the nearest bound mesh while the cord is ignored; and first-migration iOS review of selection snap, orbit, reset after orbit, all positions, continuity, clear/reappear highlighting, workout-driven positions, and unavailable state. Require camera-orbit verification separately from interactive detail picking.

- [ ] **Step 5: Commit**

  ```bash
  git add .codex/skills/migrate-hangboard-to-3d/SKILL.md
  git commit -m "Define suspended hangboard cord validation and interaction"
  git push
  ```

### Task 3: Preserve cost-aware routing and validate the revised skill

**Files:**
- Modify: `.codex/skills/migrate-hangboard-to-3d/SKILL.md:48-52,99`

**Interfaces:**
- Consumes: the existing Luna/Terra/Astra routing language and the two new suspended-presentation sections.
- Produces: a validated skill whose cost policy applies to portable-suspension migrations as well as wall-mounted boards.

- [ ] **Step 1: Make the routing change testable in prose**

  Amend the existing cost-routing paragraph to explicitly route suspension evidence, schema, catenary math, deterministic validation, renderer integration, tests, and review to Luna; retain Terra escalation only after a bounded Luna attempt exposes intricate non-geometry work; and reserve Astra exclusively for final physical board shape/fidelity after the approved evidence gate. State that no geometry worker may alter a board face, cord estimate, camera, or attachment solely to mask a validation failure.

- [ ] **Step 2: Run the skill validator**

  Run:

  ```bash
  rtk python3 /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/migrate-hangboard-to-3d
  ```

  Expected: success with valid frontmatter and no scaffold placeholders.

- [ ] **Step 3: Perform two forward-reading checks**

  Review the changed skill as if receiving each request below, verifying it gives an unambiguous next action without adding unsupported product claims:

  ```text
  Migrate a portable board with four source-documented usable faces and a cord visible in two manufacturer views.
  Migrate a board with an apparent cord but no trustworthy attachment-region view or sourced usable-face mapping.
  ```

  Expected: the first routes to evidence approval, one USDZ, pose metadata, deterministic cord validation, and lower-cost work before Astra; the second stops at the evidence gate and asks the human rather than inventing attachment/face facts.

- [ ] **Step 4: Scan for conflicting legacy wording**

  Run:

  ```bash
  rtk rg -n "always wall|wall-mounted|nail|live simulation|second model|raster fallback" .codex/skills/migrate-hangboard-to-3d/SKILL.md
  ```

  Expected: no instruction requires wall mounting, a visible nail, live rope dynamics, per-face models, or raster fallback for a suspended package.

- [ ] **Step 5: Commit**

  ```bash
  git add .codex/skills/migrate-hangboard-to-3d/SKILL.md
  git commit -m "Route suspended migrations by task complexity"
  git push
  ```

## Final Verification

- [ ] Run the skill validator from Task 3 after all changes.
- [ ] Re-read the `Suspended portable presentations`, export, integration, and cost-routing sections together; confirm they preserve the existing 3D-only package, source-evidence, explicit-unavailable, and Astra-evidence-gate contracts.
- [ ] Confirm `git status --short` shows only intentional changes before the final commit and push.
