# Lessons from the FreeCAD hold-authoring migration

Hard-won, board-agnostic lessons from migrating hangboards to native FreeCAD
sources (pilot: `lattice-triple-rung`; then `metolius-rock-rings-3d`; then
sculpted `lattice-mxedge-lift-small`). Read with
`docs/freecad-authoring-migration.md`. The point of writing these down is to
avoid repeating the same detours.

## 1. Decide the goal and the acceptance bar before you iterate

- Two different goals, two different costs: "author a CAD model that looks
  right" vs "ship a board into the app". The app renders from a *compiled* asset
  with a hash-bound descriptor, so shipping needs the whole pipeline — but only
  **once**, at the end.
- **Lean inner loop:** edit the throwaway FCStd-authoring script (under
  `.context/`, never committed) -> compile -> render / screenshot -> decide. Run the pytest suites, the delivery lock, and
  `compare_exports` as a release gate, not per tweak.
- Triage the reference **first**: is it a constant cross-section (extruded
  profile -> reproduces exactly) or a genuinely sculpted closed shell (rounded
  lip, scooped pockets -> a solid native model cannot match it)? If sculpted,
  declare the accepted deviation up front and stop chasing the tolerance; chasing
  an unreachable `compare_exports` limit burned roughly a third of one session.

## 2. Web-search is a required cross-reference, not a geometry source

Agents **must** web-search the manufacturer / product pages to cross-check
overall dimensions, grip depths, and product identity against `board.json` and
against mesh / Git-reference measurements. Prefer manufacturer pages; clearly
label commerce and other secondary sources.

This is not optional research and not a primary geometry source. Do not invent
unsupported numeric facts from search, invent hold geometry from catalogue copy,
or override mesh-authored shapes without evidence. Still measure the USDZ.

On conflict: record the URL, what that page supports, and what disagrees
(`board.json` and/or the mesh). Prefer manufacturer pages for identity; do not
paper over disagreement by inventing numbers. Rounded catalogue strings (e.g.
"20 × 11 × 5 cm") are especially untrustworthy as millimetre truth — see also
§11 "Product copy is not millimetre truth".

## 3. Diagnose visually, with normals

- Render the node with **normal-shaded (lambert) fills**, not flat fills. A flat
  fill hides the common failure modes.
- A bright/white patch is **over-lit geometry with a normal facing the light**,
  not a hole; a dark patch is under-lit or back-facing geometry, not necessarily
  a hole. Check the actual triangle normals before concluding.
- Fastest repro: read the compiled `.usdz`, project the node, print normals for
  triangles in the suspect region. The iOS rebuild is ~3 min; don't loop on it.
- **Also use an off-the-shelf Hydra render** (`usdrecord` / Storm) of the compiled
  USDZ. It is very useful for development verification: depth steps, through-holes,
  and overall silhouette read more honestly than the custom `preview.py` alone.
  Diagnostic only — never a build input.

## 4. The CAD is the source of truth for hold geometry — use surfaces, not solids

- Author each hold region as an **open surface**:
  - band: `Part::Extrusion` of the profile run (surface);
  - pocket: `Part::Loft` with `Solid = False` (lateral shell, no cap) fused with
    a `Part::Face` on the floor sketch;
  - cord aperture: `Part::Extrusion` with `Solid = False`.
- A **solid** region leaks geometry: a pocket loft's opening cap renders the hold
  flush and hides the cavity, and a `Part::Common` solid carries interior cut
  planes into the export.
- **Orientation is load-bearing.** A cap-free shell oriented as a solid has its
  cavity-facing side back-facing, so the highlight is dark/fragmented. Reverse it
  with **`Part::Reverse`** (parametric — `Source` link, so it survives a
  floor-depth edit and passes the native edit-propagation check). `Shape.reversed()`
  on a `Part::Feature` is static and breaks that check.
- `Part::Reverse` and `Part::Face` are not in the default FCStd allowlist; add
  them to `BUILTIN_TYPES` in
  `Tools/HangboardPackages/src/hangboard_packages/cad_source.py`.

