# Hangboards Batch 03 3D Migration Design

**Status:** approved design and exact-revision evidence set
**Evidence approval:** human-approved on 2026-09-20
**Input:** `/Users/asherlc/Downloads/hangboards-batch-03` R4

## Context

Batch 03 supplies six portable-board revisions as eight technically validated
GLB exports. Five revisions have one export each. Plateau Lifting Edge has three
exports representing the same physical oak contact with no blocker, the blocker
in its 15 mm orientation, and the blocker in its 10 mm orientation.

The batch is an implementation input, not the authority for physical-contact
identity. Its R4 records are `PARTIAL`: the native meshes pass the batch's
technical checks, but manufacturer evidence, Hang Ten contact semantics,
suspension topology, package validation, and current-source app review still
belong to this repository. Independent manufacturer research found three
material inventory corrections:

1. Port-A-Board has one continuous asymmetric 30 mm cavity. Its named
   two-finger and mono uses are not a second physical contact.
2. The standard Stone Hanger Mini's smooth pull-up jug is the recessed internal
   cavity/body, not the upper exterior surface. Both exterior sides participate
   in the one 60 mm pinch contact.
3. Plateau's reversible blocker changes the effective depth of one physical oak
   contact. It does not create separate 15 mm and 10 mm contacts.

Those corrections require a narrow runtime extension for a physical contact
whose effective depth depends on board configuration. They do not justify a
second identity system, a schema-version fork, or duplicated boards.

## Goals

- Migrate all six exact revisions to model-only schema-v3 packages.
- Preserve one stable identity for every physical contact and correct the
  inventories before binding model nodes.
- Represent Plateau's 18, 15, and 10 mm setups as three original model
  presentations and three positions over one stable contact.
- Carry the selected configuration through resolution, board detail, custom
  routine authoring, workout playback, ODR loading, and activity history.
- Represent only evidence-supported suspension, as bundled transient metadata.
- Fail closed whenever evidence, configuration, model identity, or runtime
  assets cannot establish the requested setup.
- Retain exact source traceability and obtain human review from retained
  import/reimport reports plus the current-source app. Workbench review is
  limited to applicable pre-migration raster/contact metadata because model
  packages are read-only there.

## Non-goals

- Adding or changing a training routine, set count, repetition count, timer,
  grip cue, coaching claim, loading recommendation, or safety claim.
- Making the blocker, cord, hardware, or environment selectable.
- Simulating knots, loading, swinging, rope physics, or hidden cord routes.
- Supporting old app binaries reading the new package, routine, or activity
  fields. The app and its bundled packages ship together.
- Generalizing configuration overrides beyond exact contact depth.
- Automatically detecting contacts or deriving paths from images.
- Treating the batch's hold map, mesh labels, or generated review renders as a
  substitute for current manufacturer evidence and operator review.

## Exact revisions and source models

The input hashes below identify the accepted R4 GLB bytes. Conversion may
change container bytes, but the import audit must retain each source hash and
bind each resulting USDZ to its own generated descriptor hash.
Accepted GLBs remain immutable provenance parents. For each Plateau
presentation, export consumes its own separately retained, hash-bound,
operator-authored corrected `.blend`, linked to its exact accepted parent by
`operatorAuthoredCorrection`; it never compiles the uncorrected GLB directly.

| Package slug | Board ID | Exact revision | Accepted GLB input(s) and SHA-256 |
| --- | --- | --- | --- |
| `aelith-cyclops-011` | `aelith.cyclops-011` | Aelith Cyclops #011, Blue × Black | `aelith-cyclops-011.glb` — `e30bffa8078cd37a9389037146f55fb340d10163d4a7dd50a472cef3fbe46d3a` |
| `frictitious-nug` | `frictitious.nug` | Frictitious The NUG | `frictitious-nug.glb` — `40c328f9bdd3ff10befcd2dde71074876a70379f03ec91187609e3873d4d7c70` |
| `frictitious-port-a-board` | `frictitious.port-a-board` | Frictitious Port-A-Board | `frictitious-port-a-board.glb` — `4314f5c6a129f17ff26139ed945b3d4b1fb32a3d2ee596522a674d3373bf69de` |
| `nature-stone-hanger-mini` | `nature.stone-hanger-mini` | Nature Climbing Stone Hanger Mini — Oak | `nature-stone-hanger-mini.glb` — `d9eedc2407d836bf008087e547fde76d81ecc41f306c7e2ce526c49524be626e` |
| `nature-stone-hanger-mini-karma8a` | `nature.stone-hanger-mini-karma8a` | Nature Climbing Stone Hanger Mini × KARMA8A | `nature-stone-hanger-mini-karma8a.glb` — `3ebe92f518cc66dd03f8256ebd6260a950f01252b74adbeb2b0c3116e775ffb6` |
| `plateau-lifting-edge` | `plateau.lifting-edge` | Plateau Lifting Edge base kit with reversible blocker and oak edge | `plateau-lifting-edge.glb` — `a71374b13a0629f98971063deacb6fbdddb5171133094c692b6a9841547ff8ce`; `plateau-lifting-edge-15mm.glb` — `4328f58efac235aa69efb4326b3254577d745e1e86881aa454ef79bcca9945ba`; `plateau-lifting-edge-10mm.glb` — `88bb08d316588b270a6b47b40acce467c81ebbcfa630b089fec638277f15e208` |

The accepted product identities and visual evidence are frozen in Appendix A.
The URL, publisher, retained-byte hash, and stated support form one record; a
later response at the same URL is not silently equivalent.

The standard Mini package is specifically the approved Oak revision. Its
`productURL` must be exactly
`https://natureclimbing.com/products/stone-hanger-mini-oak`. Its package and
new batch-03 source-audit records must identify Oak consistently and contain no
stale Beech variant name or Beech product link. Historical audits outside this
migration remain historical records and are not rewritten.

## Physical-contact inventories

`contacts[]` remains the sole physical-contact inventory. Contact IDs are
stable within the board revision. Orientation, finger use, mesh patch, blocker
orientation, and presentation are not reasons to duplicate a contact.

