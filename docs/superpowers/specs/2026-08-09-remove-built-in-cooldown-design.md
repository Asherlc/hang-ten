# Remove Built-in Cooldown Steps

## Goal

Built-in Hang Ten training plans should not include an explicit final cooldown
timer step. The app should continue to include progressive warm-ups and all
recovery intervals that occur between efforts, sets, or grips.

## Scope

- Remove creation of the final `coolDownStep` from every built-in routine in
  `LegacyPlanSeedCatalog`.
- Remove or bypass built-in plan-library export logic that creates a shared
  cooldown block from those steps.
- Regenerate `HangTen/Resources/PlanLibrary.json` so the bundled resource
  matches the source definitions.
- Keep the `.coolDown` phase in the model and decoding paths so previously
  persisted or externally supplied data remains readable.
- Add regression coverage that built-in plans do not end with a cooldown step
  and that representative recovery intervals retain their existing durations.

## Design

The source seed catalog remains the single source of truth for built-in plan
steps. The explicit cooldown factory and its call sites are removed from the
seed definitions. The plan-library builder no longer needs to discover or
reference a shared cooldown block for generated built-in plans. Existing model
support for the cooldown phase is retained for compatibility, rather than
changing the schema or filtering arbitrary custom plans at runtime.

The generated JSON resource is refreshed with the repository's existing
`scripts/export-plan-library.sh` workflow. No UI-specific filtering is added;
the workout flow naturally presents the final real training/recovery step.

## Verification

- Run the focused plan-storage tests, including the new no-cooldown regression
  test.
- Run the repository's plan-library export/check script to confirm the JSON is
  current.
- Run the full Hang Ten test suite or the repository-supported Xcode test
  command when available.

## Non-goals

- Do not remove warm-up steps.
- Do not remove or shorten between-set, between-grip, or intra-set recovery.
- Do not remove the `WorkoutPhase.coolDown` enum or invalidate older stored
  plans that contain it.
- Do not redesign the workout summary or recovery messaging beyond what is
  required by the absence of a final cooldown step.