## 5. Region mesh vs body partition — the boundary-matching rule

The compiler partitions the body: each body triangle whose centroid lies on a
region's classification shape is assigned to that region. There are two ways to
ship the region mesh, and each has a sharp edge:

- **Export the region's own CAD surface.** Clean and CAD-owned — but its boundary
  must *exactly* match the body area the partition removed, or you get a hole.
  This holds for a **cut** (a pocket): the body was cut by the same tool, so the
  hole rim equals the region rim. It **fails for a hold that is a sub-region of a
  large planar body face** (a jug band): the planar face tessellates into very few
  triangles, the centroid partition grabs one oversized triangle, and the region
  surface (a different polygon) leaves a huge triangular hole.
- **Export the body's partitioned triangles.** Gap-free and with correct outward
  normals, but the boundary follows the body's tessellation, so a sub-region of a
  coarse planar face is coarse (one big triangle).

**The real fix for sub-region holds:** refine or split the body's large planar
face so the partition boundary is fine — e.g. crack-free subdivision of oversized
triangles before partitioning, or split the face in CAD (a distinct face for the
band). Do not paper over it with a flat overlay; that is wrong for a board whose
holds are non-planar.

## 6. OCCT boolean / loft traps

- `Part::Common(shell, body)` where the shell already lies on the body boundary is
  a **degenerate boolean**: OCCT returns fragments. Only clip a region whose
  construction actually extends past the board.
- A region tool that starts outside the body **inflates `modelBounds`** (e.g.
  `±0.074/0.094` instead of `±0.073/0.092`) and broke ~66 unrelated tests. Clip
  it, or start it on the body surface.
- A ruled loft between two independently-ordered sections **twists into a wedge**.
  Resample both sections by arc length from the same start vertex and direction.
- A uniform inward offset **collapses corners** whose radius is smaller than the
  inset; use the measured floor loop resampled to the opening's vertex order.

## 7. The descriptor is a closed schema — touch all three layers

Adding a field (e.g. `outline` to a contact) requires, together:
- `Tools/HangboardModels/contact_model_descriptor.py` (compile + parse + exact-key
  allowlists, for v1 `contacts` **and** v2 `contactSlots`);
- the Swift decoder `HangTen/Models/BoardPackageStore.swift`
  (`rejectUnknownKeys` will reject an unknown key) + `TrainingModels.swift`;
- the Python package validator
  `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` (closed key
  sets).
Miss one and the build, the app, or the validator fails. Also: derive
`facePlaneAABB`/`center` from the CAD outline so an AABB can't drift when a planar
face tessellates coarsely (this fixed a jug AABB that was ~12 mm off).

## 8. The v2 / attachment path

- `compile_board` must partition **attachments as well as contacts**; the v1
  compiler silently dropped attachment nodes.
- Published-depth validation must key on `ContactSlotID` for v2 and read the depth
  from each instance's `contactIDsBySlotID` (reading `ContactID` there is
  vacuous).

## 9. Prismatic extrusion flattens any local silhouette extremum -- fillets can't fix it, a swept lip can

A `Part::Extrusion` of a 2D silhouette has a lateral surface whose normal is
`(-f'(x), 0, 1)/|.|` -- no dependence at all on the extrusion axis. Wherever the
silhouette has zero slope (`f'(x)=0`) -- and any smooth local min/max, by
definition, has at least one such point -- that normal is *exactly* aligned
with the extrusion's cross-axis across the **entire** extrusion length. On
`metolius-rock-rings-3d` this produced a 57 mm-wide, dead-flat, over-lit
"bright facet" across the full depth at the top-center notch (root cause of a
recurring visual bug). This generalizes: any board whose silhouette is padded
straight through depth (or any other prismatic axis) will show the same bug
at every local extremum of that silhouette, not just at a "notch."

**What does not fix it:**
- A small perimeter `Part::Fillet` on the flat wall's long edges only rounds
  the corner where it meets the front/back faces; the interior of the flat
  wall is untouched.
