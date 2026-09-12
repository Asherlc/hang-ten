# Rotatable 3D Board Orientations Design

## Problem and outcome

The model migration changed a five-surface YY Baguette Evo into one front-facing
USDZ presentation. The current renderer only changes a model's pose when full
suspension metadata is present. Baguette cannot truthfully provide a cord route,
cord length, anchor, and hanging poses, so suspension is the wrong abstraction.

This design adds a generic, metadata-driven orientation layer to the shared 3D
board renderer. A logical position identifies the usable holds and, for a model
presentation, may identify a canonical rotation. The rotation is applied about
the model-bounds center (the only supported pivot in this version), framing is
recomputed from the rotated bounds, and the user may still orbit manually. A
model may have either orientation metadata or suspension metadata, never both.
Fixed/front-only models remain unchanged and do not acquire unnecessary pose
metadata.

The solution applies to every 3D package; it must not contain board-ID
conditionals. The known regression is Baguette, not a special runtime case.

## Scope and inventory

The shared Swift package loader and `BoardModelScene` are authoritative for iOS.
The Android decoder is a live schema consumer even though it currently marks
model media unavailable; its schema handling must be updated in the same change
or explicitly retain a strict, documented unsupported-model result. It must not
silently interpret orientation fields as raster data.

The migration audit covers every model package currently in `Hangboards`:

| Package | Model | Required disposition |
| --- | --- | --- |
| `beastmaker-1000` | `primary.usdz` | fixed/front-only; retain the canonical front path |
| `nature-stone-hanger` | `primary.usdz` | orientation metadata for the documented front and reverse usable faces |
| `metolius-wood-grips-compact-ii` | `primary.usdz` | fixed/front-only; retain the canonical front path |
| `yy-baguette-evo` | `primary.usdz` | perform a deliberate contact-orientation audit and backfill every reviewed orientation grouping |

The inventory test discovers model media rather than maintaining this list in
runtime code. A package with multiple physical usable orientations must have a
position for each such orientation and a rotation for each position. Contacts
that the audit proves share the same reviewed quaternion may be grouped in one
position; the five old raster surfaces must not be treated as five positions
without that review. A genuinely fixed/front-only model has one canonical position and no rotation object. The
audit records the evidence URL or retained manufacturer artifact, model bounds,
the position-to-hold mapping, and the author of every display estimate.

## Data model

`BoardPosition` gains an ordered hold association. The JSON member is optional
for backward decoding, but the loaded model always materializes an array:

```swift
struct BoardPosition: Identifiable, Codable, Hashable {
    let id: String
    let presentationID: String
    let holdIDs: [String]
}
```

`holdIDs` is the complete logical inventory preferred for that physical
position, not a hint for rendering. For a model presentation, the position
arrays form an exact partition of the descriptor hold inventory: every model
hold ID occurs in exactly one position, no position contains an unknown or
duplicate ID, and the union equals the descriptor's hold IDs. This makes a
position selection deterministic while still recording which contacts belong
to each reviewed orientation. IDs are unique, non-empty board identifiers and
are ordered in canonical board hold order. Existing decoded positions without the
field receive the presentation's complete logical hold inventory, preserving
old behavior. New authored model positions must provide the field and must not
be empty; a position with no usable logical holds is rejected by package
validation.

Model media gains an optional orientation block. The block is deliberately
separate from `suspension`:

```json
"orientation": {
  "pivot": "modelBoundsCenter",
  "rotations": {
    "position-front": [0.0, 0.0, 0.0, 1.0],
    "position-reverse": [0.0, 1.0, 0.0, 0.0]
  }
}
```

`rotations` maps position IDs to unit quaternions in the descriptor's
`hang-ten-board-v1` coordinate frame, in `[x, y, z, w]` order. A quaternion is
the canonical representation; authoring tools may display equivalent Euler
angles, but JSON stores one normalized quaternion. `pivot` is required and must
be `modelBoundsCenter`; arbitrary node or world pivots are rejected. Rotation
metadata is display metadata, not geometry or evidence of a physical mounting
mechanism.

For Baguette, each quaternion is an authored display estimate derived by
deliberate inspection of retained manufacturer evidence and the existing model
geometry. The package audit labels it exactly as an “authored display estimate”
and links the evidence used. It must not claim that the manufacturer published
the angle, and it must not add, regenerate, crop, segment, vectorize, simplify,
or otherwise edit model geometry or assets.

