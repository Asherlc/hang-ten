# Metolius Board-Specific Routines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the three official Metolius Contact and three official Metolius Simulator 3D ten-minute routines to Hang Ten without changing the already-bundled generic Metolius or Method Climbing plans.

**Architecture:** Model each source row as an official ten-minute task cycle in `LegacyPlanSeedCatalog`, targeting the exact numbered hold IDs of its matching board package. Keep task-cycle timing intact—each source minute is 60 seconds and any remaining time is source-prescribed rest—then regenerate the checked-in JSON library from the Swift fixture.

**Tech Stack:** Swift, XCTest, JSON export script, existing Hang Ten board packages.

**Spec:** User-approved bounded design in this conversation: import Contact Entry/Intermediate/Advanced and Simulator 3D Entry/Intermediate/Advanced; leave the existing Method and generic Metolius plans unchanged.

## Global Constraints

- Use only the primary Metolius sources checked 2026-08-26: <https://www.metoliusclimbing.com/pages/contact-training-guide> and <https://www.metoliusclimbing.com/pages/simulator-3d-training-guide>.
- Each source plan is board-specific and must set `boardID` to its exact Metolius board; do not translate numbered holds to another board.
- Preserve every source task, count, duration, order, stay-on/reverse/switch, rest, failure, and form qualifier; use `.official` provenance only if unchanged.
- Preserve the source’s ten 60-second task cycles, with remaining time resting until the next minute; do not manufacture a fixed work/rest split.
- Do not duplicate or modify `metolius.generic-ten-minute.*`, `method.intermediate-hangboarding.repeaters`, or `method.intermediate-hangboarding.emom`.
- Record an auditable source mapping for all six plans, regenerate `HangTen/Resources/PlanLibrary.json`, and require `scripts/export-plan-library.sh --check` to pass.
- Verify each plan resolves only for its matching board and every numbered target resolves on that board.

---

### Task 1: Import and verify the six board-specific Metolius plans

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` — add six `LegacyPlanSeedCatalog` entries and any narrowly-scoped reusable source-cycle helper needed to express their exact official tasks.
- Modify: `HangTen/Resources/PlanLibrary.json` — regenerated output only.
- Modify: `docs/source-audits/2026-08-26-metolius-board-specific-routines.md` — line-by-line source audit with URLs, check date, board classification, target-ID mapping, and every source minute/task.
- Modify: existing focused plan-library validation test file(s), only if the catalog’s existing behavioral validation does not already assert plan count, board visibility, source-cycle duration, and numbered-target resolution for the six added plans.

**Interfaces:**
- Consumes: `TrainingPlan`, `WorkoutStep`, `LegacyPlanSeedCatalog`, the established Metolius cycle modeling conventions, and registered `metolius-contact` / `metolius-simulator-3d` board hold IDs.
- Produces: six unique plans, each with `boardID`, official source metadata, ten 60-second task cycles, and hold targets resolvable on exactly its associated board.

- [ ] **Step 1: Create the source audit before implementation**

Create the audit with a separate section for Contact and Simulator 3D. For each Entry, Intermediate, and Advanced routine, enumerate source minutes 1 through 10, every task in source order, all prescribed durations and counts, the exact numbered source hold, and the matching catalog hold ID. State that source minutes use remaining time to rest. Cite the two direct Metolius URLs and check date `2026-08-26`.

- [ ] **Step 2: Write or extend a behavioral test before production changes**

Add an assertion that the plan library exposes exactly six new plan IDs—three Contact and three Simulator 3D—with: the matching board ID; `.official` provenance; ten source task cycles totaling 600 seconds; source URLs; and targets that resolve on the matching board but do not make the plan available on other boards. Name the observable failure the test catches: a plan that is cross-board, non-resolvable, missing, or has the wrong source-cycle duration. Run the focused test and capture its expected failure before adding the plans.

- [ ] **Step 3: Implement the exact official task cycles**

Add the following plan family IDs, titles, source URLs, and board IDs:

| ID | Title | Board ID | Source |
| --- | --- | --- | --- |
| `metolius.contact.entry` | `Metolius Contact · Entry` | `metolius-contact` | Contact guide |
| `metolius.contact.intermediate` | `Metolius Contact · Intermediate` | `metolius-contact` | Contact guide |
| `metolius.contact.advanced` | `Metolius Contact · Advanced` | `metolius-contact` | Contact guide |
| `metolius.simulator-3d.entry` | `Metolius Simulator 3D · Entry` | `metolius-simulator-3d` | Simulator 3D guide |
| `metolius.simulator-3d.intermediate` | `Metolius Simulator 3D · Intermediate` | `metolius-simulator-3d` | Simulator 3D guide |
| `metolius.simulator-3d.advanced` | `Metolius Simulator 3D · Advanced` | `metolius-simulator-3d` | Simulator 3D guide |

Transcribe all rows from the official guide tables into their corresponding plan. Exact source data to retain is at Contact guide minutes 1–10 and totals, and Simulator 3D guide minutes 1–10 and totals. Preserve `stay on`, `reverse holds`, `repeat other arm`, `bump`, `campus`, `without dropping off`, `till failure`, weight/helper qualification, and form qualification as source-backed instructions; omit any unsupported app coaching. Use exact numbered IDs from the existing board packages, not semantic fallback targets.

- [ ] **Step 4: Run RED/GREEN verification and regenerate the library**

Run the focused validation after implementation and require it to pass. Run `scripts/export-plan-library.sh`, then `scripts/export-plan-library.sh --check`. Run the project’s relevant full test command and build command as documented by the repository. Inspect generated JSON plan IDs, source metadata, board IDs, task-cycle duration, and representative active-hold targets for each board family.

- [ ] **Step 5: Commit the complete import**

Commit the Swift catalog, regenerated JSON, source audit, tests (if changed), and this implementation plan with a message beginning `feat:`.