- A fillet radius large enough to consume the *whole* extrusion length (so
  the two edge fillets meet in the middle) needs radius = half that length,
  and OCCT's `Part::Fillet` reliably fails (`BRep_API: command not done`) at
  or near that exact radius on a polyline-edge silhouette, and can also bulge
  the profile outward past the measured silhouette even when it succeeds at
  a smaller radius.

**What does fix it:** author the rounded lip as primary geometry, not a
fillet:
- Build cross-section profiles at each silhouette-path station: a
  closed 2D wire in the *cross-axis* plane (here, depth x height) whose top
  boundary is a semi-ellipse across the full depth with **vertical tangency**
  at both depth extremes -- z(y) = f(x) - h + h*sqrt(1-(y/depth)^2) -- so it
  blends into the front/back faces with no crease, plus straight sides down
  to a shared floor far below the body, closed across the bottom.
- Consecutive stations must differ *only* in a scalar height shift (same
  point count and order, no rotation/scaling): a `Part::Loft` with
  `Ruled=True` through such congruent sections is then mathematically exactly
  a fixed-orientation sweep (every corresponding point pair connects with a
  straight line whose direction only changes with the height shift), with no
  twisting risk the way a loft between independently-parametrized sections has.
- Taper the height `h` to (near) zero at the ends of the affected span (a
  sine profile over station index works) so the lip fuses seamlessly into
  the untouched geometry outside the span, and clip the tool to exactly the
  same X-span you use to remove material from the body (see the boolean
  traps below) -- a hard discontinuity there is what a fillet-based approach
  was trying, and failing, to smooth.
- Sample the ellipse at **uniform y, not uniform angle**. Equal-angle
  sampling of a curve with vertical tangency bunches samples up near the
  tangent point (chord length -> 0 there); those hairline chords survive
  into the boolean result as `BOPAlgo TooSmallEdge` slivers. Equal-y steps
  bound every chord to at least `2*depth/segment_count`.
- **Do not chase "zero up-facing triangles."** A rounded crest legitimately
  has a triangle or two with a near-vertical normal at its exact peak (a
  physical rounded lip does too) -- that is correct, not a residual bug.
  Measure the *width* of the near-vertical band instead (e.g. triangles
  within 5 deg of vertical), and validate against the reference asset's own
  measured band width under the identical measurement, not against zero.
- **The strict angle-band-width metric and the actual rendered brightness
  can disagree, and eye comparison should win.** A symmetric elliptical
  crest always has a true zero-slope point at its exact peak regardless of
  lip height `h`; increasing `h` narrows the *angular* width of near-vertical
  triangles there (smaller radius of curvature -> tighter peak) but does
  not reduce peak brightness, and in a straight-on lambert render a taller
  lip reads as a **bigger, more dramatic bright dome**, not a smaller
  highlight -- because a light that is not purely vertical still lights a
  wide swath of a deep, steep dip. On this board, a narrow-metric-optimal
  `h=28` (near the maximum before the "meeting fillets" OCCT failure above)
  looked visibly *worse* than a smaller `h=6`, which was the closest match
  by eye to the reference asset's own (much gentler) lambert render. Render
  a sweep and compare by eye against the reference under the identical
  synthetic light before picking a value from a metric alone.

**Two more boolean traps specific to this construction**, beyond the
coincident-surface trap in lesson 6:
- Feeding `Part::Fillet` a base shape that already carries this kind of
  loft/boolean topology can crash OCCT outright (not the graceful
  "command not done" of a normal fillet failure). Apply the ordinary
  perimeter fillet to the *plain* extrusion first, then fuse in the swept
  lip afterward -- never the other way around.
- If the tool used to `Cut` material away from the body spans further (in
  the prismatic axis) than the tool used to `Common` the replacement back
  in, the two results end up with a genuinely overlapping 3D volume, not
  just a shared boundary, once fused. Fusing two solids that fully overlap
  (as opposed to merely touching) is a second flavor of the degenerate
  coincident-boolean problem from lesson 6, and can inflate an edge's
  tolerance by 100x+ relative to its length in a way `isValid()` misses
  entirely -- only `shape.check(True)` (the extended BOP check) catches it.
  Clip both tools to the exact same span before the boolean pair, so the two
  results partition the body with no overlap.