| Board | Final contact IDs | Batch-node binding and correction |
| --- | --- | --- |
| Aelith Cyclops #011 | `mono-20` | Bind batch node `edge-20mm` to `mono-20`. The lanyard opening is suspension, not a contact. |
| Frictitious NUG | `edge-25`, `edge-20`, `edge-13`, `edge-8`, `jug-40`, `pinch-60` | Bind the four named edge nodes directly. Bind `outer-jug` to `jug-40` and the opposing lower surface `outer-pinch-opposition` to `pinch-60`. These are six physical selectable surfaces; the 60 mm pinch is a documented use across opposed surfaces, not a seventh contact. |
| Frictitious Port-A-Board | `edge-30`, `edge-25`, `edge-20`, `edge-15`, `edge-12`, `edge-10`, `edge-8`, `jug-outer-rim`, `pinch-body` | Bind the seven depth nodes and `outer-jug` to the corresponding edge and jug IDs. Do **not** directly bind batch node `outer-pinch-opposition`: it is the bottom band, while approved `pinch-body` is the narrow side body. Deliberately repartition/re-author that side surface, bind the corrected node to `pinch-body`, and retain operator review of the result. Remove `pocket-30-two-finger-mono`: named finger placements reuse the one continuous `front-lower-30mm`/`edge-30` surface. |
| Stone Hanger Mini — Oak | `granite-edge-15`, `wood-edge-15-incut`, `pinch-60`, `pull-up-jug` | Bind the two edge nodes directly. Bind the upper and lower exterior patches as multiple descriptor nodes of the one `pinch-60` contact and review that the combined highlight is complete. Deliberately partition `pull-up-jug` on the internal broad recess; do not classify the upper exterior patch as a jug. |
| Stone Hanger Mini × KARMA8A | `granite-edge-15`, `wood-edge-15`, `pinch-60` | Bind the two edge nodes directly and bind both `outer-pinch-upper` and `outer-pinch-lower` as multiple descriptor nodes of the one `pinch-60` contact, with deliberate completeness review. Do not add a jug; the exact revision's manufacturer source supports only three contact families. |
| Plateau Lifting Edge | `edge-18` | Bind `edge-18mm` to stable package ID `edge-18` in all three models. The reducer/blocker node is body geometry and remains nonselectable. Remove `blocker-edge-15` and `blocker-edge-10`; 15 and 10 mm are configurations of `edge-18`. |

This table supersedes earlier repository audits where they conflict on the
Port-A-Board duplicate 30 mm contact, the standard Mini jug location, or the
Plateau blocker contacts. Later source-audit changes must cite this evidence
set and explain any proposed reversal.

Contact metadata remains source-backed. For example, NUG's `jug-40` and
`pinch-60` values are supported by the manufacturer product specification,
while an unmeasured outer Port-A-Board surface must not gain an invented depth.

## Geometry-authoring policy

Primary manufacturer evidence is for deliberate operator judgment and visual
comparison only. It must not drive image segmentation, hold detection,
registration/alignment, generated masks or contours, vectorization, automatic
path simplification, automatic cropping, or proposal/refine/promote geometry.

If a canonical 2D path is corrected during the audit or pre-migration work, an
operator must draw and review that path directly in `board.json`, using the
Trango Rock Prodigy Pivot package as the structural and path-style precedent.
Operator-selected circle, oval, pill, rounded-rectangle, or rectangle
constraints may be used only when the physical contact genuinely has that
shape; the saved path remains authoritative. Symmetry may be mirrored only
when the product is genuinely symmetric.

The final packages in this design are model-only, so they ship no raster
`contactGeometry` or canonical 2D paths. Their selectable geometry comes only
from the hash-bound descriptor's deliberate node-to-contact bindings. The same
manual policy applies to correcting the source model's contact partitions:
particularly the Port-A-Board side pinch, the standard Mini internal broad
recess jug, and both Nature multi-node pinch mappings. Mesh names are hints,
not automatic semantic authority.

All three Plateau presentations (`depth-18mm`, `depth-15mm`, and `depth-10mm`)
must omit every screw/mounting hole. An operator deliberately removes and caps
each such hole in each corrected source mesh, without automated extraction,
hole detection, or geometry repair. This display omission does not claim that
the physical product lacks mounting holes. Preserve the lower open cord
exits/grooves and their suspension attachment semantics; they are not
screw/mounting holes and must not be capped. Preserve the oak edge, black body,
reversible reducer/blocker in its applicable configurations, stable `edge-18`
identity, and selectable contact geometry.

Each of the three corrections has its own retained `.blend`, correction audit,
and normal plus rear/oblique review images. The manifest hash-binds the source
and correction audit to the accepted GLB; the audit binds the review images and
records `sourceGeometryChanged:true` and `prohibitedAutomationUsed:false`.
After candidate generation, explicit human inspection must confirm all holes
are removed/capped and the cord exits and preserved features remain intact.
Only then record the actual UTC approval instant, reviewer, and render hashes;
never prefill or backdate approval. Missing or mismatched corrections,
artifacts, or approvals in any presentation block promotion of all three.

## Model-only package contract

All six packages remain schema version 3 and contain only original model
presentations:

- Aelith, NUG, Port-A-Board, Stone Hanger Mini — Oak, and Stone Hanger Mini ×
  KARMA8A each have one model presentation, one USDZ, and one descriptor.
- Plateau has three model presentations: `depth-18mm`, `depth-15mm`, and
  `depth-10mm`. Each presentation has its own USDZ and descriptor. The 18 mm
  presentation is the sole default.
- Every model presentation has `derivation.type: "original"`.
- A package has exactly one default presentation and cannot mix raster and
  model media.
- Each presentation owns a unique `assetPath` and `descriptorPath`. Descriptors
  remain bundled; USDZ files are the only ODR assets.
- Raster PNG assets and `contactGeometry` are removed. There is no raster
  fallback and no alternate package identity.
- Each descriptor's `nodes` and `contacts` inventory must equal the complete
  final `contacts[]` inventory for that board. This design does not weaken the
  descriptor contract to presentation-specific subsets.
- Nonselectable body, blocker, and attachment nodes are tagged as body or
  attachment. They cannot be promoted to contact nodes merely to make an
  inventory check pass.

Suggested asset names are `assets/primary.usdz` and
`assets/primary.model.json` for the five single-presentation packages, and
`assets/depth-18mm.usdz`, `assets/depth-15mm.usdz`,
`assets/depth-10mm.usdz` with corresponding `.model.json` files for Plateau.

## Final non-Plateau position inventories

The following rows are the exact authored `positions[]` order. Each
`contactIDs` array is likewise in canonical package-contact order. All five
boards use their one original model presentation, `primary`; none of these
positions authors `effectiveDepths`.

| Board ID | Position ID | Presentation ID | Exact `contactIDs` |
| --- | --- | --- | --- |
| `aelith.cyclops-011` | `front-cup` | `primary` | `["mono-20"]` |
| `frictitious.nug` | `front-25` | `primary` | `["edge-25"]` |
| `frictitious.nug` | `front-inverted-20` | `primary` | `["edge-20"]` |
| `frictitious.nug` | `reverse-13` | `primary` | `["edge-13"]` |
| `frictitious.nug` | `reverse-inverted-8` | `primary` | `["edge-8"]` |
| `frictitious.nug` | `outer-upper` | `primary` | `["jug-40"]` |
| `frictitious.nug` | `outer-lower` | `primary` | `["pinch-60"]` |
| `frictitious.port-a-board` | `front-upright` | `primary` | `["edge-30", "edge-25"]` |
| `frictitious.port-a-board` | `front-inverted` | `primary` | `["edge-20"]` |
| `frictitious.port-a-board` | `reverse-upright` | `primary` | `["edge-12", "edge-10"]` |
| `frictitious.port-a-board` | `reverse-inverted` | `primary` | `["edge-15", "edge-8"]` |
| `frictitious.port-a-board` | `outer-upper` | `primary` | `["jug-outer-rim"]` |
| `frictitious.port-a-board` | `pinch-side` | `primary` | `["pinch-body"]` |
| `nature.stone-hanger-mini` | `front-upright` | `primary` | `["pull-up-jug", "granite-edge-15"]` |
| `nature.stone-hanger-mini` | `wood-inverted` | `primary` | `["wood-edge-15-incut"]` |
| `nature.stone-hanger-mini` | `pinch-side` | `primary` | `["pinch-60"]` |
| `nature.stone-hanger-mini-karma8a` | `granite-front` | `primary` | `["granite-edge-15"]` |
| `nature.stone-hanger-mini-karma8a` | `wood-inverted` | `primary` | `["wood-edge-15"]` |
| `nature.stone-hanger-mini-karma8a` | `pinch-side` | `primary` | `["pinch-60"]` |

