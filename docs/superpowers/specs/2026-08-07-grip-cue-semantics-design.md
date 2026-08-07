# Grip cue semantics design

Date: 2026-08-07
Status: Approved by the user

## Problem

`GripType` currently combines hand posture with hold-specific information. A
sloper and a pocket are hold targets, not hand postures. Pocket variants also
implicitly choose a particular pair or trio of fingers, which is too specific:
a hold can constrain how many fingers fit without prescribing which fingers the
athlete uses.

## Goals

- Represent hand posture independently from the physical hold.
- Represent a hold's finger capacity without selecting individual fingers.
- Support an exact finger selection when a routine explicitly prescribes one.
- Keep pocket/sloper terminology in hold kinds, features, targets, and hold
  labels.
- Keep existing bundled plans and saved custom routines readable.
- Make the rendered cue derive posture and finger information from the new
  fields rather than from `BoardHold.kind`.

## Domain model

`GripType` contains only postures:

- `openHand`
- `halfCrimp`
- `fullCrimp`

`FingerSlot` remains the four individual fingers: index, middle, ring, and
pinky. It becomes codable so it can participate in persisted exact cues.

`FingerConfiguration` is a small codable, hashable value containing an exact
non-empty set of `FingerSlot` values. It can represent one arbitrary finger,
any combination, or all four fingers. It is used by workout-step metadata, not
by board metadata.

`BoardHold` gains a finger-capacity value constrained to the board's physical
range (one through four). The board declares how many fingers can fit, but no
individual finger set. Existing board metadata maps two-, three-, and
four-finger pockets to capacities 2, 3, and 4; jugs, slopers, and edges use the
appropriate four-finger capacity unless a hold declares otherwise.

`WorkoutStep`, `WorkoutStepDefinition`, `MetoliusTaskDefinition`, and custom
routine drafts gain an optional `FingerConfiguration`. Posture and exact
finger selection are independently optional. The cue resolves each field in
this order:

1. explicit workout-step value;
2. selected hold metadata for posture or capacity;
3. no cue when neither source has information.

When only a board capacity is available, the UI reports the number available
without highlighting or naming particular fingers. When an exact
`FingerConfiguration` is present, the UI highlights and labels those individual
fingers.

## Persistence and migration

`WorkoutStepDefinition` persists the optional exact configuration as a new
optional field. New output contains only the posture values and the exact
finger vocabulary. The existing plan schema version remains valid because the
new field is optional and the decoder already owns compatibility normalization.

The decoder accepts the old combined values:

- `sloper` → `openHand` posture, no exact finger configuration;
- `twoFingerPocket`, `threeFingerPocket`, and `fourFingerPocket` → `openHand`
  posture, no exact finger configuration, with the resolved hold supplying its
  capacity;
- `openHand`, `halfCrimp`, and `fullCrimp` retain their posture meaning.

The bundled source fixture and regenerated `PlanLibrary.json` use the new
posture values. Existing custom routine data remains loadable and is encoded
back using the new vocabulary after it is saved.

## UI behavior

Grip pose glyphs come only from `GripType`: palm for open hand, grabbing hand
for half crimp, and fist for full crimp. Finger cues no longer inspect hold
kind. Capacity-only cues show a count without choosing a finger; exact cues
show the individual engaged fingers, including single-finger and arbitrary
combination cases. The hold name and hold-kind language remain in the separate
hold-target label.

The custom routine editor exposes posture independently from an optional exact
finger selection. Leaving the finger selection unset preserves capacity-only
fallback behavior.

## Verification

Tests will cover:

- posture labels and exact arbitrary finger configurations;
- board capacities without a prescribed finger set;
- legacy combined-value decoding and new-value re-encoding;
- propagation through plan resolution, custom routines, and compound-step
  normalization;
- regenerated plan-library freshness via the existing exporter check.

The iOS simulator validation flow will inspect portrait and landscape cues,
including capacity-only, multi-finger, and one-finger review routes, plus their
accessibility labels.
