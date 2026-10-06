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
4. Add plan and block data directly to the canonical
   `HangTen/Resources/PlanLibrary.json` without inventing segments or exercises.
   Mark provenance honestly and commit the JSON with its source mappings.
5. Target the narrowest truthful semantic `PlanContactPredicate` for each hand;
   never embed board contact IDs or visual references in a routine.
6. Generate board assets before validating factual board compatibility. Board
   metadata comes from each flat `Hangboards/<slug>.FCStd` document's
   `HangTenBoardManifest` and validated generated suspension. Cord/simulation
   inputs remain embedded CAD data; their generated artifacts do not establish
   training prescriptions. Run `rtk proxy bash scripts/build-board-assets.sh`
   and `rtk scripts/validate-plan-work-targets.sh`, then run the plan tests.
   Both apps bundle the checked-in canonical JSON; there is no Swift plan
   authoring catalog or exporter.
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