- A vertical cut plane through the model can also graze an *unrelated*
  existing curved surface (e.g. a perimeter fillet from a completely
  different feature, far from the region you're editing) at a near-tangent
  angle, which is its own source of an inflated-tolerance edge invisible to
  `isValid()`. Keep any such cut plane's extent restricted to the region it
  is actually meant to affect, not the full model bounds, even when it would
  be simpler to write a full-height box.

## 10. Process and cost

- One writer per worktree. Do not run the controller and a subagent on the same
  files at once — `git checkout`/commit from either will clobber the other.
- Give a worker a tight brief and the exact commands; the brief matters more than
  the model tier. Reserve any big-model budget for one bounded, specific question.
- Prefer tests over prose review, and prefer a numeric/visual repro over theory.
- Committed one-off per-board authoring scripts and per-board duplicate
  native-check scripts are maintenance overhead. The six
  `Tools/HangboardCAD/migration/author_*.py` scripts were retired for that reason (and because
  re-running one would now recreate a document without its embedded board
  manifest); their provenance lives in
  `docs/source-audits/2026-09-24-<slug>-cad-provenance.md`, each naming the
  commit the script can be recovered from. A new board's authoring script is a
  throwaway under `.context/`; the committed FCStd, its embedded manifest, and
  a dated provenance record are what survive.
  The framework is justified only by the repo's hard contracts (hash-pinned
  bytes, exact package schema, cross-platform reproducibility, ODR).

## 11. Sculpted lift-blocks and partitioned troughs
(`lattice-mxedge-lift-small`; applies to sibling MXEdge / similar scooped shells)

### Measure topology before inventing pockets

`board.json` contacts are a **logical partition**, not a pocket count. MXEdge
Small has four grips but the front mesh is **two stadium troughs**. The upper
trough is **one** stadium opening with **one** crowned floor — no artificial
8/14 stepped shelf: edge-8 is the upper-wall lip only; edge-14 takes the rest of
that trough including the single floor. edge-18/mono share the lower trough
(mono nests in the right end). Authoring four separate openings, or inventing a
dual-floor step in the upper trough, looked "reasonable" and was wrong for a
long stretch of the session. This model widens stadium openings to rim radius
**18 mm** (reference rim was 14 mm) and uses a **~9.9 mm** front wall roll — the
largest ≤10 mm that still leaves a straight face inside the inset budget.

**First measurement pass, before any cutter:**

1. Dump reference node AABBs from the Git-resolved USDZ.
2. Build a front depth map (0.5 mm grid is enough) and count recessed runs per
   column — that tells you trough count vs pocket count.
3. Only then decide cutters and region face selection.

Scratch diagnostics under `.context/<slug>/scratch/` (depth map, layout, floor
profile, AABB dump, candidate-vs-ref depth diff) beat eyeballing alone. Keep
them; they are not build inputs.

### Product copy is not millimetre truth

Catalogue strings like "20 × 11 × 5 cm" are rounded. Compile against
**descriptor / mesh bounds** (for Small: ±84 / ±17 / ±49 mm). MX edge labels
can be **area-equivalent** with depth varying along length — measure the crown
rather than assuming a constant floor.

### Walls matter more than floors for lambert

Flush pocket floors read as a blank brick under `preview.py`'s lambert light.
Recesses read from **wall normals** (ogee / bevel / lip). If the front looks
flat or "cattywompus," fix entry / wall geometry before chasing texture or
triangle count.

### Compile partition traps (hard)

- Contacts must be **faces of the boolean-cut body**, not separate shells
  `Common`'d onto the body (degenerate coincident boolean → fragments / holes).
- Curved contact faces (cylinders, cones) are supported since Deluxe II: the
  compiler assigns curved body faces to regions per face (lesson §15). Before
  that, a true `Cylinder` contact failed the centroid `distToShape < 1e-4` check
  and needed an n-gon prism.
