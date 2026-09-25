# J Bryant FTG-32 Portable Grip Block 3D Design

**Status:** approved design and exact-revision evidence set  
**Evidence review date:** 2026-09-20  
**Human approval:** supplied in the design conversation on 2026-09-20

## Outcome

Add one model-only schema-v3 package for one wooden grip block from the retail
pair sold as J Bryant part `FTG-32`, Amazon ASIN `B0FZGY19T9`. The app presents
one block, one physical cord loop, and two selectable contacts. Both contacts
belong to the one-sided recessed face: opposing stepped 16 mm and 25 mm ledges
are selected by rotating the block 180 degrees in its face plane.

This package reuses the existing `captain-fingerfood.dual`
`pairedLeadCord` presentation contract. It does not require a new suspension
type, parser branch, solver, renderer, or schema field.

## Exact product and revision

| Field | Accepted identity |
| --- | --- |
| Brand/manufacturer as listed | J Bryant |
| Product | “1 Pair Wooden Hangboard for Climbing Training – Dual-Pocket Grip Blocks…” |
| Part number | `FTG-32` |
| Amazon ASIN | `B0FZGY19T9` |
| Seller | J Bryant FF, seller ID `A2LE8CI3MKZB0S` |
| Canonical product URL | <https://www.amazon.com/dp/B0FZGY19T9> |
| Revision-defining retail presentation | Pair of beech blocks, yellow/orange cords, and two black carabiners |

The Amazon listing is merchant-authored commerce evidence. No independent J
Bryant manual, CAD drawing, technical sheet, or manufacturer product page was
found. The storefront
<https://www.amazon.com/stores/JBryant/page/8CB2A3B6-0CAF-42D8-95A9-DD3D87E7DEB2>
and seller profile
<https://www.amazon.com/sp?ie=UTF8&seller=A2LE8CI3MKZB0S> support seller
identity only; they are not geometry sources.

## Approved evidence set

The approved set is the canonical Amazon listing, the seven exact images the
user supplied from that listing's gallery, the four independently fetched
exact-ASIN media records below, and the user's topology confirmations. Geometry
work must not silently add or replace a source. Any later source requires a new
audit entry and human review.

### Independently fetched exact-ASIN media

These hashes identify the fetched bytes reviewed during source research, not a
later response from the same mutable URL.

| View | Source URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| Suspended pair/front | <https://m.media-amazon.com/images/I/61qkCE436dL._AC_SL1500_.jpg> | `eef9a2ea5bbb6ba5a6da4d224611c4d7cdf5cdc79c86e7f7ada7c8e39c6fef87` | Retail pair, independent loop per block, two visible leads per block, supplied carabiners |
| Beech/material oblique | <https://m.media-amazon.com/images/I/71Mr+u-2MML._AC_SL1500_.jpg> | `13e329556225441266c61d7ee4f0aea8bdb49129c02450cd2ae1756fce50adb7` | Beech appearance, exterior rounding, recessed face, two openings |
| Dimension/configuration graphic | <https://m.media-amazon.com/images/I/71vG8G2P8NL._AC_SL1500_.jpg> | `925b818fbfea32f4446d532151d0faa76c9d53a3ba3847f679081210fcc8aa54` | 105 × 77 × 37 mm block; 80 mm carabiner; illustrated 145 mm and 260 mm suspension heights |
| Contact-depth guide | <https://m.media-amazon.com/images/I/71a1HaMmk3L._AC_SL1500_.jpg> | `db495e2c910bcc4965d2005ebf62859a791d809058454e032c61d2e6a925353a` | Published 16 mm and 25 mm contact depths |

A verification fetch later on 2026-09-20 returned different bytes for the
dimension URL (`27b2689f3b79b63610d5d26f70693f78e2197aa5d1f7d610bda3c961d2b27874`).
This confirms that the URL is mutable: the source-research hash above and the
separately hashed user attachment are the reviewed records, and an
implementation must not silently accept later URL bytes as equivalent.

### Exact user-supplied gallery images

The conversation attachments are independently identified because the upload
pipeline resized or transcoded some Amazon media. Visual correspondence does
not imply byte identity. Implementation must retain these exact bytes in the
source-audit packet before relying on them; their temporary attachment paths
are not package assets.

