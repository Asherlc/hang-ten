# Suspended portable hangboard presentation

## Goal

Extend the 3D hangboard migration contract so a portable board with usable
faces or positions can be represented by one reusable USDZ while appearing to
hang naturally in each selected position. The first application is the Tension
Flash Board, but the capability is package-driven and available only to boards
whose source evidence supports it.

The capability is a display presentation, not a load, rope, or product-physics
simulator. It must preserve existing logical hold IDs, position resolution, and
model-only package rules. It does not add a visible nail, ceiling, pull-up bar,
or other mounting scene object.

## Confirmed decisions

- Each compatible product has exactly one board USDZ and one model descriptor.
  The USDZ contains the physical board, including a source-supported integral
  cord-attachment feature where applicable, but no display cord, nail, or
  duplicated per-face models.
- The app owns an invisible, fixed world-space anchor and renders the cord as
  presentation-only geometry. The anchor is never represented by a visible
  node, image, accessibility element, or hit target.
- A selected hold or resolved workout position smoothly resets the board to
  that position's canonical pose. This intentionally overrides a prior manual
  inspection view.
- Manual inspection orbits the camera around the stable suspended scene. It
  does not rotate the board independently, because that would make a fixed
  cord appear to pass through or detach from the product.
- Cord geometry is static and deterministic, not live simulation. It is
  recomputed when the canonical board pose changes.
- Every physical attachment fact, logical position, and hold availability is
  source-backed. Model coordinates, display pose values, anchor placement,
  cord length, and camera/framing values are explicitly recorded as authored
  display estimates unless direct evidence establishes them.

## Architecture

The package remains model-only. Its `board.json` owns the product identity,
logical holds, model presentation, physical positions, transitions, and a new
optional suspended-presentation declaration. The USDZ and its generated
descriptor continue to be the sole source for board rendering, highlight
meshes, picking, and display-derived hold matching. The app adds a transient
presentation layer above that validated model:

```text
board.json position + suspended metadata + model descriptor
  -> resolve selected hold / workout position
  -> canonical board transform in world space
  -> transform local cord attachment into world space
  -> derive static cord curve from invisible anchor to attachment
  -> render one board USDZ + non-pickable cord + orbit camera
```

There is no separate USDZ, mesh binding, logical inventory, or raster path for
another face. A logical hold remains one physical contact. Positions identify
the athlete-usable configuration and choose a canonical display pose; they do
not create new holds or copy model geometry.

## Package contract

`media.type: "model"` gains an optional `suspension` presentation capability.
The following declaration is the schema contract for the implementation.

```json
{
  "suspension": {
    "type": "singleCord",
    "attachment": {
      "nodeID": "Board/CordAttachment",
      "pointInModel": [0.0, 0.032, 0.014],
      "provenance": "estimatedFromApprovedModel"
    },
    "anchor": {
      "offsetFromBoardBounds": [0.0, 0.22, 0.0],
      "visibility": "invisible",
      "provenance": "displayEstimate"
    },
    "cord": {
      "restLength": 0.24,
      "radius": 0.002,
      "material": "matteCord",
      "provenance": "displayEstimate"
    },
    "canonicalPoses": {
      "front": {
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "translation": [0.0, 0.0, 0.0],
        "camera": { "viewDirection": [0.0, 0.0, -1.0], "fitPadding": 0.1 }
      }
    }
  }
}
```

`attachment.nodeID` must identify a validated importer-visible node in the
hash-bound descriptor. Its local point is expressed in the descriptor's board
coordinate frame. It may reference a body node or a distinct nonselectable
attachment feature, but may not reference a logical hold node merely for
convenience. The presentation layer transforms that one point with the chosen
canonical board pose; it must never alter the board USDZ to manufacture an
attachment location.

Each `canonicalPoses` entry is keyed by an explicit package `positionID`.
Every suspended position has exactly one pose and no unknown position may have
a pose. Rotation is a finite, normalized quaternion and translation is finite.
The camera values are presentation-only and remain independent of physical
metadata. Position suitability and transitions continue to use the existing
source-audited position contract; a pose does not itself assert that a user can
make a transition during an authored rest.

The schema must not silently give a conventional wall-mounted package a
suspension. A model without `suspension` retains existing model behavior.
Suspended media cannot declare a raster fallback, a second model path, baked
cord nodes, visible anchor nodes, or hand-authored hold bounds.

## Static cord behavior

For a selected canonical pose, the renderer creates a fresh non-pickable cord
from the invisible anchor to the transformed attachment point. It uses a
deterministic static hanging-curve solve in the gravity plane: a uniform cord
with the declared endpoint separation and rest length follows a catenary when
slack is available; a straight taut segment is used only at the physical
minimum length within declared numerical tolerance. The solver samples the
same curve and material parameters on every supported platform so screenshots
and tests are repeatable.

The board's canonical rigid pose is an authored presentation orientation, not
a claim that a freely rotating one-point suspension would settle there under
all real loads. The catenary shows how the cord would hang between the fixed
anchor and the board's actual attachment point; it does not claim to calculate
user forces, friction, knot behavior, elastic stretch, or dynamic swing.

If the declared rest length is shorter than endpoint separation, the package is
invalid. If a curve cannot be solved with finite values, positive length and
radius, continuity at both endpoints, and the required clearance, the affected
presentation is unavailable rather than falling back to an implausible line or
an alternate board model.