- **No non-planar quads** for crowned floors. A lofted/ruled quad between
  stations along a parabola is non-planar and breaks `compile_board`'s
  surface-area partition check; author a **triangle soup** (planar by
  construction) instead.
- Floor / wall splits: decide ownership by a face's **whole extent**, not its
  centroid. One boolean face can span a full apex strip; a centroid test assigns
  it arbitrarily when it straddles a region boundary.
- **Published grip depths may not match reference node depths.** The reference
  Small nodes span whole troughs; the published-depth gate wants 8/14/18/25 mm.
  Satisfy the gate with a **lip-only** band for the shallow upper partition and a
  **single crowned floor** at the published centre depth for the deeper one — do
  not invent a second floor or stepped shelf, and do not blindly copy reference
  AABB depth extents.

### Construction habits that paid off on Small

- Bake the outer body to a `Part::Feature` before further cuts when a prior
  fillet / loft would otherwise be wiped by `Part::Cut` dependency quirks.
- Prefer even arc segment counts so a vertex lands on trough centreline.
- Subdivide long straight wall runs when a single face would make a contact AABB
  overrun (one face spanning x ±48 put edge-18 out to 48 instead of ~39).
- Sample wall stations from one stadium template of (core x, outward normal)
  pairs so corresponding samples stay aligned under depth scaling.

### Acceptance and process reminders specific to this class

- Declare sculpted → measured approximation **before** iterating; do not use
  `compare_exports` as a per-tweak gate.
- Resolve the reference only via `reference.load_reference` into
  `.context/<worktree-slug>/ref/` — never read live `assets/primary.usdz`.
- Do not attach an `EXIT` trap that deletes `.context/` to one-shot shell
  blocks; that wipes the venv mid-loop. Clean up exact owned resources at
  session end instead.
- Prefer the retired sibling author scripts for Small and Large, and their
  authoring notes, as the structural precedent for partitioned troughs — not
  the constant-section `lattice-triple-rung` pad clone. The notes are preserved
  in `docs/source-audits/2026-09-24-lattice-mxedge-lift-small-cad-provenance.md`
  and `…-lattice-mxedge-lift-large-cad-provenance.md`, which also give the
  commit to `git show` the code from. Large-specific measurement traps are in
  §11.

## 12. What Large added
(`lattice-mxedge-lift-large`; same sculpted brick as Small)

Large’s committed descriptor claimed a ±49 mm front. The mesh is the Small
brick: 168 × 34 × 98 mm. Catalogue “20 × 11 × 5 cm” is the shared rounded
string. Measure the mesh before trusting either.

The depth map must ignore the front skin and the perimeter roll. Minimum Y in
a cell is the lip, so pockets vanish; take the deepest front-half sample.
`|z| ≈ 49` is the roll and looks like a ~29 mm recess — ignore `|z| > 44` when
counting troughs. Large was still two stadiums: edge-16 / edge-12 on the upper,
edge-22 / mono-28 on the lower.

Published and measured floors diverge per trough. Upper matched 16 mm. Lower
measured 20 mm and was authored at the published 22 mm so the region-depth
gate passes. Crown was `c ≈ 0.134` on Small’s stadium (arc centres `x = ±48`,
radius 14 mm). A shallow lip station must stay shallower than the crowned end;
12 mm versus 13.9 mm only just fit.

Fit the mono on its own circle. The contact node includes the trough end, so a
radius over the whole node is the stadium wall. Large tapered 13.6 mm to
11.8 mm; Small’s 10.7 / 9.2 bore is the wrong hole. Put the left-hand split at
`center − rim radius` or the edge and the mono claim the same faces.

Cord dots on the top view were mouths, not through-holes: radius 3.4 mm,
3 mm deep. `board.json` already said the interior was omitted. A dark lambert
top hides them; confirm with a point query. Keep them n-gons.