Port-A-Board intentionally replaces the batch `outer-lower` position with
`pinch-side` because the approved contact is the manually corrected narrow
side body, not the batch bottom band. Each Nature board intentionally collapses
its batch upper/lower pinch views into one `pinch-side` position whose one
contact binds both reviewed exterior nodes. The standard Mini's
`front-upright` position includes the manually partitioned internal broad
recess jug and the granite edge in the exact order shown.

## Position-scoped effective depth

### Additive schema field

`BoardPosition` gains an optional `effectiveDepths` dictionary keyed by stable
contact ID. Values use the existing `HoldDepth` representation, but this field
accepts only an exact positive range: `minimum == maximum` and both values are
finite and greater than zero.

Plateau's authored positions are:

```json
{
  "positions": [
    {
      "id": "depth-18mm",
      "presentationID": "depth-18mm",
      "contactIDs": ["edge-18"],
      "effectiveDepths": {
        "edge-18": { "range": { "minimum": 18, "maximum": 18 } }
      }
    },
    {
      "id": "depth-15mm",
      "presentationID": "depth-15mm",
      "contactIDs": ["edge-18"],
      "effectiveDepths": {
        "edge-18": { "range": { "minimum": 15, "maximum": 15 } }
      }
    },
    {
      "id": "depth-10mm",
      "presentationID": "depth-10mm",
      "contactIDs": ["edge-18"],
      "effectiveDepths": {
        "edge-18": { "range": { "minimum": 10, "maximum": 10 } }
      }
    }
  ]
}
```

`PhysicalContact.depth` for `edge-18` retains the base product fact of 18 mm.
Whenever a position is resolved, its effective depth is authoritative for
matching, display, and recording. An override changes no other contact fact:
kind, shape, capacity, name, and identity continue to come from
`PhysicalContact`.

### Validation invariants

Swift and Python package readers enforce the same rules:

1. Every `effectiveDepths` key is identifier-shaped, names a canonical
   `contacts[]` member, and appears in that position's `contactIDs`.
2. The field is valid only when omitted or when it contains a nonempty object.
   Explicit `null` and `{}` are invalid.
3. Every value is an exact finite positive `.range`; categories, intervals,
   zero, negative, NaN, and infinity are invalid.
4. An overridden contact's base `PhysicalContact.depth` must itself be an
   exact finite positive `.range`. The effective value may equal the base or
   reduce it, but must not exceed it.
5. If any position overrides a contact, every position containing that contact
   explicitly overrides it. There is no mix of inherited and configured depth
   for one contact.
6. Omission remains valid for ordinary contacts and old packages.
7. Effective-depth maps cannot add contacts, make a descriptor node
   selectable, or substitute for position membership.

The schema remains v3 because this is an additive, coordinated app/package
extension. Existing v3 data remains readable by the new app. Strict old
binaries may reject the new field and are not required to read newly bundled
packages or newly saved routine/activity data.

## Multiple model presentations and per-presentation validation

The arbitrary one-model-presentation limit is removed from the Swift loader
and Python catalog parser. All other model-only constraints remain.

Validation is scoped per presentation:

- Let `localPositions` be positions whose `presentationID` equals the model
  presentation ID. Every model presentation must have at least one local
  position, and every position must reference a real presentation.
- A local position's `contactIDs` must be nonempty, unique, in canonical board
  order, and a subset of that presentation descriptor's complete inventory.
- The union of `contactIDs` across a presentation's local positions must equal
  the descriptor inventory. This check runs independently for every model
  presentation. Contact IDs may appear in more than one position when the same
  physical surface is usable from more than one evidenced orientation.
- Every descriptor still equals the complete board inventory. Per-presentation
  validation must not relax that global identity contract.
- Orientation rotations and suspension canonical-pose keys are validated
  against only that presentation's local position IDs. Metadata for one model
  presentation neither requires nor accepts keys belonging to another.
- Asset paths, descriptor paths, model hashes, orientation data, suspension
  attachments, and cameras are validated independently per presentation.

The existing single-presentation behavior is unchanged. The loader must not
obtain the first model descriptor and apply it to all positions as a global
shortcut.

## Plateau configuration transitions

The blocker is a physical setup change. All six directed cross-configuration
edges are authored explicitly as `setupRequired`:

- `depth-18mm` → `depth-15mm` and the reverse;
- `depth-18mm` → `depth-10mm` and the reverse; and
- `depth-15mm` → `depth-10mm` and the reverse.

Remaining in the same position is the existing implicit free transition. No
cross-configuration edge is `seamless`; no transition duration is invented.
Explicit edges preserve the intended semantics even though an omitted edge
currently defaults conservatively to `setupRequired`.

## Suspension decisions

Suspension follows `docs/3D_SUSPENSION_AND_ODR.md`. It is bundled presentation
metadata rendered as transient, invisible-anchor, non-pickable geometry. The
USDZ remains the board and contact mesh only.

| Board | Topology | Evidence-backed attachment decision |
| --- | --- | --- |
| Aelith Cyclops #011 | `singleCord` | One cord at the narrow tip attachment/opening, supported by AE-1 through AE-3. The knot, carabiner, anchor, length, and load behavior are not product claims. |
| Frictitious NUG | `pairedLeadCord` | Two visible lead passages, supported by NU-1 through NU-4. Render two exterior leads to one invisible anchor without inventing a hidden lead-to-lead route. |
| Frictitious Port-A-Board | `pairedLeadCord` | Two visible front passages and paired lead behavior, supported by PA-1 through PA-5. Do not add another through-bore, interior connection, or unsupported mounting route. |
| Stone Hanger Mini — Oak | `pairedLeadCord` | Leads seat in the left and right open side grooves/notches, supported by NS-1 through NS-5. These features are open grooves, not closed bores. |
| Stone Hanger Mini × KARMA8A | `pairedLeadCord` | Leads seat in the left and right open side grooves/notches, supported by NK-1 through NK-5. These features are open grooves, not closed bores. |
| Plateau Lifting Edge | `pairedLeadCord` | Leads emerge from the two open ends of the lower curled extrusion, supported by PL-1 through PL-6. Do not represent drilled cord holes. Each of the three presentations carries equivalent presentation-scoped suspension metadata and attachments. |

Every suspended position must have one matching `canonicalPoses` key in its
own presentation, and that presentation's pose-key set must exactly equal its
local position-ID set. No pose may be borrowed from another presentation or
silently omitted. An unchanged, previously reviewed pose may be reused only
after its source coordinates and quaternion are converted into the imported
descriptor basis and the converted pose is revalidated against model bounds,
attachments, contact visibility, and cord clearance.

The three `pinch-side` poses require deliberate retained visual review because
their contact partitions differ from the batch's original upper/lower or
bottom-band assumptions. When suspension `canonicalPoses` define the complete
physical setup for these positions, separate `orientation` metadata is
unnecessary and must not duplicate or conflict with the canonical pose.

