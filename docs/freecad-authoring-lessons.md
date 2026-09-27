# Lessons from the FreeCAD hold-authoring migration

Hard-won, board-agnostic lessons from migrating hangboards to native FreeCAD
sources (pilot: `lattice-triple-rung`; then `metolius-rock-rings-3d`, later re-authored as vectors (§17); then
sculpted `lattice-mxedge-lift-small`; then the vector-profile
`metolius-prime-rib`). Read with
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
- Curved contact faces (cylinders, cones, B-splines) need
  `HangTenCurvedRegionPartition` on the source (lessons §15 and §16). Without
  it, a true `Cylinder` contact fails the centroid `distToShape < 1e-4` check,
  and the body keeps a duplicate of the hold.
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
(`HangTenCurvedRegionPartition`, §15, now opts a source into claiming such
triangles.) Compact II avoids this with planar faces only:

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

## 15. Vector-primitive profiles
(`metolius-prime-rib`; applies to any constant-section board)

### Fit primitives before you reduce vertices

Order the reference's end-cap loop (every vertex at the prismatic end, here
x = 252.8 mm) and fit its runs before reaching for a polyline. On prime-rib,
straight runs and circles fit exactly: 11 lines and 12 tangent arcs with radii
2 / 2.2 / 2.6 / 3.4 / 3.5 / 4 / 6 / 7.5 mm. No circle fits the top surface
(0.3–1.1 mm residual). A cubic Bezier with its end points fixed, solved by least
squares on the mesh's uniform parameter samples, fits both top spans to 6e-5 mm
with poles on a 0.1 mm grid. That points to parametric design data behind the
mesh. The whole profile became vector geometry with named dimensions. Have the
throwaway authoring script refuse to save if the sketch drifts more than
0.01 mm from any reference vertex (prime-rib's did; see its provenance record).

### Sketcher B-splines as Beziers

- Build a cubic Bezier as `BSplineCurve.buildFromPolesMultsKnots(poles, [4, 4],
  [0, 1], False, 3)` and call `exposeInternalGeometry`. That call already adds
  the pole circles, one `Weight` and three `Equal` constraints. An extra
  `Weight` is redundant.
- On 1.1.3, an endpoint `Tangent` between a circular arc and a B-spline end
  leaves the end handle free to rotate: one DoF per joint, reported through
  `getGeometryWithDependentParameters()`. A B-spline–B-spline `Tangent` does
  bind. Level the handle explicitly (point-to-point `Horizontal` between pole
  centres). Then check G1 numerically, because `FullyConstrained` alone does not
  prove tangency.
- Find each pole circle by its centre coordinates, not by creation order.

### Regions, orientation, partition

- Sketch `Edge<n>` names follow `Shape.Edges`, not the geometry index. See
  migration trap 12.
- An extruded region face's normal follows the stored edge direction. See
  migration trap 13. A flipped hold renders dark in the front view before any
  test notices it.
- Curved hold surfaces need `HangTenCurvedRegionPartition`. Without it, the body
  keeps a duplicate of every curved hold. Check the compiled asset with a
  duplicate-coverage count (body triangles inside a region's profile span in
  the prismatic middle). It should be zero.

### Cost of fidelity

A 1.2 mm end round-over reproduces the reference ends and contact extents
exactly. On OCCT 7.9.3 it also costs ~54k body triangles (2,048 per toroidal
fillet face) against the reference's 8.8k. The asset grows to ~1.1 MB.
`compare_exports` takes tens of minutes on it and needs a small `--chunk`. If that trade is wrong for a
board, a square end changes the ends by at most 0.5 mm (1.2·(√2−1)).

## 16. What Deluxe II added: holds as vectors, not triangles
(`metolius-wood-grips-deluxe-ii`)

- **Author with native features, not faceted polyhedra.** The body is a
  `PartDesign::Body`: five pads of one lines-only profile sketch, one
  through-all pocket of the outline sketch, and 21 capsule sketches (two lines,
  two arcs, tangent and radius constraints) pocketed from their tier front
  planes. Each pocket's `Length` *is* the published depth. The document has 373
  B-rep faces and is 1.1 MB; the faceted draft of the same geometry had 11,893
  faces and was 12.7 MB.
- **Opt in to the curved partition.** The source sets
  `HangTenCurvedRegionPartition` (README "Surface partition"). Without it, every
  cylindrical pocket wall and conical chamfer stays duplicated in the body.
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

## 17. Vector primitives on a "sculpted" board
(`metolius-rock-rings-3d`, re-authored 2026-09-25)

### Look for the generator's sampling before you call a mesh sculpted

The first Rock Rings source treated the reference as a sculpted shell and
accepted a 17.67 mm deviation. In fact nearly every feature was sampled from
primitives:

- Outline: each span has exactly 12 uniform parameter samples between
  round-number knots, and cubic Beziers with integer poles fit them to 5e-6 mm.
  The perimeter round's stations are 22.5 + 6·sin θ.
- Pockets: six depth stations. Each station is an exact stadium, and each is the
  opening inset by the same amounts at the same depth fractions in all three
  pockets.
- Cord tunnels: exact ellipses (fixed 1.4 aspect) and circles at a few
  stations.

Group the vertices by coordinate (`Counter` of rounded y, z, …). Station planes
show up as large counts, and the sample spacing within a span shows the
parameterisation.

### The reference can be wrong about the product

The reference's jug was a stepped scoop cut down from behind. The photographs
and the product owner show a convex hump. An exact fit to the reference is not
evidence about the product, so check each feature against the photographs
before authoring it.

### OCCT traps met here

- **One fillet across both perimeters of a Bezier outline with small kinks
  fails** (`BRep_API: command not done`), at any radius. Two sequential
  `Part::Fillet`s, front then back, succeed.
- **`Part::Mirroring` of a B-spline shell flips it to face inward.** Mirrored
  cylinders and cones kept their orientation; mirrored B-spline loft walls did
  not. Author the other side's sections and bind them with expressions instead.
- **`Part::Common` drops a `Reversed` B-spline face's orientation.** A
  `Part::Reverse` placed *before* the clip had no effect on the walls, but it
  did reverse the planar end cap. Reverse *after* the clip. A loft's intrinsic
  normal is set by its station order, so try reversing the section list first.
- **Every `Part::Cut` in a chain stores a full copy of the body.** With B-spline
  fillets this made the FCStd 15 MB. One `MultiFuse` of all tools and one
  `Cut` brought it to about 5 MB (7.4 MB once the jug region also stores the
  rounded crown).
- Assert region orientation in the authoring script: step 0.3 mm along each
  region face's normal and require the point to be outside the body. Flipped
  regions render dark. The CPU `preview.py` side view shows the flip as the lit
  arc of a tunnel appearing on the wrong side.

### Do not bind fillet faces by name; split the solid instead

The jug had to include the crown's round-overs to be visible from the front. A
`SubShapeBinder` on those fillet faces (on `Part::Fillet`, and again on
`PartDesign::Fillet`) lost its element-map names after a crown edit, even
though the solid's topology and face indices were unchanged. It then fell back
to binding the **whole solid**, which is silently wrong, because the compiler
would have exported the entire body as the hold. Edge bindings to sketch
geometry (prime-rib) survive. Face bindings to fillets do not.

A geometric split has no names to lose. `Part::Common(rounded solid, box)` is
the region, and the same box joins the body's recess `MultiFuse`, so the body
and the region meet on the box planes. The region's seam faces are internal:
they are coincident with the body's seam faces, which the partition hands to the
region, and they are hidden inside the board. Exempt them from orientation
checks. Two cautions:

- Keep the box planes off tangencies. A plane at exactly the height where the
  round meets the crease gave an invalid solid; 1 mm lower was clean.
- Test the region with an edit that moves it (here `CrownP3Z`), not only with
  an edit elsewhere. An unrelated edit passed with the broken binder.

### Cost

B-spline fillet faces tessellate densely at 0.08 mm. The board went from 15.8k
to 87.8k triangles, the asset from 314 KB to 1.95 MB, and the FCStd from
1.3 MB to 7.4 MB.

## 18. What Linebreaker BASE added
(`target10a-linebreaker-base`, from a retained signed-distance generator)

- **Look for generator configs under `.context/` history.** The batch-01
  imports kept `source/geometry-config.json` (outline polygon, relief cuts,
  cavity table) at `2dd5182b4`. The Dewoodstok, Escape Unlimited, and Moon
  Armstrong generators are there too. Their frame was already native (front
  −Y, mm), so no transform was needed.
- **The published-depth gate measures the region's whole Y extent.** Tilted
  floors and mouths that cross a crease both inflate it. A 35° floor pivoted on
  the centre line measured 43 mm against a published 35 mm. Pivot it so the
  deepest point equals the published depth, as for every other cavity. The
  lower-row mouths crossed the tier crease by 1–3 mm, so the crease was raised
  4 mm. Label both as adaptations.
- **Sequential rim fillets, again.** Front then back `Part::Fillet` worked. The
  back failed only where a cut plane met the back face exactly on an outline
  edge (sloper planes through z = 132 at y = 0). Test each edge with
  `makeFillet` to find the offenders, and leave them square.
- **The reference's region selectors may be sloppy.** Its box-selected nodes
  spilled onto neighbouring holds by up to 19 mm, so large `facePlaneAABB`
  deltas were reference defects, not CAD errors. Check them in a highlighted
  render before chasing them.
- **Diagnostic renders need a z-buffer.** A painter's-algorithm render of a
  CAD asset, whose big planar faces are a few long triangles, draws them in the
  wrong order and looks broken.
- **Taps in `axe` are in points.** Divide screenshot pixels by 3 on the iPhone
  17 Pro, or tap a hold-map row by its accessibility frame. A second
  `hangten://…/hold/…` deep link to the board that is already open did not
  change the selection.

## 19. Re-authoring from manufacturer photos
(`trango-rock-prodigy-pivot`, 2026-09-25/26)

The Pivot's approved display mesh was wrong about the product. It was about
20 % undersized, had the wrong topology, and reversed two published depth
gradients. Tracing it faithfully would only have reproduced those errors. The
board was re-authored from first-party evidence instead. The techniques below
got it from "resembles the product" to "matches it feature by feature", and
they carry over to any board that has a straight-on manufacturer photo. They
are reading and review aids only. Every point is still typed in by an
operator, and nothing detects, traces, fits or registers pixels (see
`AGENTS.md`).

### Check the reference against the manufacturer before measuring it

Before extracting anything, put the reference's front render next to the
manufacturer's photos and depth guide. Compare:

- feature count and shape (teeth vs scallops, slab vs ridge);
- relative sizes of features;
- the direction of every published depth gradient ("16mm - 31mm (L - R)").

If they disagree, stop measuring the mesh and author from the manufacturer.
Depth-guide pictures can show a half rotated 180°; reverse the L→R order for
those, and say so in the provenance.

### Take the scale from a known part in the photo's plane

Manufacturers often publish no dimensions, and retail listings contradict each
other. Pick a feature of known size that lies in the part's front plane: a
bolt seat, a counterbore, a hardware hole whose fastener the manual names.
Measure it in pixels and record the inference chain. For the Pivot, the quick
start's 7/32 in hex key points to a 3/8 in flat-head bolt, which gives a 20.6 mm
countersink, which at 78.8 px gives 3.82 px/mm. Check that circles image as
circles (the photo is near-orthographic) and cross-check against every other
anchor you can find. Record the conflicts; don't average them away.

### Read coordinates off 1 mm-gridded, contrast-stretched crops

`Tools/HangboardCAD/photo_grid.py crop` cuts a region of the photo in the
authoring frame (mm), stretches its contrast, upsamples it to about 20 px/mm,
and draws a 1 mm grid with labelled 5 mm lines. At full-photo zoom, low-contrast
edges such as grey resin-on-resin ledges are invisible. In a 40–60 mm tile with
the contrast stretched they read to about 0.5 mm.

- Tile the whole part at 40–60 mm per tile. Read the silhouette first, then
  each feature, then write the points into a table in the authoring script.
- Pass `--mark x,z ...` to circle authored joints on the crop and confirm they
  sit on the edge.
- Where two crops of the same edge disagree by more than about 1 mm, re-crop
  tighter. Eyeball readings across different zooms drift by 2–3 mm.
- Shading in a product photo is ambiguous about which side of an edge is high.
  Decide from an oblique photo, the manufacturer's CAD render, or the product
  owner, not from the straight-on shot alone (see "Ask about the region" below).

### Fit vector primitives to the typed points

Fit lines and cubic Béziers (G1 at smooth joints, one-sided tangents at kinks)
to the hand-typed points, and report the worst deviation (Pivot: 0.80 mm).
Unconstrained Bézier handles at a kink fold back on themselves. Take each
kink's tangent from the local one-sided direction, and keep handle lengths
positive.

### Review with an overlay, not just side-by-side renders

`Tools/HangboardCAD/photo_grid.py overlay` blends the compiled model's front
view over the photo at the same scale and origin. Misplaced features show up
immediately. Side-by-side renders from a hand-matched oblique camera hide
errors, because the camera never quite matches. Use the overlay for X/Z. Use
oblique photos and the manufacturer's CAD render (quick-start page 3 for the
Pivot) for depth-direction questions.

### Ask about the region, and use the owner's photos

The Pivot's lower-right corner was wrong through two passes until the product
owner circled it on a photo. The band there ends in a pointed caret, the field
runs down to the rail, the rim wraps the rail's end as a J lip, and the upper
bar ends free. When feedback is vague, ask which region looks off, and ask for
a photo of the owner's board. Zoom into their photo at the circled region
before re-reading the gridded crop.

### Moulded parts need round-overs

A resin board with sharp CAD edges reads as wrong even when every dimension is
right. Round every convex edge (a dihedral test: n₂·t₁ < 0) at about 1.5 mm.
Test candidates one at a time, then add them in chunks of about 12, keeping
the ones OCCT accepts together (Pivot: 58 of 102). Keep gated bands sharp so
the published-depth check stays exact. The round-overs roughly double the
triangle count.

### OCCT traps met here

- `makeChamfer` (symmetric or asymmetric) fails on an outline chain that ends
  at a near-tangent or concave kink. Build an asymmetric crimp band as a ruled
  loft from its photographed front edge on the rim face to the silhouette at
  the published depth, and cut it.
- A cutting tool whose edge coincides with another cutter's edge (the field
  floor meeting the rail slot) should overlap by about 0.5 mm instead.