Once an `FCStd` exists, the delivery lock hashes descriptor + source, not the
USDZ or `board.json` (which is generated from the source at build time), so the
package contributes two files. Park the old digest in
`supersededSha256Manifest`. That alignment test now runs in CI's Python job.
Do not claim `native_source_checks` edit propagation for a cut-body source;
that suite is the sketch-and-pad checker.

In the app, tap the hold map. `hangten://board/…/hold/…` stops on the system
“Open in Hang Ten?” dialog. The owned-simulator trap deletes DerivedData, so
a second screenshot pass is a full rebuild.

## 13. Board metadata lives in the FCStd; board.json is generated at build time

- A CAD board's `board.json` is generated from the FCStd's document-level
  `HangTenBoardManifest` property (`hangboard_packages.cad_source`, with
  `Tools/HangboardCAD/board_manifest.py` as its command line) whenever the
  package is validated or staged into the iOS or Android app. It is never
  committed: an earlier design committed it and checked it for freshness in
  CI, which left a hand-editable second copy of the metadata. The validator now
  rejects an on-disk `board.json` in a CAD package. Edit the manifest with
  `set_board_manifest.py`.
- The FCStd is Git LFS. Every job that validates, stages, or builds the apps
  must check out LFS objects; a pointer fails generation with a fetch hint.
- **Do not re-save a source through FreeCAD just to change metadata.** A FreeCAD
  1.1.3 save re-serializes every `*.brp`, element map, and placement with
  last-ulp differences (and flipped one enum), even with no geometry edit.
  `set_board_manifest.py` rewrites only `Document.xml` and proves every other
  member byte-identical.
- **Number spelling is part of the package contract.** The package validator
  requires nine-decimal instance translations (`0.000000000`), so a plain
  `json.loads`/`json.dumps` round trip (`0.0`) breaks validation; the generator
  keeps every float's source lexeme, and the validator checks the exact
  generated bytes that staging writes.
- **FreeCAD 1.1.3 on Linux (AppImage) does not reproduce the macOS-built USDZ
  bytes.** The same unchanged sources compiled on Linux differ from the
  committed assets for all five boards. Linux is fine for before/after
  comparisons on one platform (the manifest migration compiled byte-identically
  before and after), but committed assets must be compiled on the pinned macOS
  toolchain, which CI's `cad-reproducibility` job enforces.
- FCStd sources are Git LFS objects. Without `git-lfs` they are 130-byte
  pointers and every CAD tool (and the freshness check) refuses them.

## 14. What Compact II added
(`metolius-wood-grips-compact-ii`; a wide sculpted wood board with 19 contacts)

### Check Git for a retained authoring script before you measure

The pre-migration Compact II asset came from a hand-authored Blender script,
`Tools/HangboardModels/wood_grips_compact_ii.py`, deleted in `d7ca9c5c9` and
still readable at `d7ca9c5c9^`. It holds every number the approved mesh was
built from: the silhouette's cubic spans, the pocket and edge layout, fillet
radii, the depth-dependent top profile, and the 64 mm body depth. It also says
which numbers are estimates. Porting those numbers verbatim reproduced the
reference with no mesh measurement. Node IDs, `modelBounds`, and every
`facePlaneAABB` came out within 0.6 mm. Run
`git log --all -- 'Tools/HangboardModels/*<slug>*'` before you build a depth
map. Label the ported numbers as retained display estimates, not as
manufacturer dimensions. On this board Metolius publishes only the
610 × 157 mm face and the 29 / 19 / 56 mm hold labels.

### A polyhedral body is how you get exact contacts on a sculpted surface

The partition claims a body triangle only when its centroid is within 1e-4 mm
of a contact face. On a curved face, a chord triangle's centroid sits up to
the tessellation deflection away from the surface, so the claim fails
silently. The triangle then stays in the body and z-fights the region mesh.
Compact II avoids this with planar faces only:

- The body is a stack of depth stations. Each station is the silhouette offset
  along its inward normal by the roll inset, with the top lowered by the
  depth-dependent profile. A station pair becomes a planar quad where the four
  corners are coplanar and two triangles where they are not. For the
  triangles, pick the diagonal from the side of the centreline, so the two
  mirrored halves facet the same way.
