# Unilateral portable training design

## Purpose

Make unilateral hangs, force pulls, and loaded lifting-edge work first-class
Hang Ten workouts. The data must represent physical equipment truthfully while
keeping that normalization invisible to athletes.

## Scope

This change covers board-package identity, workout semantics, custom-routine
authoring, execution/highlighting, sensor capture, and workout history. It adds
the Frictitious Port-A-Board as a single-object package and corrects the Rock
Rings model to identify its two independently usable physical objects. It also
adds source-audited built-in examples only where the source supplies every
displayed prescription.

It does not add bodyweight profiles, PR analytics, estimated 1RM calculations,
or user-managed equipment inventories.

## Equipment model

Every `TrainingBoard` has one or more internal `EquipmentObject`s. An object
has a stable identifier and owns its physical holds. Every `BoardHold` declares
one `equipmentObjectID`.

Package `equipmentObjects` is the source-of-truth inventory. Existing
single-piece boards migrate to an explicit sole object with ID `primary`.
Rock Rings 3D declares `left-ring` and `right-ring`; each existing left/right
hold belongs to its matching ring. The default presentation continues to show
both rings together. The Frictitious Port-A-Board declares only `primary`.

Presentations remain visual-only. They cannot create, combine, or remove
physical objects. Package validation rejects missing object IDs, orphaned
objects, duplicate object IDs, and holds referring to unknown objects.

## Workout semantics

Each non-rest step carries two new source-serializable fields:

- `handUse`: `single` or `double`, defaulting to `double` when absent.
- `action`: `hang`, `isometricPull`, or `loadedLift`, defaulting to `hang`
  when absent.

`handUse` describes how the athlete uses the hold, not the product. The step
also carries an optional side cue (`left`, `right`, `both`); it is mandatory for
single-hand steps and must be `both` for double-hand steps. A `loadedLift` can
declare repetitions and an optional signed external load; positive load is
added weight and negative load is assistance. The run session records the
selected load alongside the step measurement.

Timed hangs and isometric pulls keep the existing work/rest timer. A loaded
lift is an explicit repetition action: the runner counts completed reps, while
the rest timer runs between prescribed reps/sets. No text instruction is used
as a substitute for these fields.

## Resolution and user experience

The athlete never configures equipment objects. They choose familiar workout
details: one hand or two hands, and left or right where relevant.

For a single-hand target, the resolver chooses one compatible object and its
hold. For a double-hand target, it either chooses two compatible distinct
objects (such as the two Rock Rings) or a documented hold with
`handCapacity: 2`. It must never satisfy a double-hand target with two holds
from one single-hand object, or a single-hand target by highlighting the whole
paired product.

The board screen retains the product presentation. During a unilateral step it
highlights just the selected ring/object; during a bilateral Rock Rings step it
highlights both. The runner displays the action, hand use, side, prescribed
repetitions when present, and external load entry. Tindeq remains an optional
sensor: its force samples are attributed to the active structured step and
recorded as its peak load.

## Built-in source-backed examples

Add only programs whose displayed work/rest/repetition structure is traceable:

- Alex Megos one-arm 7:3 repeaters: four 7-second work / 3-second rest cycles
  on each side, two minutes between sets, six sets.
- Tyler Nelson force-measured recruitment pulls: three to five 3–5 second
  maximal pulls per finger position with 60–120 seconds rest. The app will use
  the source's stated range only when the source field supports range display;
  otherwise this remains a custom-routine template rather than fabricated
  exact steps.
- One-arm 20 mm lifting-edge strength: 70–80% of 1RM, three sets of seven
  lifts, two to three days per week. The app will preserve the source's
  percentage range and avoid calculating 1RM from bodyweight.

Each plan has its original URL and a field-to-source mapping in a source audit.
The Frictitious Port-A-Board contributes physical inventory and supported
setup modes only; its currently discoverable material does not provide a full
program and will not be represented as one.

## Compatibility and validation

All new fields decode absent values to preserve saved custom routines, bundled
plans, board packages, and workout history. Encoders emit the fields for newly
saved records. Existing steps resolve as two-handed hangs on the board's sole
object or existing documented bilateral contacts.

Tests cover JSON/package decoding, package invariants, existing-board
migration, Rock Rings single/double resolution, Port-A-Board single-object
resolution, custom-routine validation, timer/rep runner state, Tindeq sample
attribution, and history round trips. Package validation and the iOS simulator
build/run verify default, unilateral, and bilateral highlighting.

## Sources

- [Frictitious Port-A-Board](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard)
- [Metolius Rock Rings 3D](https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d)
- [Megos/Hörst one-arm 7:3 repeaters](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/)
- [Tyler Nelson recruitment pulls](https://www.trainingbeta.com/media/tyler-nelson-fingers/)
- [One-arm 20 mm lifting-edge program](https://www.climbing.com/skills/crimp-strength-training-safely/)
