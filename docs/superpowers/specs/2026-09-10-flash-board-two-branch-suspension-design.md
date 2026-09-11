# Tension Flash Board two-branch suspended presentation

## Goal

Replace the Flash Board's provisional single-attachment suspension with a
source-aware two-branch presentation that matches the newly supplied closeups.
The board remains one reusable USDZ whose canonical poses expose its existing
faces and positions. The renderer adds two continuous, deterministic cord
branches through the board's physical end passages and makes both branches
converge at one invisible fixed overhead display anchor.

This is a display contract, not manufacturing CAD, a rope simulator, a load
calculation, or a claim that the estimated display dimensions are product
measurements. The implementation must not add a visible nail, carabiner,
ceiling, wall, stand, or other environment.

## Evidence and decisions

The exact approved logical inventory remains seven IDs, in the existing
package order:

```text
three-edge-left
three-edge-center
three-edge-right
two-edge-left
two-edge-right
small-crimp-left
small-crimp-right
```

The three-well face maps to the three `three-edge-*` contacts; the two-well
face maps to the two `two-edge-*` contacts. The two small crimps remain the
extreme outboard contacts. Existing positions and their source-backed
availability are preserved. No new logical ID is introduced by this design.

The approved evidence packet contains the following sources:

| Source | Tier | Supports | Limitations |
| --- | --- | --- | --- |
| [Tension Flash Board product page](https://tensionclimbing.com/products/flash-board-2) | Manufacturer / primary | Product identity, compact cylindrical board, portable cord suspension, two-well face, and global categories including Small Crimps and 8/10/15/20 mm | Does not publish a per-face/count map, attachment coordinates, cord dimensions, knot details, or canonical display poses |
| [Backcountry Flash Board listing](https://www.backcountry.com/tension-flash-board) | Commerce-gap | Hanging configuration and paired end-cord passage context | Retailer evidence; does not establish manufacturer-authoritative dimensions, knot geometry, attachment coordinates, poses, or material specifications |
| [Amazon Flash Board listing](https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G) | Commerce-gap | Annotated three-well face map: outboard small crimps; upper 15 mm tapered / 20 mm tapered / 15 mm tapered ledges; lower 8 mm flat / 15 mm flat / 8 mm flat ledges | Retailer evidence, not manufacturer authority; cannot add logical IDs or prove exact depth/geometry by itself |
| User-supplied closeup photographs in the migration review | User evidence | Intentional shallow long ledges/notches around the wells and the physical cord routing through the board ends | No public source URL, scale, revision label, or exact dimensions; visual evidence alone does not establish additional selectable contacts |

The Amazon annotation is retained because it resolves a useful commerce gap,
not because it overrides the manufacturer source. In particular, the shallow
lower grooves visible in the supplied photos do not visually correspond to the
outboard small crimps. The closeups support authoring those grooves as physical
nonselectable board geometry. Whether a lower ledge is a separate training
contact or part of a larger recess remains unresolved; it must not become a
logical ID without manufacturer confirmation or a separately approved product
revision audit.

All attachment coordinates, passage centerlines, body thickness, shallow
ledge dimensions, canonical pose transforms, anchor placement, cord lengths,
cord radius, cord material, knot treatment, and camera values are
`displayEstimate` unless a retained primary source directly establishes them.
The evidence packet must carry this source-versus-estimate distinction into
the generated descriptor and review report.

## Presentation architecture

The package remains model-only: one USDZ, one hash-bound descriptor, no raster
presentation, no canonical 2D paths, and no duplicated model for a face or
orientation. The board USDZ owns all physical board surfaces, including the
four modeled end passages and the visible shallow ledges/notches. Only the
seven approved logical hold meshes are selectable and bound to hold IDs.

The runtime adds one transient suspension layer:

```text
board.json model + positions + twoBranchCord metadata + descriptor
  -> resolve selected position
  -> apply that position's canonical board pose
  -> transform four local passage points into world space
  -> solve two continuous branch paths to one invisible fixed anchor
  -> render one USDZ + non-pickable cords + orbit camera
```

The four passages are physical routing features, not holds. They are grouped
as two end pairs (`left` and `right`), with two passage points per end. The
two continuous branches are independently ordered through the relevant paired
passages and share the same fixed world-space anchor. The package describes
the order explicitly so an implementation never infers it from node names or
from the camera. Any board-interior passage span is checked against the actual
mesh and may be hidden only where the source-supported routing feature
contains it; free spans remain visible as cord geometry.

For each branch, the ordered centerline is the continuous path
`anchor -> passageIDs[0] -> passageIDs[1] -> anchor`. The two passages in a
pair represent the two physical crossings at that board end; the branch's
interior span follows the modeled routing feature, while its two free spans
are solved independently between the fixed anchor and the transformed
passage interfaces. This makes the shared-anchor topology explicit without
inventing knot or hidden-cord detail that the sources do not establish.

The anchor is a mathematical world-space point only. It has no scene node,
mesh, texture, accessibility element, or hit target. It stays fixed while
the board pose and camera change.

## Typed package contract

`media.type: "model"` gains a strict suspension discriminator. Existing
boards may continue to use `singleCord` when their evidence and geometry
actually describe one attachment. Flash Board must migrate to
`twoBranchCord`; it must not retain a misleading `singleCord` declaration.

The following is the intended shape; member names and order become the typed
schema contract during implementation:

```json
{
  "suspension": {
    "type": "twoBranchCord",
    "passages": {
      "left": [
        {
          "id": "left-outer",
          "nodeID": "Board/CordPassageLeftOuter",
          "pointInModel": [-0.08, 0.0, 0.012],
          "provenance": "displayEstimate"
        },
        {
          "id": "left-inner",
          "nodeID": "Board/CordPassageLeftInner",
          "pointInModel": [-0.08, 0.0, -0.012],
          "provenance": "displayEstimate"
        }
      ],
      "right": [
        {
          "id": "right-inner",
          "nodeID": "Board/CordPassageRightInner",
          "pointInModel": [0.08, 0.0, 0.012],
          "provenance": "displayEstimate"
        },
        {
          "id": "right-outer",
          "nodeID": "Board/CordPassageRightOuter",
          "pointInModel": [0.08, 0.0, -0.012],
          "provenance": "displayEstimate"
        }
      ]
    },
    "branches": [
      {
        "id": "left-branch",
        "passageIDs": ["left-outer", "left-inner"],
        "restLength": 0.24,
        "radius": 0.002,
        "material": "matteCord",
        "provenance": "displayEstimate"
      },
      {
        "id": "right-branch",
        "passageIDs": ["right-inner", "right-outer"],
        "restLength": 0.24,
        "radius": 0.002,
        "material": "matteCord",
        "provenance": "displayEstimate"
      }
    ],
    "anchor": {
      "offsetFromBoardBounds": [0.0, 0.22, 0.0],
      "visibility": "invisible",
      "provenance": "displayEstimate"
    },
    "canonicalPoses": {
      "front": {
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "translation": [0.0, 0.0, 0.0],
        "camera": {
          "viewDirection": [0.0, 0.0, -1.0],
          "fitPadding": 0.1
        }
      }
    }
  }
}
```

The values above are illustrative display estimates, not requirements to copy
into the Flash package. The implementation must use evidence-reviewed values
from the package and label them accordingly.

Schema rules:

- `passages` contains exactly two named end pairs, each with exactly two
  distinct passage IDs. Every passage node is importer-visible and hash-bound
  to the descriptor; passage nodes cannot be logical hold nodes.
- Every branch has exactly one ordered passage pair, exactly one finite
  positive rest length and radius, and a declared cord material. Branch IDs,
  passage IDs, and position keys are unique and order-sensitive.
- Both branches resolve to the same fixed anchor. The anchor is metadata, not
  a USDZ node. Branch-specific anchors, visible anchor geometry, and a second
  model are invalid.
- `canonicalPoses` has exactly one finite normalized pose per supported
  `positionID`, with no unknown or duplicate positions. Camera values are
  presentation-only.
- The model package declares no raster fallback, no baked cord or anchor, no
  hand-authored hold bounds, and no extra selectable passage/notch meshes.
- Optional closed-schema members mean omission only. Explicit JSON `null`,
  unknown members, duplicate keys, nonfinite numbers, wrong scalar kinds, and
  order violations are rejected consistently by Python and Swift parsers.

The raw parser and typed parser must preserve object/list order and scalar
kind, matching the existing cross-language package contract. A `singleCord`
declaration is not silently widened to `twoBranchCord`; conversion must be an
explicit migration with evidence and a semantic audit.

## Cord solve and failure behavior

For every canonical pose, transform each passage point by the board pose and
keep the anchor fixed. Solve each branch's ordered free spans in the gravity
plane using a deterministic uniform-cord catenary. A straight span is allowed
only when its declared rest length equals its endpoint separation within the
declared numerical tolerance. Interior passage routing is continuous and
must preserve the declared order; it is not replaced with a direct shortcut
that would pass through the board.

The solver uses fixed sample count, material parameters, gravity direction,
numeric tolerance, and arc-length procedure across platforms. It verifies
finite samples, positional continuity at passage joins, sampled length, tube
radius, and self-intersection. Tangent discontinuity between an independently
solved catenary and the modeled interior passage span is permitted at a
passage interface; tangent matching is not a contract for this piecewise
route. It checks cord clearance against actual board triangles/rays, requiring
at least cord radius plus the declared clearance everywhere except the
approved physical passage interface.

Any of these conditions enters the existing explicit model-unavailable/error
state for the affected presentation. There is no straight-line fallback,
raster fallback, alternate face model, visible anchor stand-in, or silent
relaxation:

- missing, duplicate, unknown, or non-importer-visible passage node;
- passage point outside the descriptor coordinate-frame contract;
- missing anchor, branch, pair, material, pose, or position mapping;
- nonfinite, nonpositive, or inconsistent cord dimensions;
- rest length shorter than any required anchor-to-passage or passage-to-
  passage separation;
- nonfinite, nonunit, or otherwise invalid canonical pose;
- an unsolved, discontinuous, nonfinite, self-intersecting, or wrong-length
  branch;
- cord tube collision with board geometry outside the approved passages;
- a cord mesh becoming selectable, accessible, or a nearer hit than the
  descriptor-bound active hold; or
- camera framing that clips/conceals the active hold, attachment passages, or
  required visible cord segment.

## Migration from `singleCord`

The migration must be performed as a typed package change with a semantic
before/after audit. It must:

1. retain the seven logical IDs, their metadata, order, positions, transitions,
   and source provenance;
2. replace Flash's `suspension.type` with `twoBranchCord` and add the four
   physical passage bindings;
3. preserve one USDZ and one descriptor, while adding only the modeled
   passage/ledge geometry required by the approved evidence;
4. remove any provisional single-attachment assumption from descriptor,
   runtime, tests, and reports;
5. keep the shallow ledges/notches as nonselectable geometry with no new
   logical IDs, and document the unresolved product-revision gap; and
6. prove no raster asset, canonical 2D path, duplicate face model, baked cord,
   visible anchor, nail, carabiner, or mounting environment remains.

The deterministic converter must reject duplicate or unknown legacy members,
preserve every recognized field, and fail closed if a single-cord package is
missing evidence needed for the two-branch conversion. Existing unrelated
single-cord boards are not changed by this Flash migration.

## Geometry, export, and verifier requirements

The geometry authoring pass is Astra-owned after the approved multi-angle
evidence gate. It must directly author the reviewed cylindrical body, both
faces, the seven selectable contact surfaces, the four physical cord passages,
and the visible shallow ledges/notches. It must not trace pixels, segment
photos, infer new contacts, or change the cord estimate to hide a board-shape
failure. The geometry review must include front, opposite-face, oblique, and
close passage/notch views before final export.

The actual-export verifier must reimport the USDZ in isolation with source
materials removed and prove:

- exactly one body model and exactly seven descriptor-bound logical hold IDs;
- four importer-visible passage nodes with stable source-piece correspondence;
- physical passage and shallow-notch surfaces are present but nonselectable;
- every board and contact mesh has a usable material and expected embedded
  material/image payload where required;
- no cord, anchor, nail, carabiner, wall, ceiling, mounting hardware, or
  unbound selectable mesh is present;
- actual triangle intersections and nearest-hit probes resolve each active
  hold to its expected descriptor ID while cord geometry is ignored;
- complete ligaments remain around exterior-adjacent passages/recesses and
  between neighboring pockets; and
- dimensions, bounds, triangle budget, and model hash satisfy the package
  descriptor without promoting display estimates to physical metadata.

The verifier must retain the exact command, options, imported node mapping,
hashes, probe results, and failure diagnostics. Blender bootstrap and managed
sandbox Metal failures follow the existing migration skill's documented
one-repro boundary; a pre-Python sandbox SIGSEGV is not treated as a geometry
failure, and an authorized narrow host-context export is cleaned up exactly.

## SceneKit, picking, and accessibility

`BoardModelView` loads the validated USDZ once, resolves the selected
position's canonical pose, transforms the four descriptor passage points, and
creates the two transient cord branches. The cord nodes use independent
materials, remain outside the model's selectable node set, and are absent
from accessibility. The invisible anchor has no SceneKit node.

Interactive picking continues to use actual nearest triangle intersections on
the seven descriptor-bound hold meshes. Tests must explicitly flush
`SCNTransaction`, shoot front-to-back orthographic segments through each
active hold, assert the expected nearest hold ID, and assert the cord cannot
become the nearer hit. Passage and notch geometry may be visible but must not
produce a logical selection.

Selecting a hold or resolving a workout position restores that position's
canonical board pose and camera, even after orbiting. Manual gestures modify
only camera azimuth, elevation, and allowed zoom; they never rotate the board
or anchor independently. During a pose transition, the board and both cord
branches animate from the old valid state to the new deterministic state and
end exactly at the new solve. Highlight clearing restores wood, and the cord
does not affect active/cleared state.

## Validation and iOS acceptance

Before promotion, run the shared malformed-fixture matrix in both Python and
Swift for all `singleCord`/`twoBranchCord` discriminator, passage, branch,
pose, null, scalar-kind, duplicate-key, and order-sensitive failures. Run
package validation, exact schema counts, model-byte/hash staging checks, and
the actual-export verifier.

The first migration's iOS review must use the exact owned simulator name
required by the validation skill and record its UUID before XCTest. It covers:

- three-well and two-well positions, including every supported canonical pose;
- front, opposite-face, oblique, and active-hold captures;
- selection snap and reset after manual camera orbit;
- board/cord continuity and visible routing through both end passage pairs;
- physical taps on every approved hold, with passage/notch taps not selecting;
- active highlight, clear, and reappearance;
- workout-driven position resolution and transitions; and
- explicit unavailable/error behavior for every listed malformed or unsolved
  case.

Retain captures and native-picking diagnostics under the workspace-owned
context packet. If CoreSimulator is unavailable, record that environment
failure and do not touch shared simulator services; the migration is not
accepted until the required iOS checks run.

## Cost-aware delivery

Luna is the default for source synthesis, typed schema, conversion, catenary
math, verifier, tests, documentation, package work, and routine renderer
integration. Escalate to Terra only after a bounded Luna attempt exposes
intricate non-geometry schema, tooling, SceneKit, or cross-platform failures.
Astra owns only the final physical geometry and fidelity correction after the
human-approved evidence gate. No lower-cost worker may alter board shape,
passage placement, or notch interpretation to mask a validation failure.

## Out of scope

- live rope dynamics, stretch, knots, swing, friction, loads, or safety claims;
- visible nails, hooks, carabiners, walls, ceilings, or mounting scenery;
- new logical contacts inferred from commerce annotations or photographs;
- duplicate USDZs, raster fallbacks, or per-position model copies; and
- treating any display estimate as a sourced product measurement.
