---
name: add-training-routine
description: Use when adding or auditing a manufacturer hangboard routine in Hang Ten, verifying source prescriptions, classifying board compatibility, or correcting routine hold targets.
---

# Add a training routine

Read `docs/ADDING_A_ROUTINE.md` completely before changing files. Treat the
manufacturer's primary source as the prescription and the board catalog as a
separate factual inventory.

## Workflow

1. Find the current official manufacturer guide or manual and record its direct
   URL and check date.
2. Classify the routine as board-flexible or board-specific before modeling it.
3. Create a line-by-line source audit covering every task, count, duration,
   order, switch, stay-on, maximum/failure, and rest instruction.
4. Add `TrainingPlan` and `WorkoutStep` data without inventing segments or
   exercises. Mark provenance honestly.
5. Target the narrowest truthful semantic `ContactRequirement` predicate;
   never embed board contact IDs or visual references in a routine.
6. Generate board assets before running the plan exporter, which stages board
   metadata from each flat `Hangboards/<slug>.FCStd` document's
   `HangTenBoardManifest` and validated generated suspension. Cord/simulation
   inputs remain embedded CAD data; their generated artifacts do not establish
   training prescriptions. Regenerate `HangTen/Resources/PlanLibrary.json` with
   `rtk scripts/export-plan-library.sh`, then run it with `--check`.
   This JSON is an ignored build output; commit the audited Swift definitions
   and source mappings. CI generates the same library from those definitions.
7. Verify each factual requirement remains compatible with every board where
   the plan appears. Keep source-generic work as explicit athlete self-selection.
8. Preview representative text, timer, audio, hand cue, and active-hold states
   in the dedicated simulator after `rtk proxy bash scripts/build-runtime-assets.sh`.

## Non-negotiable rules

- Do not use a retailer, blog, or memory when a primary source exists.
- Do not translate a numbered board-specific routine to another board and call
  it official.
- Do not add or remove warm-ups, cooldowns, tasks, repetitions, times, or rest
  periods under `.official` provenance.
- For manufacturer task cycles, do not turn the first numeric hang into a fixed
  work/rest split when later tasks remain in the same cycle.
- If sources conflict or a target cannot resolve truthfully, report it instead
  of guessing.