The cord is continuous at the attachment and anchor, with tangents consistent
with the solved curve. It has no separate selectable mesh, no accessibility
element, and cannot obscure a hold pick: board picking continues to use only
the descriptor-bound USDZ meshes.

## Runtime interaction

Hold selection and workout resolution select a `positionID` before presenting
the model. The renderer interpolates the board from its current canonical pose
to the newly selected pose over a short, fixed presentation transition, then
recomputes the cord at the destination pose. It may animate the cord along the
same deterministic samples during that transition, but must end exactly at the
destination solve. Selecting another hold always restores that hold's
position's canonical pose, even after manual inspection.

Manual gestures alter only orbit camera azimuth, elevation, and allowed zoom
around the suspended board-and-cord scene. The board transform, invisible
anchor, and solved cord remain fixed. On release the camera stays at the
chosen inspection view; the next position/hold selection resets the canonical
board pose and its canonical camera framing with a short smooth transition.
The camera must keep the active hold and its cord attachment legible without
changing the source-derived identity of the active position.

An invalid position, descriptor, attachment node, or solve displays the
existing explicit model-unavailable state. It must not use raster rendering,
an incorrect face, a detached cord, or a visible stand-in for the anchor.

## Evidence and authoring requirements

The existing multi-angle gate applies before final geometry. For portable
suspended products, the retained evidence packet additionally records:

- the exact revision and each usable physical face/position;
- the manufacturer evidence that identifies the cord or attachment method,
  attachment feature, and any supplied cord dimensions/material claims;
- at least two materially distinct exact-revision visual snapshots, including
  a view sufficient to assess the attachment region when one exists;
- a position-to-logical-hold mapping and the evidence supporting each mapping;
- clear separation between sourced facts and estimates for model attachment
  coordinates, attachment depth, canonical poses, anchor offset, cord length,
  cord radius, material treatment, and camera settings; and
- deliberate display simplifications, including invisible anchor and omitted
  surrounding mounting environment.

Evidence may establish that the product hangs by a cord, but it does not
license invented exact cord dimensions or knot geometry. Unsupported values
remain labeled display estimates. Lower-cost workers collect and structure
the evidence; Astra receives the approved images and may only author or refine
the physical board shape. No worker traces, segments, vectorizes, or otherwise
derives board geometry from pixels.

## Validation and acceptance

Validation extends the model-package checks without weakening any existing
asset, descriptor, material, mesh-binding, and picking rules.

Package/schema tests must reject unknown or duplicate pose keys, omitted poses
for declared suspended positions, nonfinite transforms, nonunit quaternions,
unknown attachment nodes, attachment points outside the declared coordinate
frame contract, nonpositive cord dimensions, and a rest length shorter than
the attachment-anchor separation for a canonical pose. They must also reject
baked cord/anchor geometry declared as logical hold geometry or a second model
as an orientation substitute.

For every canonical pose, deterministic geometry validation must prove:

1. the cord begins at the fixed invisible anchor and ends exactly at the
   transformed physical attachment point;
2. the sampled curve is continuous, finite, has the declared or solved length,
   and does not self-intersect;
3. the cord tube remains outside the board mesh by at least its radius plus a
   declared clearance, except at the approved attachment interface;
4. the active face's complete selectable inventory is reachable through the
   existing nearest-triangle model picking; the cord never becomes a nearer
   hit; and
5. canonical camera framing contains the active hold, the attachment, and the
   necessary visible cord segment without clipping or concealing the active
   contact.

The validator uses mesh intersections and camera-space checks, not a visual
mask. Front, oblique, and active-hold review captures are retained for each
canonical pose. Human review confirms that the board face, attachment,
suspension silhouette, active highlight, and camera orbit are credible against
the approved evidence. This visual approval remains required even when all
deterministic checks pass.

The first implementation additionally needs iOS simulator review covering
selection snap, manual camera orbit, selection reset after orbit, every
position, cord continuity, active/cleared highlighting, inaccessible-model
state, and workout-driven position selection. Native picking tests must prove
the board remains interactive while the cord is ignored.

## Cost-aware delivery policy

Luna is the default model for source-packet synthesis, package/schema work,
cord mathematics, deterministic validation, tests, documentation, routine
integration, and review. Terra is used only for intricate non-geometry schema,
tooling, renderer, or cross-platform integration work, or after a bounded
Luna attempt fails verification and the unresolved issue is no longer routine.
Astra is reserved exclusively for final physical board geometry, difficult
fidelity judgment, and corrections to the board's physical shape after the
approved multi-angle evidence gate. Astra does not own cord math, schema,
tools, package conversion, renderer integration, or validation.

The first Flash Board migration is the reference acceptance case; it must not
gain board-specific renderer routing. Subsequent compatible portable boards
reuse the same one-model suspended-presentation capability by supplying their
own evidence-backed package data and passing the per-pose validation contract.

## Out of scope

- live rope dynamics, swinging, collisions, load calculation, knot simulation,
  user-force estimation, and safety certification;
- visible nails, hooks, pull-up bars, walls, ceilings, or mounting scenery;
- duplicated USDZs or raster presentations for board orientations;
- turning estimated presentation values into product measurements; and
- inferring unsupported face, transition, attachment, or training claims.