- Each cutter is a stack of rounded-rectangle stations with the same sampling
  angles at every station. Matching chords stay parallel, so every side quad
  is a planar trapezoid. The capsule's zero-length straight side is removed on
  every station at once, so all stations keep the same vertex count.
- One `Part::Cut` removes a compound of all 14 cutters. A pocket region is
  every face of the cut body that lies on its cutter. A top region is every
  up-facing face above the pocket rows, split at fixed x boundaries. Put a
  silhouette vertex exactly on each boundary so no face spans two holds, and
  fail the build if one does.

`removeSplitter()` merged nothing on this construction (10,316 faces before
and after). The source is 13 MB, mostly the cutter and body BReps. A compile
takes about 3.5 minutes because it recomputes the boolean. That is heavy, but
it reproduces byte for byte.

### `compare_exports` does not scale to a dense reference

The reference has about 60k triangles and the candidate about 17k.
`compare_exports.py` compares every sample with every triangle, so here it ran
for about 25 minutes and peaked near 23 GB RSS. It reported a worst sampled
two-way deviation of 0.39 mm, which passes the 0.5 mm limit because the
geometry was ported, not re-measured. Start it in the background right after
the first good compile, or skip it once the descriptor `facePlaneAABB` and the
renders agree. It is evidence, not a gate.

### A board authored before §13 only needs the manifest embedded

Compact II was authored on a branch that predated §13, with a committed author
script and a hand-authored `board.json`. Bringing it to the current convention
needed no FreeCAD run: `set_board_manifest.py` embedded the existing
`board.json`, `board_manifest.py` regenerated it byte-identically on the first
try, and only `Document.xml` changed in the FCStd, so the USDZ and descriptor
bytes stayed the same. Then delete `board.json`, add it to `.gitignore`, move
the script's provenance into a dated `docs/source-audits/` record, and delete
the script.

## 15. What Deluxe II added: holds as vectors, not triangles
(`metolius-wood-grips-deluxe-ii`)

- **Author with native features, not faceted polyhedra.** The body is a
  `PartDesign::Body`: five pads of one lines-only profile sketch, one
  through-all pocket of the outline sketch, and 21 capsule sketches (two lines,
  two arcs, tangent and radius constraints) pocketed from their tier front
  planes. Each pocket's `Length` *is* the published depth. The document has 373
  B-rep faces and is 1.1 MB; the faceted draft of the same geometry had 11,893
  faces and was 12.7 MB.
- **The compiler now partitions curved faces per face** (README "Surface
  partition"), so cylinder and cone hold faces are exact. The region ships the
  claimed body triangles, so its boundary with the body is shared.
- **Small toroidal fillets explode the mesh.** A 1.2 or 2 mm fillet around a
  12.5 mm capsule arc tessellates to about 3,700 triangles per toroidal face
  with the pinned OCCT, whatever the deflection: about 300k triangles for the
  board. A chamfer of the same size gives exact conical faces and 23k triangles
  in total. Measure triangle counts per surface type before you pick fillets.
- **PartDesign features refine by default.** Set `Refine = False` on every pad
  and pocket, or coplanar faces merge and a top region straddles its x boundary.
  The same applies to `Part::Cut`.
- **Split region boundaries with the feature tree.** Pad the profile once per
  top-region span (x = ±305, ±238, ±81). With refine off, the chamfer faces
  stay split at those x stations, so each top hold owns whole faces.
- **Do not fillet an edge that lies on the board end face.** Each side-open
  floor meets the end face in a straight edge. Adding those six edges to one
  combined fillet made it fail (`BRep_API: command not done`), although every
  pocket filleted on its own. Exclude them; the end stays sharp.
- **Check the reference texture before embedding it.** The Deluxe reference
  carried `dummy_texture.png`, a 1 × 1 black pixel. Embedded as `TextureFile`,
  it rendered the whole board black in the app. Use `BaseColor` alone when the
  texture is a placeholder.