## Canonical JSON contract

The schema remains version 2. Add the following optional key to a model media
object; unknown keys continue to be rejected:

```json
{
  "type": "model",
  "assetPath": "assets/primary.usdz",
  "descriptorPath": "assets/primary.model.json",
  "display": {"camera": {"type": "orthographic", "viewDirection": [0,0,-1], "up": [0,1,0], "fitPadding": 0.08}},
  "orientation": {
    "pivot": "modelBoundsCenter",
    "rotations": {
      "front": [0, 0, 0, 1],
      "reverse": [0, 1, 0, 0]
    }
  }
}
```

Canonical serialization is deterministic: root object keys use the existing
schema order; `positions` retain authored array order; each `holdIDs` array is
canonical hold order; and `orientation.rotations` object members are sorted by
position ID. Numeric components are finite and rounded to nine decimal places.
There is no v2 model serializer in this change; canonical ordering and
numeric normalization apply to hand-authored v2 JSON and validator behavior.

Strict validation must reject:

* an orientation on raster media, a missing/incorrect pivot, unknown keys,
  unknown or duplicate position IDs, or a rotation map with missing or extra
  position IDs;
* a position with duplicate/unknown hold IDs, a presentation mismatch, or a
  model position whose `holdIDs` partition is not exact (missing, repeated, or
  extra model hold IDs);
* non-finite or non-nine-decimal quaternion components, a zero quaternion, or
  a quaternion whose norm differs from one beyond the existing descriptor
  tolerance;
* both `orientation` and `suspension` on one model media object; and
* orientation metadata on a model with no declared multiple physical
  positions. A fixed model uses the legacy canonical front path instead.

The loader reports the existing `invalidPackage(boardID:reason:)` error with a
field-specific reason. It never falls back to a different presentation,
borrows hold mappings, infers a rotation from mesh normals, or displays a
partially valid orientation map. A malformed package is unavailable as a whole.

## Runtime data flow

1. `BoardPackageStore` decodes positions and model orientation after descriptor
   hash, bounds, node inventory, and hold inventory validation. It constructs a
   `BoardModelOrientation` value containing the pivot and position map.
2. `BoardModelScene` receives that value alongside `BoardModelDescriptor` and
   the existing display camera. It selects a position using the existing
   position-selection path, resolving the position's `presentationID` and
   `holdIDs` before applying media state.
3. For orientation media, it computes the quaternion transform about
   `(modelBounds.minimum + modelBounds.maximum) / 2`. The transform is applied
   to the shared board container, not individual hold nodes. It computes the
   transformed model bounds, derives a new orthographic framing, and animates
   the canonical change with the existing transition duration.
4. Canonical selection resets the canonical camera/orbit accumulator for that
   transition, then the next gesture starts from the newly framed model.
   `orbit(azimuth:elevation:zoomScale:)` remains enabled for all model detail
   and workout surfaces, whether orientation, suspension, or fixed media is in
   use. Orbit acts on the camera around the framed target and never overwrites
   canonical metadata.
5. A display-only preview that currently suppresses gestures uses the same
   canonical selection and framing but remains non-interactive by its existing
   policy. Any surface that advertises 3D interaction must forward orbit and
   reset gestures; preview hit-testing must not accidentally disable gestures
   on detail or workout views.

For suspension media, the existing solver and canonical pose/camera path is
unchanged. Orientation media has no cord, attachment, anchor, clearance, or
transient-cord state. The two paths are mutually exclusive in both decoded
types and runtime initialization.

## Backward compatibility and migration

Schema-v1 raster packages and schema-v2 raster packages are unchanged. Schema-v2
model packages without `orientation` continue to render their existing front
camera. Model packages with `suspension` continue to use suspension poses.
Existing callers constructing `BoardPosition(id:presentationID:)` retain a
compatibility initializer that supplies an empty association; package loading
materializes the complete legacy inventory before validation.