| Attachment | Dimensions | SHA-256 | Review role |
| --- | ---: | --- | --- |
| 1 — suspended pair/front | 679 × 683 JPEG | `f276704568bb877405617446e7527183ad81291df8e9231611487e52cadd533c` | Complete product/pair and suspension overview |
| 2 — material/oblique | 1500 × 1500 JPEG | `13e329556225441266c61d7ee4f0aea8bdb49129c02450cd2ae1756fce50adb7` | Exterior, recess, openings, and wood appearance |
| 3 — dimensions | 1500 × 1500 PNG | `4551e29ccb0202d769ff6b7d4cf66e0308fb6cffe000059c0b6bafa313d7247c` | Published dimensions and illustrated suspension configurations |
| 4 — depth guide | 1500 × 1500 PNG | `119395ee56ab6f534558991c5167cd0d7f74578115b39b242ea1d293133e101c` | Published shallow/deep depth labels |
| 5 — weight-loading lifestyle view | 1498 × 1500 PNG | `d137c6538a7d13352899b7d7a3bc246b6c76586eba5259cd294a5efeb60e973c` | Contextual one-block use; no new measurements |
| 6 — one-hand loading lifestyle view | 1500 × 1500 PNG | `61c9fb581ed214f2ae76d578147aabb63d894e6dd3f41ec5c2f2fb9abd05561f` | Contextual one-block use; no new measurements |
| 7 — suspended training lifestyle view | 1500 × 1499 PNG | `3bd9cffa6952e7ad24c8ac57006e90cff81117fc22f3d59a35e8b9af144f5dd7` | Pair-in-use context; no new measurements |

### Human topology confirmations

The user supplied the following product facts in the 2026-09-20 design
conversation:

- the product is one-sided;
- the recessed face has stepped contacts;
- the 16 mm and 25 mm holds are opposing horizontal ledges in the same front
  recess and are selected by rotating the block 180 degrees;
- the two cord holes are centered rather than defining an intrinsic “top”;
- one cord forms one loop by passing through the two holes and around the back;
  and
- the requested app presentation is one block and one loop, following the
  already shipped DUAL presentation pattern rather than displaying the retail
  pair.

The user then approved both the proposed package/contact design and the final
build-and-validation design. These confirmations close the topology questions
left unresolved by the commerce gallery. They do not establish unpublished
numeric measurements.

## Facts, estimates, and omissions

### Source-backed facts

- The retail item is a matching pair, but each modeled block measures
  105 × 77 × 37 mm (4.13 × 3.03 × 1.46 in).
- The listed material is beech wood.
- One block has one recessed working face with opposing stepped 16 mm and
  25 mm ledges.
- Rotating the block 180 degrees in its face plane changes which ledge is in
  the usable lower orientation while keeping the recessed face toward the
  athlete.
- One cord loop passes through the two centered holes and returns around the
  rear of the block.
- The listing includes ropes and carabiners. The diagram labels a carabiner as
  80 mm long and depicts 145 mm and 260 mm suspension heights.
- Amazon lists 1.2 lb for the item. This is treated as a retail-set listing
  weight, not a measured mass for one block.

### Authored display estimates

The following values are necessary for a credible display model but are not
published product measurements: outer corner radii; recess width, height,
floor, wall angle, and transitions; ledge lip radii and exact mesh extents;
back profile; hole diameter, spacing, and exact coordinates; wood grain and
finish shader; cord radius, material appearance, rest length, and color;
anchor offset; canonical camera framing; and any small pose tilt or translation.

Every such numeric value must be labeled `displayEstimate` in the source audit
or package provenance as applicable. The 145 mm and 260 mm illustrations are
not total rope lengths and must not be converted into `restLength`. Contact
depths and overall dimensions remain sourced facts, not estimates.

### Unsupported and deliberately omitted

Do not add a rope length, rope or carabiner strength/rating, cord material,
knot type, coating specification, per-block mass, load capacity, safety claim,
finger capacity, handedness, training prescription, grip recommendation, or
physiological claim. Do not model a carabiner, bar, hook, weight, hand, second
block, knot, or mounting environment. Omit optional package metadata rather
than filling it from lifestyle copy or visual inference.

## Package and contact contract

The implementation uses these stable identities unless a schema validator
requires a purely syntactic adjustment that preserves their meaning:

| Concept | ID/value |
| --- | --- |
| Package slug | `j-bryant-ftg-32` |
| Board ID | `j-bryant.ftg-32` |
| Revision ID | `amazon-b0fzgy19t9-ftg-32-2026-09` |
| Display name | `FTG-32 Portable Grip Block` |
| Product URL | `https://www.amazon.com/dp/B0FZGY19T9` |
| Dimensions string | `10.5 × 7.7 × 3.7 cm` |
| Equipment object | `primary` |
| Presentation | `primary` |
| Model asset | `assets/primary.usdz` |
| Descriptor | `assets/primary.model.json` |
| Contacts | `edge-16`, `edge-25` |
| Positions | `edge-25-down`, `edge-16-down` |

