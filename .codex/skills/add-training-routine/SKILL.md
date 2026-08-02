---
name: add-training-routine
description: Import or audit a manufacturer hangboard routine in Hang Ten while preserving exact tasks, order, repetitions, times, interval structure, provenance, and board compatibility. Use for new routines, source verification, generic-versus-board-specific classification, or routine hold-target corrections.
---

# Add a training routine

Read `docs/ADDING_A_ROUTINE.md` completely before changing files. Treat the
manufacturer's primary source as the prescription and the board catalog as a
separate semantic-resolution layer.

## Workflow

1. Find the current official manufacturer guide or manual and record its direct
   URL and check date.
2. Classify the routine as board-flexible or board-specific before modeling it.
3. Create a line-by-line source audit covering every task, count, duration,
   order, switch, stay-on, maximum/failure, and rest instruction.
4. Add `TrainingPlan` and `WorkoutStep` data without inventing segments or
   exercises. Mark provenance honestly.
5. Target exact board IDs for numbered routines and the narrowest truthful
   `HoldFeature` for board-flexible routines.
6. Regenerate `HangTen/Resources/PlanLibrary.json` with
   `scripts/export-plan-library.sh`, then run the script again with `--check`.
7. Verify every target resolves on every board where the plan appears.
8. Preview representative text, timer, audio, hand cue, and active-hold states
   in the dedicated simulator.

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