Attachment coordinates, invisible anchor placement, cord radius, rest length,
material, camera framing, and canonical pose are documented display estimates
unless the source explicitly establishes a number. Each estimate must satisfy
the solver, length, mesh-clearance, self-intersection, framing, picking, and
accessibility checks. Failure of either paired lead makes the whole
presentation unavailable. No cord, knot, carabiner, weight, hook, wall, tree,
or stand is baked into a model.

The repository's closed cord audit must be updated to cover all newly migrated
model presentations. A represented decision requires the exact evidence and
human approval in Appendix A; it cannot inherit a historical decision from a
different revision.

## Contact requirements and custom routines

`ContactRequirement` gains optional `positionID` for a board-specific exact
selection:

```swift
struct ContactRequirement: Codable, Hashable {
    let contactID: String?
    let positionID: String?
    // Existing kind, shape, depth, capacities, and selection fields remain.
}
```

The field is deliberately narrow:

- Generic catalog requirements leave both `contactID` and `positionID` unset;
  they never author a board configuration.
- Initially, `positionID` is accepted only for a board-specific custom routine
  with `selection: single` and a nonempty exact `contactID`, bound to the
  applicable board revision. A bilateral or board-agnostic requirement cannot
  carry it.
- The position must exist, contain the exact contact, and satisfy all authored
  requirement fields under its effective metadata.
- When the requirement authors `depth`, the selected contact must have a known
  resolved position override or base depth and the authored value must match
  it. An authored depth can never match an unmeasured contact. When no depth is
  authored, an exact contact + position selection remains valid even if the
  contact is unmeasured; resolution must not invent a depth. Plateau's depth
  selector is the narrower editor contract described below and always authors
  its known exact depth atomically with `positionID`.
- Converting a requirement to generic mode or copying/moving the routine to a
  different board strips both `contactID` and `positionID` together. It
  preserves the requirement's semantic `depth` unless that conversion workflow
  explicitly changes or clears the depth.
- Hand materialization and ordinary copying retain `positionID` when they
  retain the same exact contact, the same board binding, and single selection.
  Any transformation that drops that exact-contact context must also drop the
  position.
- No manufacturer or catalog routine is rewritten to add a configuration that
  its training source did not prescribe.

In the custom-routine editor, choosing `edge-18` on Plateau exposes an
**Edge depth** choice of 18, 15, or 10 mm. Initial selection and every later
configuration switch atomically update both `positionID` and
`ContactRequirement.depth` to the selected position's exact effective depth.
The operation does not create, remove, or retoggle a contact. No intermediate
saved or previewed state may pair one position with another position's depth.
A stale exact contact or position blocks save/start until the athlete repairs
it.

## Resolved runtime target

Resolution returns an immutable board target rather than only contacts. Its
logical contents are:

```swift
struct ResolvedBoardTarget: Hashable {
    let boardID: String
    let revisionID: String
    let contactIDs: [String]
    let positionID: String
    let presentationID: String
    let effectiveDepths: [String: HoldDepth]
    let modelSHA256: String?
}
```

The exact Swift name is an implementation choice; the information and
invariants are not. `modelSHA256` comes from the resolved presentation's
descriptor, never from `board.defaultPresentation` unless that is actually the
resolved presentation. Unlike the package position's override-only
`effectiveDepths`, the resolved map is materialized: it contains every selected
contact whose depth is known, using the position override when present and the
unchanged base depth otherwise. This materialized map may be empty when none of
the selected contacts has a known depth. It never synthesizes a depth merely
because a position was selected.

Resolution proceeds as follows:

1. An explicit `positionID` must exist and satisfy the complete requirement.
   If the requirement authors `depth`, the corresponding selected contact must
   have a known effective/base depth and it must match. If the requirement
   omits depth, depth adds no constraint, including for an unmeasured exact
   contact. Failure is an error; it does not search another position or invent
   metadata.
2. Without an explicit position, matching evaluates contact metadata as
   modified by each candidate position's `effectiveDepths`.
3. An exact depth selects the unique compatible configuration. On Plateau,
   exact 18, 15, and 10 mm requirements resolve to the correspondingly named
   positions while preserving `edge-18`.
4. A requirement with no depth, a broad category, or any other constraint that
   leaves multiple configurations requires an explicit pre-session athlete
   choice. Declaration order and the default presentation are not tie-breakers.
5. No compatible configuration fails resolution with a board/setup-specific
   diagnostic.
6. All simultaneous requirements in one target-bearing segment resolve
   jointly to one compatible position and presentation. Their candidate-position
   intersection must be nonempty; a segment cannot satisfy one requirement at
   one depth and another requirement at a different depth. Multiple compatible
   positions remain an explicit-choice case under rule 4.
7. Targetless work remains self-selected. Resolution does not manufacture a
   contact, position, presentation, effective-depth map, or setup gate for it.
8. The selected target sequence is frozen before playback. Rendering,
   recording, navigation, and setup prompts consume that same resolved value.

This extension must integrate with whole-routine position planning. It may
minimize changes only after every ambiguous equipment choice has been resolved;
it may not silently choose 18 mm or the first package position.

## User interface and session behavior

### Board detail

Plateau board detail shows a local selector labeled **Edge depth** with values
18 mm, 15 mm, and 10 mm. It presents one physical contact and swaps the model,
descriptor, suspension pose, highlight geometry, and displayed specification
atomically. The selected value's effective depth appears in specifications.
The selector exposes its label, value, and selected state to assistive
technology and announces a committed change, for example:
`Edge depth, 15 millimeters, selected.`

The default 18 mm presentation is acceptable for browsing board detail. It is
not permission for workout resolution to default an ambiguous requirement.
If the selected model cannot be acquired and verified, board detail shows an
explicit unavailable state and retains no stale model from another depth.

### Routine editor and preview

A board-bound custom requirement stores `contactID` plus `positionID`.
Preview follows that exact position/presentation and highlights the same stable
contact. Changing depth changes the model configuration, not contact identity.
Generic catalog requirements remain configuration-neutral and prompt during
workout preparation when more than one setup remains valid.

### Workout preparation and playback

The session owns the requested and last-confirmed configuration independently
of transient view state.

- Before the first affected work interval, show the resolved model and require
  readiness confirmation.
- For a later configuration change, begin showing the next setup during the
  preceding authored rest. Confirmation does not shorten the rest.
- If rest reaches zero before confirmation, pause exactly at the boundary.
  Neither work time nor rest time accrues while waiting, and countdown/spoken
  interval audio is stopped.
- The gate names only the evidenced equipment action, for example
  **Set edge to 15 mm**, and offers the existing readiness action. It adds no
  training prescription.
- After confirmation, continue through the normal countdown/start rules.
- Consecutive steps in the same configuration do not create another gate.
- Skip, forward jump, rewind, restart, and resume all compare the destination
  against the last configuration the athlete confirmed and apply the same
  transition gate. A UI presentation picker cannot override the frozen target.

The setup wait is outside authored work/rest duration and outside source plan
fidelity. Any diagnostic timing for setup remains separate from training time.

## Activity history

`ResolvedContactSnapshot` adds an optional nested configuration value:

```json
{
  "boardID": "plateau.lifting-edge",
  "revisionID": "...",
  "modelSHA256": "<hash of the selected presentation>",
  "requirement": {
    "contactID": "edge-18",
    "positionID": "depth-15mm",
    "depth": { "range": { "minimum": 15, "maximum": 15 } }
  },
  "contactIDs": ["edge-18"],
  "configuration": {
    "positionID": "depth-15mm",
    "presentationID": "depth-15mm",
    "effectiveDepths": {
      "edge-18": { "range": { "minimum": 15, "maximum": 15 } }
    }
  }
}
```

The nested value is optional so the new app decodes existing history. When the
key is present, its value must be a non-null object containing exactly
`positionID`, `presentationID`, and `effectiveDepths`. Missing, extra, unknown,
explicitly null, or malformed members invalidate the snapshot. Both IDs must
be nonempty identifier-shaped strings. `effectiveDepths` must be a non-null
object with structurally valid `HoldDepth` values, and every key must appear in
the snapshot's nonempty, unique `contactIDs`; it cannot record an unselected
contact. Unlike `BoardPosition.effectiveDepths`, this is a materialized result
map and may be `{}` when none of the selected contacts has a known depth.

New records include configuration whenever the resolved target carries an
explicit configuration/position, even when its materialized depth map is
empty. The snapshot as a whole always records that configuration's
`positionID`, `presentationID`, and actual presentation `modelSHA256`. Before
writing, recording validates the position/presentation relationship against
the resolved board, verifies every selected contact is a member of that
position, and verifies that the materialized map contains exactly every
selected contact whose override/base depth is known—including unchanged base
depth—and no unmeasured contact. If no selected depth is known, the writer
records `{}`. It also verifies `modelSHA256` against that presentation's
descriptor. Recording the default presentation's hash for a nondefault
configuration is invalid.

Historical reads do not consult the current board package: they validate the
snapshot's own shape, identifiers, selected-contact keys, and depth value
structure only; an empty materialized map is structurally valid. This keeps old
history reproducible even after package inventory changes while still
rejecting corrupt configuration payloads.

Historical snapshots are immutable. Deleted legacy contact IDs remain valid as
historical facts and are not rewritten to pretend the old package had the new
domain model.

## Legacy behavior and repair

- Packages without `effectiveDepths` behave exactly as they do today.
- Existing routines and activities with no `positionID` or `configuration`
  continue to decode in the new app.
- A valid exact requirement with no stored position may resolve automatically
  only when its full metadata identifies exactly one position. Ambiguous
  requirements require athlete choice.
- A custom routine referencing a removed contact—such as
  `pocket-30-two-finger-mono`, `blocker-edge-15`, or `blocker-edge-10`—is stale.
  The editor may offer an evidence-backed repair to the corrected contact and
  configuration, but the athlete must confirm it before save/start. Workout
  playback does not silently alias or drop a stale ID.
- Old activity history is displayed from its snapshot rather than re-resolved
  against the current package.
- New package/activity data need not decode on old binaries. This rollout does
  not add a parallel schema, compatibility shadow fields, or a raster fallback.

## ODR, staging, and caching

The existing delivery boundary remains:

- `board.json`, descriptors, and suspension metadata are bundled resources.
- Every declared USDZ is staged as an Apple On-Demand Resource in production.
- Staging discovers all model presentations rather than assuming one USDZ per
  package. This batch therefore contributes eight USDZ assets: five single
  models plus three Plateau configurations.
- The in-flight cache key remains board ID + presentation ID + descriptor
  `modelSHA256`. A board-only cache key is invalid because it could return the
  wrong Plateau configuration.
- Presentation changes acquire and verify the target resource before the scene
  commits, then replace model, highlight, suspension, pose, and camera
  atomically. A prior presentation may remain visible only as an intentional
  loading state, never as if it satisfied the new selection.
- Resource acquisition, regular-file checks, SHA-256 checks, and SceneKit
  decoding remain mandatory. Purging ODR cannot fix missing bundled suspension
  metadata.

The current staging and cache architecture already enumerates presentation
assets and keys loads by presentation/hash; implementation should extend tests
and remove single-presentation assumptions rather than rewrite the renderer.

## Fail-closed behavior

The board or requested setup is unavailable when any of the following occurs:

- an unknown or duplicate presentation, position, contact, transition, asset,
  descriptor, pose, attachment, or effective-depth key;
- missing, unreadable, undecodable, or hash-mismatched USDZ bytes;
- a descriptor whose complete contact inventory differs from `contacts[]`;
- incomplete per-presentation position coverage;
- missing or invalid presentation-scoped orientation/suspension metadata;
- an unsolved, colliding, self-intersecting, selectable, or inaccessible cord;
- an explicit routine position that no longer satisfies the contact
  requirement;
- an ambiguous configuration without athlete selection; or
- a requested depth that no configuration supports.

Failure never substitutes 18 mm, the first declared position, another model
presentation, a range of 10–18 mm, a deleted contact alias, a straight-line
cord, or a raster image.

## Validation and acceptance

Implementation is accepted only when all affected layers agree.

### Evidence and package audit

- A tracked source audit preserves Appendix A's 28 exact
  publisher/URL/source-tier/hash/path/support records and the 2026-09-20 human
  approval. All 28 approved files exist byte-for-byte at their unique tracked
  regular-file snapshot paths, and audit verification recomputes every hash.
- Package inventories exactly match the approved table, including deletion of
  Port-A-Board's duplicate pocket and Plateau's blocker contacts.
- `nature-stone-hanger-mini` identifies the Oak revision, uses exactly
  `https://natureclimbing.com/products/stone-hanger-mini-oak` as its
  `productURL`, and has no stale Beech variant name or Beech product link in
  the migrated package or its new batch-03 source-audit records.
- The Port narrow-side `pinch-body`, standard Mini internal broad-recess jug,
  and both Nature multi-node pinch mappings receive deliberate operator review
  against the approved primary evidence and retained import/reimport reports.
- Each source GLB hash matches the input table; each USDZ matches its generated
  descriptor hash.
- The eight source manifests and eight mappings require exactly five geometry
  corrections: Port, Oak, and each of Plateau's three presentations. Plateau
  imports report `sourceGeometryChanged:true` and compile only their own
  approved corrected sources; the accepted-source count remains eight and the
  standalone mapping-review count remains one (KARMA8A).
- Automated tests reject absent, swapped, hash-mismatched, or unapproved Plateau
  correction chains and verify exact node/material/contact invariants. Absence
  of screw/mounting holes is established by deliberate human visual review of
  each source's retained normal and rear/oblique images and again of the final
  shipped renders, never pixel analysis, automatic hole detection, topology
  inference, or a node-name proxy.
- Package validation finds no PNG, raster presentation, unlisted asset, mixed
  media, or descriptor inventory mismatch.

### Schema and parser tests

- Swift and Python accept multiple original model presentations and reject
  mixed/derived model media, duplicate paths, zero defaults, and multiple
  defaults.
- Tests cover every package `BoardPosition.effectiveDepths` invariant,
  including complete override coverage across positions, omitted-versus-invalid
  null/empty handling, required exact positive base depth, and rejection of an
  override above that base. These tests do not apply the package map's
  nonempty rule to materialized resolved or snapshot maps.