`contacts[]` is the only logical contact inventory. `edge-16` is named
“16 mm edge” and has exact depth range 16–16 mm. `edge-25` is named “25 mm
edge” and has exact depth range 25–25 mm. Both have `kind: "edge"`, supported
by the user's confirmation that they are opposing ledges. Neither receives a
side, paired-contact relationship, shape, finger capacity, hand capacity, or
grip-type claim.

Both positions use presentation `primary` and expose exactly one contact:

| Position | Contact IDs | Canonical orientation |
| --- | --- | --- |
| `edge-25-down` | `["edge-25"]` | Authored baseline with the 25 mm ledge in the usable lower orientation |
| `edge-16-down` | `["edge-16"]` | Exactly 180 degrees about model +Z from the baseline, preserving the one-sided face toward the camera |

The 25 mm baseline is only a deterministic authoring choice; it is not a claim
that the deeper edge is preferred or safer. The presentation is original,
model-only, and default. The physical face aspect ratio is 105 / 77
(`1.363636…`); the final package uses the validator-compatible rounded value.

The package contains exactly `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`. It contains no PNG, raster fallback,
`contactGeometry`, source photos, or editable Blender file.

## Analytic model design

Author the block directly in Blender in the `hang-ten-board-v1` frame, in
metres, with +X right, +Y up, and +Z toward the athlete. Begin from the sourced
105 × 77 × 37 mm envelope. Construct the rounded solid, one-sided recess,
opposing stepped ledges, and two through-holes analytically. Use the approved
views for deliberate visual judgment only; do not trace, register, detect,
segment, vectorize, auto-crop, generate contours, or infer dimensions from
pixels.

The USDZ contains:

- nonselectable beech body geometry, including recess floor/walls and the two
  visible through-holes;
- a separately tagged selectable surface mesh for `edge-16`;
- a separately tagged selectable surface mesh for `edge-25`; and
- no cord, rear loop segment, anchor, carabiner, knot, mounting scene, or
  raster-derived geometry.

The two contact meshes must cover only their deliberate physical ledges. The
descriptor may bind multiple disconnected nodes to one contact only if that is
required to represent one continuous physical ledge faithfully. Recess walls,
hole walls, and the opposite ledge must not highlight with the selected
contact.

The geometry author retains an editable `.blend`, source-versus-estimate
report, and front/oblique/clay review renders under a workspace-owned
`.context/nervous-frog-j-bryant-ftg-32/` path. The implementation must compare
the wood material and render treatment side by side with a similar shipped
portable wood model. Generated evidence and editable source do not enter the
package.

Use `Tools/HangboardModels/contact_model_package.py` only to transport the
deliberately tagged geometry. It must not repair topology or invent contact
partitions. Reimport the exported USDZ into an empty scene and generate the
descriptor from importer-visible triangles. The descriptor binds both exact
contact IDs, records read-only mesh-derived bounds/centers, and hash-binds the
USDZ bytes. Export or reimport failure is a failed model, not permission to
hand-author the descriptor or add fallback geometry.

## Suspension representation

The physical object has one loop. The runtime representation intentionally
shows only its two exterior leads:

```text
one invisible shared anchor
  -> left visible lead -> left hole mouth
  -> right visible lead -> right hole mouth
rear connecting segment intentionally not rendered
```

Declare existing `type: "pairedLeadCord"` exactly as used by
`captain-fingerfood.dual`. Bind `left-lead` and `right-lead` to two distinct
points on an importer-visible body or attachment node at the visible hole
mouths. They must never bind to `edge-16` or `edge-25` contact nodes. A
validator-required terminal passage record may identify each same visible
mouth, but the package must not upgrade the known physical holes into a
`twoBranchCord` route or attempt to render the through-hole/rear segment.

The two visible leads meet at one invisible display anchor. Cord geometry is
transient, non-pickable, and absent from accessibility. Anchor offset, lead
rest length, cord radius, material treatment, terminal coordinates, and any
ordered exterior contact points are display estimates derived from the final
reviewed model and must pass every-pose clearance. The cord is not baked into
the USDZ.

Both canonical suspension poses use the same rotations as their corresponding
positions. The complete board pose, attachment endpoints, cord solve, and
camera update atomically when the selected position changes. If a pose needs
attachment-point overrides to preserve left/right ordering after the 180-degree
roll, those overrides remain package data and must use both lead IDs. No
renderer special case is permitted.