The migration updates only board JSON metadata and, if required, the shared
decoders/models. It does not change USDZ bytes or descriptor geometry. For every
current 3D package, the audit classifies it as fixed/front-only or multi-
orientation and records the exact position order, hold IDs, pivot, quaternion,
and provenance. Baguette's legacy surfaces are represented by reviewed logical
positions sharing the one model; each reviewed orientation grouping names its
preferred hold IDs. The number of positions is determined by the reviewed
quaternion grouping, not by the number of legacy raster surfaces.

## Alternatives considered

Runtime mesh-normal inference is rejected. It is unstable across imported node
hierarchies, cannot distinguish an intended contact face from decorative
geometry, violates the direct authoring rule, and produces no auditable source
or provenance.

Duplicated model presentations are rejected. They duplicate USDZ assets and
descriptor inventories, recreate the original five-surface collapse risk, make
hold identity drift likely, and cannot preserve one shared interactive model.
Metadata keeps one source of geometry while making the deliberate display
choice reviewable.

## Test plan (RED then GREEN)

Write failing tests before implementation, then make each pass with the
smallest change:

1. Swift package decoder tests cover legacy positions, valid orientation JSON,
   sorted canonical output, pivot/quaternion validation, unknown and incomplete
   rotation maps, duplicate/unknown hold IDs, non-partitioned hold IDs, and
   orientation+suspension rejection. Assert the exact `invalidPackage` reason
   category.
2. Swift model-scene tests use a non-centered descriptor and prove a canonical
   quaternion rotates around model-bounds center, recomputes framing, preserves
   hold node bindings, and leaves manual orbit functional after selection.
   Suspension tests prove the old solver remains selected and orientation tests
   prove no cord is created.
3. A package inventory test discovers every `Hangboards/**/board.json` with
   model media, loads it through the real package validator, and asserts that
   every multi-orientation package has a complete position/hold/rotation
   matrix while every fixed/front-only package has no orientation block. This
   catches omissions when a new model package is added.
4. Android repository tests cover the shared JSON contract and assert that model
   packages either decode the same orientation fields or produce the explicit
   existing unavailable-model result without accepting malformed metadata. No
   Android board-ID exception is permitted.
5. Run the package compiler/validator and the focused Swift and Android tests,
   then the full relevant test suites. The RED run must demonstrate each new
   assertion fails against the pre-change behavior; the GREEN run must show all
   pass.

## Provenance, audit, and visual acceptance

The package audit cites the direct manufacturer pages and retained evidence
already used for each board, including the YY Vertical Baguette Evo product
evidence (`https://www.yyvertical.com/en/products/baguette-evo`) and the existing
model-package audit at `docs/source-audits/2026-09-10-imported-model-packages.md`.
Every hold association is traceable to that evidence or to the model descriptor
inventory; every Baguette quaternion is explicitly labeled an authored display
estimate, and the audit records why contacts were grouped or separated.
Unsupported claims are omitted.

Use the Hang Ten iOS simulator validation route in landscape for each current
3D package. Capture front and every canonical position, verify every expected
hold is visible and selectable, rotate manually, reset, switch positions, and
confirm framing remains within the viewport. Validate both detail and workout
surfaces, plus the display-only preview's intentional gesture policy. A failed
load must show the existing unavailable state, never a raster fallback.

The Nature Stone Hanger 3D card renders blank under the synthetic landscape
review flag (a programmatic `requestGeometryUpdate(.landscapeRight)` with the
device physically in portrait). The identical scene state renders correctly in
portrait, and the shared renderer proves itself on all other boards in the
same harness. The scene graph state is verified correct via live debugger
inspection (non-zero size, valid scene/geometry/lights/camera, zero errors).
This is a harness presentation edge, not a package defect. A physical-device
landscape rotation check is required before marking this validation fully
complete.

All simulator screenshots, temporary build products, and validation logs live
under `.context/<workspace-owner>/`. Before completion, install an exit trap
that stops and deletes only resources owned by this worktree, verify deletion,
and leave shared or unknown resources untouched.

## Acceptance criteria

The change is complete when the strict cross-language schema and real package
inventory tests pass; all current model packages have an audited disposition;
Baguette renders all logical holds through reviewed metadata-selected positions
from one unchanged model;
fixed boards remain on the legacy path; suspension behavior is unchanged;
manual orbit works on every interactive 3D surface; malformed or conflicting
metadata fails closed; provenance contains no invented source claims; and iOS
visual validation has reviewed every canonical orientation.