- Per-presentation tests prove local position union coverage and pose/orientation
  scoping; a model cannot borrow another presentation's descriptor or pose.
- Package fixtures assert the exact ordered position IDs, `primary`
  presentation references, and canonical-order `contactIDs` arrays in the
  final non-Plateau position table. No omitted batch position or replacement
  alias is accepted.
- Every suspended presentation's `canonicalPoses` keys exactly equal its local
  position IDs. Tests reject missing, extra, cross-presentation, unconverted,
  and conflicting orientation/pose metadata.
- Existing single-model fixtures and packages remain valid.
- Negative mutations exercise unknown contacts, missing local positions,
  partial effective-depth coverage, nonexact ranges, and nonfinite/nonpositive
  values.

### Resolution, editor, and persistence tests

- Plateau exact-depth requirements resolve to 18, 15, and 10 mm positions over
  `edge-18`; broad requirements produce a choice; unsupported depths fail.
- Simultaneous requirements resolve to one common position; tests reject a
  segment that could be satisfied only by splitting its contacts across two
  depths. Targetless work remains self-selected.
- Resolved targets materialize every known selected-contact depth, including
  unchanged base depth, omit unmeasured contacts, and permit an empty map when
  every selected contact is unmeasured. They never manufacture a depth.
- An explicit valid custom `positionID` is honored, and an invalid/stale one
  fails without fallback.
- Exact Port-A-Board requirements for unmeasured `jug-outer-rim` in
  `outer-upper` and `pinch-body` in `pinch-side` resolve without an authored
  depth and produce an empty materialized map. If either requirement authors a
  depth, resolution fails because no known depth can prove the claim.
- Selecting or switching Plateau depth atomically synchronizes `positionID`
  and exact requirement `depth`; resolution rejects mismatched pairs and tests
  never observe or persist an intermediate mismatch.
- Custom-position decoding enforces board-specific ownership, nonempty exact
  contact, and single selection. Generic conversion and cross-board copying
  strip both exact IDs while preserving semantic depth unless explicitly
  changed; same-board hand materialization that retains the exact contact
  retains the position and depth.
- Generic requirements remain board-agnostic and contain no invented setup.
- Custom editor round trips contact + position and keeps one contact selected
  while depth changes.
- Legacy routines/history decode, new configuration snapshots round trip, and
  historical stale IDs are not rewritten.
- Snapshot tests reject null, partial, unknown, malformed, and unselected-key
  configuration data but accept an empty materialized depth map. Port
  `jug-outer-rim` and `pinch-body` snapshots still record position,
  presentation, and actual model hash with `{}`. Historical structural
  validation runs without loading a current package, while new writes verify
  membership, the exact complete set of known effective/base depths, and
  presentation model hash against the resolved board.
- Activity recording uses the selected presentation hash, not the default hash.

### Workout-state tests

- Initial readiness, confirmation during rest, rest-expiry pause, no-rest
  transition, same-configuration continuation, pause/resume, skip, jump,
  rewind, and restart all preserve the confirmed-configuration invariant.
- No authored timer accrues and no countdown audio continues during setup wait.
- The board view cannot diverge from the frozen resolved target.

### Model, suspension, and ODR tests

- Import and native model tests cover all eight USDZ/descriptor pairs, all
  authored positions, highlighting, nearest-contact picking, clear/reappear,
  orbit/reset, and model switching.
- Port-A-Board tests prove `pinch-side` highlights and picks the deliberately
  re-authored narrow side body, never the batch `outer-pinch-opposition` bottom
  band, and prove no `outer-lower` position remains.
- Both Nature packages prove that selecting `pinch-60` in `pinch-side`
  highlights the complete reviewed upper-and-lower multi-node contact as one
  contact. The standard Mini also proves `pull-up-jug` highlights only the
  manually partitioned internal broad recess in `front-upright`.
- The closed cord audit discovers all migrated presentations. Every canonical
  pose passes length, clearance, framing, self-intersection, non-picking, and
  accessibility checks.
- Staging proves descriptors remain bundled and exactly eight USDZ assets enter
  ODR for these packages. Offline/missing/hash-mismatch paths show explicit
  unavailable state with no raster or stale-model fallback.

### Human review

- Model packages are read-only in Workbench. Every 3D contact binding,
  corrected source partition, import mapping, and reimport result is reviewed
  through retained importer/reimport reports and render artifacts, then in the
  current-source app. Workbench is used only for applicable pre-migration
  raster paths and contact metadata; it is not presented as a model-geometry
  editor or as proof of model binding correctness.
- Current-source visual review explicitly covers Port-A-Board `pinch-side` and
  both Nature `pinch-side` poses, including the complete multi-node highlight,
  correct side/recess visibility, suspension junctions, and reset pose.
- Current-source iOS Simulator review uses the repository
  `validate-hang-ten-ios` workflow and covers every board, position, Plateau
  depth, active-contact state, cord junction, camera reset, board detail,
  routine editor, setup prompt, portrait/landscape layout, Dynamic Type, and
  VoiceOver labels.
- Plateau review confirms the blocker is visible but never selectable and that
  all three configurations highlight the same stable oak contact.
- For each Plateau configuration, retained normal and rear/oblique views of
  the corrected source and final shipped USDZ prove to the human reviewer that
  every screw/mounting hole is removed and capped while the lower open cord
  exits/grooves remain intact. Each approval follows candidate generation at
  the actual review time and binds the exact source/model and relevant render
  hashes; the current-source app review repeats this visual check at all three
  depths before final acceptance.
- Review artifacts and external resources follow workspace ownership and
  cleanup rules.

The standard package validation, full HangboardPackages tests, affected model
tool tests, cord clearance/audit lanes, focused XCTest suites, native build,
and `git diff --check` must pass before completion. A blocked native lane is
reported as blocked; CLI validation does not substitute for it.

## Implementation boundaries

The work may change the schema-v3 readers/writers, board-position domain,
contact resolution, custom routine persistence/editor, board detail, workout
session state, activity recording, ODR/staging tests, model import outputs,
the six packages, and the closed source/cord audits. It should reuse the
existing model renderer, position-transition semantics, transient suspension
renderer, ODR lease, and cache architecture unless a focused failing test
demonstrates a necessary runtime defect.

The migration must not broaden into unrelated board cleanup or training-plan
content. Every changed physical fact must trace to Appendix A; every numeric
display estimate must be labeled as an estimate in the source/cord audit.

## Rejected alternatives

- **Three Plateau products:** rejected because the manufacturer sells one base
  product with a reversible blocker.
- **Three Plateau contacts:** rejected because the same oak surface remains the
  physical contact; the blocker changes usable depth.
- **One 10–18 mm depth range:** rejected because it falsely implies continuous
  adjustability and loses the required setup transition.
- **A parallel configuration registry:** rejected because `BoardPosition`
  already owns physical setup and presentation selection.
- **Default/first-position resolution:** rejected because it silently changes
  prescribed depth and makes declaration order behaviorally significant.
- **Splitting the Port-A-Board 30 mm surface by finger use:** rejected because
  the approved visual set supports one continuous cavity.
- **Treating the standard Mini outer top as the jug:** rejected by the approved
  exact-revision views; the jug is the internal recessed cavity/body.