The known rear loop routing is retained in the source audit as a physical fact
and deliberate display omission. It is not represented as an invisible
interior connection and does not justify a new suspension topology.

## Source audit, catalog, and ODR integration

Implementation must add an exact-revision source audit that maps every
metadata field, contact, position, attachment fact, and estimate to this
approved evidence. It must retain the approved image bytes by hash and record
the commerce-source caveat. It must also update the closed model-cord audit
with:

- `packageID: "j-bryant.ftg-32"`;
- `sourceFact: "documentedSuspension"`;
- `decision: "represented"`;
- `topology: "pairedLeadCord"`;
- the approved exact-revision evidence and 2026-09-20 human approval; and
- a ruling that the two visible leads are represented while the known rear
  connecting loop segment is deliberately omitted.

Add the package to every closed board/model/orientation inventory and every
real-package parser, staging, model, and suspension fixture required by the
current repository. Add the USDZ to the Xcode project's board-specific Apple
On-Demand Resource tag. `board.json` and the descriptor remain ordinary bundled
metadata; `primary.usdz` is the only ODR asset. Staging must preserve the source
USDZ bytes, descriptor hash, and package identity exactly.

No raster fallback is added. Unsupported, missing, hash-mismatched, or
invalid model/suspension data fails closed to the existing explicit unavailable
state.

## Validation and native visual review

The implementation starts with focused failing inventory/audit/package tests,
then proves the final package through the existing retained tools. At minimum:

1. validate the schema-v3 package and final catalog inventory;
2. compile/reimport the USDZ and validate exact model dimensions, material,
   complete node roles, two-contact bindings, descriptor canonicalization, and
   SHA-256 identity;
3. validate the closed suspension audit and all-pose production cord
   clearance, length, self-intersection, and framing checks;
4. prove staging parity and the board-specific ODR registration while keeping
   only the USDZ in ODR;
5. run affected model-tool pytest suites and package hard-cut tests;
6. run focused `BoardPackageStoreTests`, `SuspendedBoardPresentationTests`,
   `BoardModelTests`, native picking tests, and the full affected Swift
   test/build lane; and
7. run `scripts/hangboard-packages.sh validate --root Hangboards
   --final-inventory`, `scripts/hangboard-packages.sh status --root Hangboards`,
   direct JSON parsing, and `git diff --check`.

Current-source iOS Simulator review must follow `validate-hang-ten-ios` on an
owned isolated simulator. Retain app-rendered evidence for both
`edge-25-down` and `edge-16-down`, including:

- canonical front and oblique views with credible one-block scale and beech
  treatment;
- active highlight for each ledge and cleared/reappearing selection;
- a visible, continuous paired-lead cord with no front-face/recess collision,
  clipping, or self-intersection;
- proof that cord geometry is neither pickable nor accessible and that the
  active contact remains the nearest descriptor-bound hit;
- manual orbit followed by canonical reset;
- workout-driven resolution of both positions; and
- the explicit unavailable state under a focused invalid-asset or invalid-
  suspension test.

Human visual review compares the normal and highlighted model to the approved
front, oblique, dimension, and depth-guide images. It must confirm the
one-sided recess, opposing stepped ledges, centered holes, 180-degree position
change, contact-highlight coverage, and suspension silhouette. Passing hashes
or inventory checks alone is not geometry approval.

## Out of scope

- Displaying both blocks from the retail pair, two anchors, or two simultaneous
  block selections.
- A new suspension schema, parser, solver, renderer, or board-specific runtime
  branch.
- Rendering the rear cord segment, hole-interior cord, carabiner, knot, bar,
  hook, ceiling, hand, or weights.
- Rope dynamics, swing, elasticity, friction, load calculation, structural
  analysis, or safety certification.
- A raster presentation, fallback image, canonical 2D path, or Workbench model
  editing.
- Training routines, exercise names, repetitions, timing, coaching copy, grip
  prescriptions, or claims copied from the listing's lifestyle graphics.
- Converting illustrated suspension heights, set weight, or visually estimated
  dimensions into product facts.
- Manufacturing CAD accuracy for unpublished recess, hole, radius, or cord
  measurements.

## Acceptance criteria

The change is complete only when the exact package identity and approved source
set are auditable; one source-dimensioned block contains exactly the two
reviewed selectable ledges; the two positions differ by the approved
180-degree face-plane rotation; the existing `pairedLeadCord` path shows one
loop as two non-pickable visible leads without a rear segment; package, model,
cord, inventory, staging, ODR, native test, and full build lanes pass; and
current-source simulator captures receive human visual approval. No unsupported
measurement, training claim, second block, or runtime feature may be added to
reach that result.