- **Descriptor subsets per presentation:** rejected because every supplied
  model represents the complete board revision and the existing full-inventory
  descriptor invariant remains useful.
- **Raster fallback or mixed media:** rejected because stale 2D geometry would
  create a second selection authority and conceal model failures.
- **Baked cords or hidden-route reconstruction:** rejected because suspension
  is transient metadata and the sources do not establish hidden routing.
- **Image-driven geometry automation:** rejected by the repository's direct
  authoring policy and by the need for deliberate semantic review.
- **A schema-version fork solely for additive fields:** rejected for this
  coordinated app/package rollout; backward compatibility is new-reader to
  old-data, not old-reader to new-data.

## Appendix A: approved exact-revision manufacturer evidence

The following 28 records are the complete evidence set approved by the human
operator on 2026-09-20. Hashes identify retained bytes captured on 2026-09-19;
live URLs may later return different content. These records support product
identity, inventory, manual geometry decisions, suspension review, and visual
comparison only.

### Tracked snapshot contract

Implementation must promote all 28 approved files byte-for-byte from the
workspace-owned ignored capture at
`.context/sweet-hamster-batch03-research/evidence/` into repository-tracked
regular files. It must not re-download, re-encode, resize, minify, or otherwise
replace the approved bytes. A URL-only record, symlink, external absolute path,
ignored file, or pointer to another checkout does not satisfy retention.

The tracked machine-readable source audit contains one closed record per
reference below. Every record explicitly stores `publisher`, exact `url`,
`sourceTier: "manufacturer"`, full `snapshotSHA256`, unique repository-relative
`snapshotPath`, the evidence-specific `supportClaim`, and a complete
`humanApproval` object with `approved: true`, a nonempty reviewer/audit
identity, `reviewedAt: "2026-09-20"`, and review notes. These values are not
inherited from another record even when publisher and product are shared.

The validator discovers exactly these 28 records and rejects duplicate refs,
URLs where distinct views are required, or snapshot paths. For each record it
resolves `snapshotPath` beneath the repository, verifies that it is a tracked
regular file rather than a symlink or external resource, hashes the bytes, and
requires exact equality with `snapshotSHA256`. The support claim and approval
must also be nonempty and structurally complete.

| Ref | Required tracked `snapshotPath` |
| --- | --- |
| AE-1 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/aelith-cyclops-011/product-page.html` |
| AE-2 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/aelith-cyclops-011/front-back.jpg` |
| AE-3 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/aelith-cyclops-011/in-use.jpg` |
| NU-1 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-nug/product-page.html` |
| NU-2 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-nug/front.jpg` |
| NU-3 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-nug/reverse.jpg` |
| NU-4 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-nug/in-use.jpg` |
| PA-1 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-port-a-board/product-page.html` |
| PA-2 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-port-a-board/front.jpg` |
| PA-3 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-port-a-board/reverse.jpg` |
| PA-4 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-port-a-board/side.jpg` |
| PA-5 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/frictitious-port-a-board/in-use.jpg` |
| NS-1 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini/product-page.html` |
| NS-2 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini/front-original.jpg` |
| NS-3 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini/reverse-original.jpg` |
| NS-4 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini/oblique-original.jpg` |
| NS-5 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini/in-use-original.jpg` |
| NK-1 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini-karma8a/product-page.html` |
| NK-2 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini-karma8a/front-original.png` |
| NK-3 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini-karma8a/reverse-original.png` |
| NK-4 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini-karma8a/oblique-original.jpg` |
| NK-5 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/nature-stone-hanger-mini-karma8a/in-use-original.png` |
| PL-1 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/plateau-lifting-edge/product-page.html` |
| PL-2 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/plateau-lifting-edge/front.png` |
| PL-3 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/plateau-lifting-edge/oblique.png` |
| PL-4 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/plateau-lifting-edge/blocker-15.png` |
| PL-5 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/plateau-lifting-edge/blocker-10.png` |
| PL-6 | `docs/source-audits/2026-09-20-hangboards-batch-03-evidence/plateau-lifting-edge/oak-blocker-in-use.jpg` |

| Ref | Publisher and evidence | Exact manufacturer URL | Retained SHA-256 | What the retained bytes support |
| --- | --- | --- | --- | --- |
| AE-1 | Aelith Equipment — product page | <https://aelithequipment.com/product/011-blue-x-black-cyclops-portable-hangboard/> | `1f802675e64e2f9850542622cef9fb44f34eb7d4ae01ce502e5b610daddd9eb0` | Exact #011 Blue × Black identity, one 20 mm edge, supplied-cord context, and exact gallery association. |
| AE-2 | Aelith Equipment — front/back visual | <https://i0.wp.com/aelithequipment.com/wp-content/uploads/2025/05/011CyclopsProductSpread.jpg?fit=2160%2C2160&ssl=1> | `fc40128d4eaf51c260201e84bb1d8fde7d5224c49a42bd1349c93e4ab56cdeff` | Exact color, teardrop body, single recessed mono surface, reverse profile, and cord attachment at the narrow end. |
| AE-3 | Aelith Equipment — in-use/context visual | <https://i0.wp.com/aelithequipment.com/wp-content/uploads/2025/05/img_0159-2-1.jpg?fit=2000%2C1333&ssl=1> | `0226a85fcc54586b7b12ff09b15154ff6aaf190f47fb16142d2fceed95a7a30c` | The same form and recessed surface from a distinct view plus the single-cord knot and portable suspension arrangement. |
| NU-1 | Frictitious Climbing — product page | <https://frictitiousclimbing.com/products/the-nug> | `eb44cc7bf24b53b721183cae2c42542863299c4ab193171a8d3be5ea6b9444de` | Exact product identity, 25/20/13/8 mm edges, 40 mm jug, 60 mm pinch, material, and gallery provenance. |
| NU-2 | Frictitious Climbing — front visual | <https://frictitiousclimbing.com/cdn/shop/files/NUG-Front-1.jpg?v=1780420316&width=3840> | `7c476ab558d6defdacf4d4105e09cbffe99edaf5455c6ea04e5f00b812f2a384` | 25 and 20 mm face orientations, recesses, rounded body, and two suspension passages. |
| NU-3 | Frictitious Climbing — reverse visual | <https://frictitiousclimbing.com/cdn/shop/files/NUG-Front_3aac9546-2dcb-447e-bb5a-4dea686e2818.jpg?v=1780420315&width=3840> | `c3e36dc47c9e4542321d155c337d91a3511ef6d6f9dfbcd0bd40100ce26f8202` | 13 and 8 mm reverse orientations and their relationship to the same body and paired passages. |
| NU-4 | Frictitious Climbing — in-use visual | <https://frictitiousclimbing.com/cdn/shop/files/NUG-Product-4.jpg?v=1716309065&width=3840> | `146cbf91b840b7e6ae2063877c08729ae869bbb07da5e478300f9fdbeffd9ecd` | Portable/loading use, scale in hand, outer-body grip context, and paired lead-cord behavior. |
| PA-1 | Frictitious Climbing — product page | <https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard> | `71f455b60e3f5f15511c22ca24d17c17d8928ef5bf8f296d3ed9207ca8dcfb55` | Exact identity, marketed edge-depth language, jug/pinch uses, mounting/suspension context, and gallery provenance. Its wording alone does not establish a second physical 30 mm surface. |
| PA-2 | Frictitious Climbing — front visual | <https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840> | `1509f81ed1dcf960a8ee1e91424e538de5aa890698b351a12fe2f1c36e4859e1` | Front 20, 25, and one continuous asymmetric 30 mm recess, center body/rim, and paired cord passages. |
| PA-3 | Frictitious Climbing — reverse visual | <https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840> | `38522abf6ccfa4a0f18dac57e5bbbf9a6290de4cd6a030756248f1a0314f70f4` | Reverse 15, 12, 8, and 10 mm recesses and continuity within one body. |
| PA-4 | Frictitious Climbing — side visual | <https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840> | `61221d7cb34edf3c5fd13e2300045050a0d7149424be9c5bcf8ded6c021df8e7` | Board thickness, rounded side profile, face relationship, and external cord path. |
| PA-5 | Frictitious Climbing — in-use visual | <https://frictitiousclimbing.com/cdn/shop/files/PAB-homewall-1.jpg?v=1784658897&width=3840> | `a2cc5ec6e79272241c8f24891d91f89d075c3ebadc69b731d082a20775a43cd3` | Scale in hand, center ridge/30 mm region use, and paired lead-cord arrangement from both front passages. |
| NS-1 | Nature Climbing — Stone Hanger Mini Oak product page | <https://natureclimbing.com/products/stone-hanger-mini-oak> | `782f39e5a7e4a04c61e812e28f581094c95b1d6cbbda7eb9b0bb3a82cca16369` | Exact Oak identity and four uses: 15 mm granite edge, 15 mm incut wood edge, 60 mm pinch, and smooth pull-up jug. |
| NS-2 | Nature Climbing — front visual | <https://natureclimbing.com/cdn/shop/files/Oakminihanger1.jpg?v=1774539696> | `3aae064c37d7eef11e7874acaabbaca0194a1caa357e2bff1bbfb83faf093ff7` | Exact front geometry, stone insert, wooden recess/jug cavity, 15 mm marking, and side cord exits. |
| NS-3 | Nature Climbing — reverse visual | <https://natureclimbing.com/cdn/shop/files/Oakminihanger2.jpg?v=1774539697> | `09a4926269b291354b171fdac6e20365a6c9c66528bb4275b8cb56b20b8f1eae` | Solid reverse, exact branding/revision, rounded outer body, and both cord exits. |
| NS-4 | Nature Climbing — oblique/side visual | <https://natureclimbing.com/cdn/shop/files/Oakminihanger3.jpg?v=1774539696> | `383cdd3665f1e30a0dc8443959d7442e65780dbd27b71bc597efc9a1b924f685` | Board thickness and open side-groove routing for paired cord leads. |
| NS-5 | Nature Climbing — in-use/context visual | <https://natureclimbing.com/cdn/shop/files/MiniHanger-environment-11.jpg?v=1774539799> | `f17ceb9007a1f00ad19859c6fdf4bbd0c8a48b5f8d1cdbf169c6de46ffeb076e` | Front/recess geometry from a distinct oblique view and portable cord context. |
| NK-1 | Nature Climbing — KARMA8A product page | <https://natureclimbing.com/products/mini-hanger> | `b962a7df9b6169c12993aa86b8c7d189941cad4acc373fac4f6064987bc04666` | Exact KARMA8A identity and only three supported families: 15 mm granite, 15 mm wood, and 60 mm pinch; no separate jug. |
| NK-2 | Nature Climbing — front visual | <https://natureclimbing.com/cdn/shop/files/Untitled_design_a3abac48-3dbc-4913-bc3e-15c8b2a9e85d.png?v=1774607004> | `3267c96f30e9576b1b66f769d83722cac6c55322c9ad6491cda82ea3910f7743` | Dark-oak front, stone insert, wooden recessed edge, 15 mm marking, collaboration art, and cord exits. |
| NK-3 | Nature Climbing — reverse visual | <https://natureclimbing.com/cdn/shop/files/Untitled_design_1.png?v=1774607067> | `412059dc91cb4b564d450b4065fdf467618d1d981c9568cb5346983ae7653de0` | Solid reverse, collaboration branding, rounded body, and side cord exits. |
| NK-4 | Nature Climbing — oblique/side visual | <https://natureclimbing.com/cdn/shop/files/P11_efb30f02-ff67-4d8d-a247-80a40873e358.jpg?v=1774607067> | `95292e0c642c3a3de255e66e0c09cd8b8ddcd6802a724a8bbd429d7647b58cbf` | Both faces, board thickness, pinchable outer nodes, and paired leads in open side grooves. |
| NK-5 | Nature Climbing — in-use visual | <https://natureclimbing.com/cdn/shop/files/2_8414fdb3-da87-4e09-bfd7-acd77452106c.png?v=1774607067> | `a962fc997461aed38bfaee08071681b27b12f671406c216947f7b21ce6bb2df8` | Wooden recessed-edge use, scale, hanging orientation, and paired leads around an overhead support. |
| PL-1 | Plateau Climbing — product page | <https://www.plateauclimbing.com/products/plateau-lifting-edge> | `4c63ca9c62f1dbd686e823ceb2af3366a5f8381daaafe92b024ad7743a8a74b3` | Exact identity, one physical oak edge, 18 mm base, reversible 15/10 mm blocker configurations, loading use, and gallery provenance. |
| PL-2 | Plateau Climbing — front visual | <https://www.plateauclimbing.com/cdn/shop/files/IMG_1171.png?v=1773212075&width=3840> | `7a854f73c876dffdff07251e4ab4cd5128014c3f51a3d31e14ecf00ac36fe7a7` | Front assembly, one oak edge, metal body, lower curled section, and cord loop emerging from both open ends. |
| PL-3 | Plateau Climbing — oblique visual | <https://www.plateauclimbing.com/cdn/shop/files/IMG_1166.png?v=1773212075&width=3840> | `bb12d65453f77a917e048eb7ed09582c0ee4d96d6cf265973748f99cfc39191d` | Oak edge/metal backing side profile and cord route through the lower curled extrusion. |
| PL-4 | Plateau Climbing — 15 mm blocker visual | <https://www.plateauclimbing.com/cdn/shop/files/IMG_1168.png?v=1773212075&width=3840> | `4e666f921ffebdb287f383eb1330d5eb8aafab591cea5cfc488667368ee312b0` | Reversible blocker installed for 15 mm effective depth on the same board/cord assembly. |
| PL-5 | Plateau Climbing — 10 mm blocker visual | <https://www.plateauclimbing.com/cdn/shop/files/IMG_1161.png?v=1773212075&width=3840> | `b2a474441847de209fa85307383d0822f462801650f1f188bd0b1d8d8d49e243` | Blocker reversed for 10 mm effective depth while preserving one physical oak contact. |
| PL-6 | Plateau Climbing — oak/blocker in-use visual | <https://www.plateauclimbing.com/cdn/shop/files/45_edited.jpg?v=1773212075&width=3840> | `a4a037eccdd1de212333f3f4482fab309ff385720768bb60c61606a9fb209e75` | Scale in hand, oak edge/blocker as one configurable grip, paired lead-cord loading setup, and outdoor use context. |
