# Authoring cords on CAD hangboards

Each board's flat `Hangboards/<slug>.FCStd` retains its geometry, embedded board
manifest, and optional document-level `App::PropertyString` properties
`HangTenSuspensionAuthoring` and `HangTenRopePhysics`. These are the source inputs.
Run `rtk proxy bash scripts/build-board-assets.sh` to generate the ignored USDZ,
model descriptor, solved `assets/suspension.json`, and any physics descriptor
before package validation.
For app builds use `scripts/build-runtime-assets.sh`. Staging generates bundled
`board.json` from the native manifest and validated generated suspension; CI consumers
download the producer's runtime artifact. See
[generated artifacts](GENERATED_ARTIFACTS.md).

## The standard method

Every newly authored or revised CAD cord setup generates its routes and hanging
height against the native solid through `compile_suspension.py` and the retained
`Tools/HangboardCAD/solve_threaded_rope.py`, preserving the
connection graph established by the retained evidence. For connected internal
mouth pairs, model the hidden passage as a void in the native FreeCAD solid
and store the topology in embedded `HangTenSuspensionAuthoring` as a `twoBranchCord` (or the
single-loop `threadedLoopCord`) with `internalLoop`. Measure the channel length
with `Tools/HangboardCAD/measure_channel_spines.py`, then solve the visible
routes and hanging height against the exported CAD solid.

For independent visible leads, exterior wraps, or mouths whose hidden
connection is unknown, use the source-backed `cadRoutedCord` topology and
authoring `ropeSolver.method: "nativeRoutes"` described in
[Evidenced exterior wraps and incomplete passage evidence](#evidenced-exterior-wraps-and-incomplete-passage-evidence).
The DUAL front-entry leads are one such case: visible front threading does not
establish a hidden connection between its two holes. Do not invent that join
to fit the connected-channel method. For either native method, generate every
canonical pose through the pinned board build, reproduce generated artifacts
with the native solver's `--check`, and retain native-solid clearance, length,
tube and topology checks. Change CAD authoring inputs and rebuild; never apply
solved heights or routes into a source property.

Do not hand-place cord contact points, anchors that stand in for a solve, or
`pairedLeadCord` leads on a CAD board. The runtime's convex-section fallback and hand-authored
`pairedLeadCord` / `singleCord` metadata remain only for older non-CAD
packages. Captain Fingerfood POCKET retains its existing manifest-embedded
`pairedLeadCord` as an intentional legacy exception pending a separate
evidence-backed revision; consolidation preserves that CAD-contained setup
unchanged. It does not authorize hand-authored routes on new or revised CAD
cord setups. Migrate those cords to the native method matching the evidenced
connection graph.

These boards use the connected-channel method:

| Board | Channel | Section plane | Notes |
| --- | --- | --- | --- |
| Lattice Mini Bar | curved `PartDesign::SubtractivePipe`, two mouths on one face per end | `mouth-x` (default) | constant-section bar; four grip poses |
| Crimptonite Helium Mobile | straight `Part::Cylinder` through-bore, front and back mouths per end | `anchor` | mouths sit in the rounded ends; one loop of cord through both holes |
| Clavellium Training Block | owner-confirmed straight rectangular `Part::Box` passages | `mouth-x`, `channelProfile=rectangular` | one central-channel loop; round-cord adaptation of a flat sling; grip-to-channel mapping unknown |
| Metolius Rock Rings | connected `Part::MultiFuse` void with linked ordered spine | none (direct-leg solve) | one continuous loop per displayed ring; exact native-solid clearance |

One sling through one channel uses the same `twoBranchCord` wire type with
one branch, its two mouths in `passages.left`, and an empty `passages.right`.
This one-loop form is valid only with `internalLoop` and a complete generated
route cache for every pose. It must not duplicate the physical sling to satisfy
the older two-loop inventory. Existing exterior and uncached topologies still
require two branches and four mouths.

Rock Rings extend the topology to one branch with two mouths and retain the
whole measured channel centerline in `internalLoop.channelPointsByBranchID`.
The solver settles the board from total cord length and checks both free legs
and the interior path against the native solid in FreeCAD Python. The spine is
rendered as transient cord geometry, hidden by the body except at its openings.
Schema-2 embedded authoring attaches this setup to each independent instance of the same
model. See the [retained threading audit](source-audits/2026-09-30-rock-ring-threading.md)
for the owner-confirmed hidden connection and estimated channel dimensions.

If a board's cord does not fit the solver's assumptions (below), extend the
solver with evidence and tests rather than falling back to hand-authored
routes.

This contract was first learned from the Lattice Mini Bar migration. Read the [suspension and ODR guide](3D_SUSPENSION_AND_ODR.md) for
package delivery and the approved Mini Bar cord passage metadata
for the product-specific evidence. The approved [Lattice end view](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-2.jpg)
and [loaded view](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-1.jpg)
were decisive: the lower curve belongs to the same loop as the two rising
legs. The user confirmed that two mouths at each end connect inside the wood.

## Establish the threading before choosing a solver

Draw a route graph from evidence. Name every visible endpoint, bore mouth,
hidden connection, free leg, and overhead support. Decide which parts are
one continuous piece of cord. Do not infer an internal channel from a dark
spot in a photo; obtain another view or an owner correction. Retain exact
manufacturer images and record which observations are sourced and which
dimensions are display estimates.

For the Mini Bar there are **two separate loops, one at each end**. Each loop
is one continuous cord: overhead support → first exterior leg → first mouth →
hidden connected U channel → second mouth → second exterior leg → overhead
support. The channel is a void in the FreeCAD wood solid. Its centerline is
not drawn as a visible cord. The material-free USDZ contains the board only.

The preceding solid-bar and exterior-wrap interpretations were wrong because
they lacked the observed mouths and the connected passage. A plausible
silhouette is insufficient evidence for a cord route. Compare a loaded
manufacturer side/end photo with the same CAD pose and approximate camera;
inspect the mouths, both legs, lower bearing, and occlusion, then rotate the
model through every supported grip. The Mini Bar matched-photo review is
described in its source audit.

## Settled physics for a bar-shaped board

`HangTenSuspensionAuthoring` stores two point mouths per loop, their body node, branch
pairing, one overhead anchor, estimated radius and rest length, canonical
board pose rotations/cameras and optional `offsetXZ: [x, z]`, a positive
clearance, `internalLoop.windingByPassageID`, and
`internalLoop.channelLengthByBranchID` measured from the CAD pipe spines.
The passage IDs and pair order are part of the topology. Authoring contains no
model/source hashes, settled heights, or generated visible route points. The
compiler binds generated `assets/suspension.json` to the current CAD source,
authoring payload, and each model descriptor's `modelSHA256`; package validation
checks those bindings. `board.json` is generated from the FCStd manifest plus
this validated artifact.

`Tools/HangboardCAD/export_rope_collision_solid.py` tessellates the final,
watertight FreeCAD wood solid as a build intermediate. The reusable
`solve_threaded_rope.py` intersects that solid at each mouth, offsets the
section by the cord radius plus declared clearance, and finds the shortest
collision-free exterior path in the passage's winding direction. It includes
the CAD-measured hidden channel length, then lowers the board beneath the
fixed support until the longer of its two loops uses the declared length.
The other loop may have at most 0.5 mm slack. Every visible segment is sampled
at 0.5 mm against the native 3D solid before the producer publishes the artifact.

The resulting translations and centerline contacts are a **generated cache**
under each `canonicalPoses` entry in ignored `assets/suspension.json`. Authors
specify mouths, threading, channel length, loop length, overhead support,
rotation/camera, and optional horizontal offsets in CAD, then rebuild; they do
not draw pose contacts or copy the generated Y translation into CAD.
`--check` regenerates the cache and
rejects stale values. The app renders this cache as transient, unpickable
RealityKit geometry. Cord remains absent from the CAD body and material-free
USDZ. The prior convex-section runtime solver remains a fallback for older
packages without a generated cache.

This solves the **settled, taut, negligible-mass rope** shape in the plane of
each mouth for a bar-shaped board with a representative end section. It models
contact and fixed length without animated swing. It does not model friction,
elastic stretch, or unrestricted 3D sliding along a nonuniform board. For a
board that violates the section assumption, use a full 3D constrained solver
and retain the same native-solid clearance and loop-length acceptance gates.
The estimated 0.82 m Mini Bar loop is not a manufacturer measurement, so the
predicted board height is a display estimate to compare with loaded photos.

An earlier offline Bullet experiment tried
to settle an earlier solid-bar surrogate and failed exact-mesh acceptance in
all eight cases. That experiment did not contain the now-confirmed channel,
so it cannot establish whether a correctly constrained physical simulation
would work. See [the archived experiment and its measured limits](source-audits/retired-bullet-rope-prototype.md).

Live simulation remains possible engineering work. RealityKit provides
[rigid-body physics](https://developer.apple.com/documentation/realitykit/physics-simulations-and-motion),
[joints](https://developer.apple.com/documentation/realitykit/physics-joints-and-pins),
and [cloth simulation](https://developer.apple.com/documentation/realitykit/physics-cloth-simulation),
but these APIs do not infer a threaded, continuous rope through hidden
channels from mouth and anchor positions. A rope implementation would still
need the route graph, attachment and bore constraints, a collision shape
faithful at the mouths and grip recesses, a stable tension/length model, and
repeatable settling across all poses. Test exact CAD-solid clearance and
motion before replacing the convex-section renderer; the old surrogate's
failure is evidence about that experiment, not a proof against simulation.

### Follow-up whole-loop physics probe (2026-09-27)

The corrected Mini Bar CAD solid was tessellated directly from the final
FreeCAD `RightCordChannel` feature: 17,022 vertices and 34,048 triangles. The
result is watertight, unlike the importer-visible USDZ surface, and can supply
an inside/outside collision test. A temporary position-based chain prototype
seeded one continuous loop through each CAD channel, with both ends at the
fixed overhead point and 2 mm cord radius. It remains under the workspace's
ignored `.context/frantic-kiwi/` directory; it is **not** product code.

Two failures were reproducible. First, holding the board center at one height
for every grip while declaring a fixed 0.82 m loop leaves roughly 0.29 m of
unaccounted length in three of the four poses. A hanging board must be allowed
to move vertically beneath the fixed support as its grip pose changes. The
estimated downward displacement for a taut seed is about 154 mm for either
edge, 48 mm for the jug, and 156 mm for the pinch. These values depend on the
estimated loop length and are only initial conditions, not authored poses.
Second, unsigned closest-face distance missed particles already inside the
wood. Signed distance from the closed FreeCAD solid detected those crossings.
After adding signed collision and constraining the hidden particles to the
channel, an edge-20 trial had zero sampled points inside the wood but still
measured 0.829 m of chain for a declared 0.820 m loop, with a link stretched
28% at the bore rim. Finer 2 mm spacing did not resolve the constraint conflict;
the trial measured 0.856 m and a 72% maximum local stretch. The prototype is
therefore rejected for app integration. Point clearance alone is insufficient:
acceptance also needs segment clearance, length and local strain, topology,
convergence, and all eight pose/loop combinations against the exact CAD solid.

A later Bullet soft-body chain trial used the same watertight CAD collider and
the **measured** FreeCAD channel spine as its hidden seed. The spine exporter
reproduced both mouth centers and the 87.214214 mm channel length. At 1 mm
chain spacing, 1,000 position iterations, and an experimental 0.84 m loop,
the edge-20 left loop still settled at 0.84166 m; the most stretched link was
about 10% longer than rest. Sampled nodes stayed outside the wood, but
segment midpoints came within 1.974 mm of it for a 2 mm rope. This is also a
rejected probe: increasing iteration count and using the real hidden spine
did not establish inextensible, nonpenetrating contact. The nominal 0.82 m
length is a display estimate, not a manufacturer measurement. A solver cannot
use that estimate as proof of a physically feasible rope configuration.

The prior convex-section approximation passed a fixed-length test for all
four grips, but native-solid inspection found up to 3.41 mm centerline
distance near a mouth: 1.41 mm of visible space beyond the 2 mm rope radius.
The new CAD-section solve removes that hull buffer where the rope bears on
wood. Across four grips and four visible leads it measured at least 2.097 mm
centerline distance from the solid, with 2 mm estimated rope radius and
0.1 mm authored clearance. Direct legs may have more clearance because they
do not bear on the wood. The four pose solutions use no more than 0.378 mm
slack in either loop; their 0.82 m rest length remains an estimate.

For a future unrestricted 3D simulator, include both the board's free vertical
degree of freedom and a continuous, inextensible loop constrained inside the
real channel. The board's [manufacturer-published 150 g mass](https://latticetraining.com/product/mini-bar-portable-hangboard/)
can set the gravitational load. The current section solver meets the settled
shape requirement for this approximately extruded bar; it is not a dynamic
soft-body simulation.

Mouth and anchor coordinates **do not uniquely determine a route**. Between
one mouth and an external support, cord can travel around either side of the
section. The winding choice records how the physical cord was threaded. It
is a discrete topology input, not a manually placed contact point. The
solver can calculate bearing only after that ambiguity is resolved.

## Solver assumptions and section planes

The current solver applies when all of these hold:

1. Source evidence supports two connected mouths per loop and a continuous
   cord returning to the same support.
2. The CAD source contains the connected void, and mouth coordinates refer
   to that void in the descriptor/importer coordinate basis.
3. Each mouth's section plane (below) is representative of the bearing
   surface along that leg. The native solid is watertight for collision checks.
4. The internal-loop model has one or two branches, two distinct point mouths
   per branch, and one winding
   choice for each mouth. Each branch's `passageIDs` lists its paired mouths
   in traversal order.

The `threadedLoopCord` extension instead requires one branch with two distinct
mouths, its complete ordered native channel spine, and unobstructed rising
legs. It does not use a section plane or surface winding; exact native-solid
checks enforce cord radius plus the configured internal-loop clearance.

**Channels.** A channel is either a curved `PartDesign::SubtractivePipe`
(its Sketcher spine is measured) or a straight `Part::Cylinder` through-bore
(its axis is measured). A straight rectangular sling passage can be an editable
`Part::Box` with an operator-selected `HangTenChannelAxis` of `x`, `y`, or `z`;
the tool measures the transformed centerline between the actual mouths, not
the cutter's overhang. A through-bore's two mouths lie in the same section,
which the bore cuts in two; the solver bridges that gap to recover the
exterior outline and reopens only the notch at the mouth it is solving.
For a wide rectangular passage, explicitly select
`ropeSolver.channelProfile=rectangular` with `mouth-x`: the solver joins matching
parallel depth rims across the slot instead of circular morphological closing.
Tapered, overlapping, or multiple section pieces are rejected for that method.

**Section planes.** The embedded authoring property's optional
`ropeSolver.sectionPlane` chooses each mouth's plane. It is never merged into
`board.json`, and `--check` reads it so the cache stays reproducible.

- `mouth-x` (the default) cuts at the mouth's x. It suits mouths on a
  constant-section bar, like the Mini Bar.
- `anchor` cuts the plane through the mouth that contains the model depth
  axis and the overhead anchor, which is the plane a taut leg actually hangs
  in. The plane follows the solved board height until it converges. Use it
  when the section changes along x near a mouth: the Helium Mobile's mouths
  sit in its rounded ends, and a `mouth-x` solve there let the leg clip the
  taller face it crosses on its way to the central hook.

For a tapered, twisted, or locally different section that neither plane
represents, one planar path may miss a shorter 3D route even when its sampled
points clear the solid; extend the solver toward a full 3D route. For an
external wrap without connected internal mouths, a different connection
graph, or a moving anchor, extend the schema and solver with evidence and
tests. No solver choice can recover hidden threading from the mesh alone.

## Authoring sequence for connected internal mouths

1. Inspect the exact product revision from several manufacturer views and
   record the route graph and unknowns in a source audit. Confirm whether
   each cord is one piece, where it enters and exits, and whether any segment
   is hidden in the board. Request owner input for genuinely occluded facts.
2. Author the body and connected channel in the native FCStd. Confirm the
   shape recomputes, the mouths open at the declared coordinates, and the
   exported USDZ has neither cord nor material bindings. Record estimated
   diameters and offsets as estimates.
3. Put suspension inputs in the FCStd's `HangTenSuspensionAuthoring` with
   `Tools/HangboardCAD/set_cad_authoring.py`. Bind
   all mouths to the body node, pair each loop, supply the overhead anchor,
   and choose each winding from the evidence. Measure the paired-mouth length
   from each channel's spine (pipe spine or bore axis) with
   `Tools/HangboardCAD/measure_channel_spines.py`; record it in
   `internalLoop.channelLengthByBranchID` and rerun the tool with
   `HANGTEN_CHANNEL_VERIFY=1` to catch authoring drift. For every canonical grip,
   compare the CAD contact-region normal with the
   intended loaded face. A selected edge must not point down while the hand
   is meant to hang from its upper rail. The pose camera's stored
   `viewDirection` points from camera to board, so it must oppose the
   outward contact normal to show that region. A nearly end-on camera can hide the rail
   and make a cord opening look like the selected hold. A bar that flips
   between grips needs its pose rotation changed before the cord is solved.
   Choose `ropeSolver.sectionPlane` (see above). The anchor's
   `offsetFromBoardBounds` is only the solver's starting point: set it low
   enough that the loop is longer than the route at the base pose (the solver
   then lowers the board until the loop is taut), so the settled hang depends
   on the loop length, not on that offset. Store canonical rotation, camera,
   and any horizontal displacement as `offsetXZ: [x, z]`; omit the offset when
   it is zero. Run `rtk proxy bash scripts/build-board-assets.sh --package <slug>` to export
   the final native solid and solve every pose, then reproduce the generated
   artifact with `solve_threaded_rope.py --package <slug> --solid <owned-collision-solid.json> --check`
   using the [pinned environment and collider export](../Tools/HangboardCAD/README.md#focused-cord-reproduction).
   When a winding is in doubt, compare each mouth's route length and turn for
   both directions; the physical one is normally the short route over the
   nearest edge.
   Generated pose routes are a cache in `assets/suspension.json`, not operator-drawn
   contacts. Generate `board.json` through the normal CAD package process;
   never commit that generated file.
4. Validate the schema, model SHA, package inventory, and
   byte-for-byte CAD rebuild. Add a focused parser and native solver test for
   every pose and a negative test for malformed topology.
5. Measure cord-centerline clearance against the **actual FreeCAD solid**,
   including the segment entering each mouth. A hull-only check cannot prove
   it avoids the wood. Inspect front, side, top, and loaded-photo-matched app
   screenshots for every grip. Check that the cord remains invisible to
   picking and accessibility, that selection and orbit still work, and that
   clearing/reselecting a pose removes/recreates the transient cord.

The original Mini Bar routes used a 2 mm estimated radius. The owner has since
confirmed a 7 mm cord diameter for both the Mini Bar and Clavellium. The current
Mini Bar's generated routes have at least 3.586 mm sampled centerline-to-wood
clearance with a 3.5 mm radius. Its 7.4 mm CAD bores remain display estimates;
see [the cord and bore audit](source-audits/2026-09-29-cord-and-bore-scale.md).

For live physics, the FCStd's `HangTenRopePhysics` retains authored simulation
inputs; `export_rope_physics.py` supports native circular
`PartDesign::SubtractivePipe` channels as well as straight Box and native
`Part::Cylinder` adapters. A Cylinder supplies the bore axis from its authored
placement. Its complete circular cap boundary comes from the CAD wire, rather
than its single seam vertex. Native side seam vertices are retained while the
convex planar caps receive deterministic triangulation; OCCT's varying internal
cap diagonals otherwise change the exported descriptor between identical runs.
The pipe adapter intersects the native subtractive tool with the pre-cut wood
to retain the actual channel void. Curved wood mouths have no planar cap:
complete circular sections just inside the exits track sliding material
crossings, while the full wood collision mesh determines physical rim contact.
These sections do not replace the curved mouth geometry. The source spine
between those sections supplies the initial channel traversal. Export support
alone does not enable live physics for a package; it still needs an accepted
initial state, numerical transition checks and visual review.

## Evidenced exterior wraps and incomplete passage evidence

The [remaining-board source audits](source-audits/2026-09-29-remaining-cad/)
include a single eye (Cyclops), an open curl (Plateau), end wraps (Baguette),
four independent bores with exposed rear returns (Flash Board and Baguette
Evo), and visible mouths whose interior connection is unknown (Captain,
Frictitious, Nature, Travelboard). Do not turn these into hidden U channels or
two independent loops. The connected-channel method above remains the method
for boards whose evidence supports that topology.

For these other graphs, `cadRoutedCord` declares one to eight visible strands.
A `lead` runs from the fixed support to one evidenced mouth, a `loop` runs
from that support through two exterior bearing stations and back, and a
`segment` joins two evidenced stations. Unknown joins remain unspecified.
Each strand records its length, radius, material and provenance; estimated
visible lengths are display estimates, not claims about the unseen full cord.

The authoring-only `ropeSolver` has `method: "nativeRoutes"`, a positive
`clearance`, and `terminalsByStrandID`. Each entry supplies one terminal for a
lead or two bearing stations for a loop/segment, plus a `planeNormal` selected
from the native geometry. These are attachment facts, not drawn routes. The
solver extracts native-solid sections, retains their holes and separate
pieces, solves paths around rope-offset boundaries, and settles hanging height.
`sectionPlane: "anchor"` makes each free lead's section contain its actual
support and terminal; it iterates with height for tapered or varying sections.
An optional `pathSearch: "aStar"` searches the same native visibility graph
using the actual three-dimensional distance to the finish as its lower bound.
It changes search order, not obstacles, stations, edge costs or clearance gates.
The endpoint bound uses the actual support even when its projection lies off
the section plane. Omitting this setting preserves the original Dijkstra
search. The setting accepts only this value and is removed from the generated
runtime manifest. A* also reuses a certified result for exactly identical
rotation and horizontal-translation inputs within one solve; it still solves
height from the cord lengths. It does not infer symmetry or equivalent poses.
The [Port-A-Board cord review](source-audits/2026-09-29-remaining-cad/frictitious-port-a-board/cord-physics-review/review.md)
records the actual-support correction and native path comparison. Use anchor
sections when the support-to-mouth span needs a lateral component: projecting
the support into a fixed-X section can introduce a sideways bend that a smooth
rim cannot support.
An optional `planeAxis` selects the native axis that the preferred section
contains. Certified conflict recovery may rotate the free-span section around
its support-to-derived-collar chord as described below; it does not rotate the
actual bore's `mouthAxis`.
For a lead whose bore direction is established by the native solid and retained
manufacturer evidence, `mouthAxis` keeps the terminal at the real opening and
derives a short outward exit beyond the solid's support plane. The solver
certifies the axis segment and includes it in the available-length calculation;
the operator never draws that collar or the resulting centerline.
If the rounded-cache certificate finds a collision on a collar lead, the solver
may retry up to five times, increasing only that lead's section margin by a
quarter of its unchanged cord radius per attempt. Return segments retain their
original margin. The selected margin, derived exit and attempt appear in the
report's `mouthCollars`; they are derived diagnostics rather than authored route
stations. Every attempt retains the same full-solid and tube-intersection gates.

Multiple collared leads must also clear each other. A shortest path through an
empty CAD bore can be invalid once another lead occupies that bore. After an
actual tube conflict, the solver can reserve the other generated collar tubes
as section obstacles. Parallel capsule sections use their actual distance from
the plane and a conservative polygon; unsupported oblique reservations fail
explicitly. Already-valid preferred routes are preserved exactly.

In a rotated grip, independent preferred planes may bring both leads onto the
same lip. If strict checks still reject those routes, the solver searches a
bounded, deterministic set of section rotations around each support-to-derived
collar chord. Each candidate recomputes the native section, settles height and
passes the complete rounded-route solid and tube checks. The mouths and axial
entry directions stay fixed. Candidate angles and failures appear in
`sectionOrientationRecovery`; they are generated diagnostics, not hand-authored
stations. Exhausted searches fail without updating the package. This is a
bounded route approximation, not a global minimum or dynamic rope simulation.
The DUAL front-entry review retains the motivating occupied-bore and lip-contact
regressions.

For evidenced front-entry leads in anchor sections, the optional authoring
setting `tightening: "coupled3D"` releases the seed's exterior collar as a
mandatory bend. It generates that seed from the native solid and attachment
facts, then shortens the visible paths together in three dimensions. The actual
mouth and fixed support remain fixed during each pass; the final segment must
approach from the positive `mouthAxis` half-space and clear the complete native
solid. Every accepted move shortens the path and passes the unchanged solid and
self/interstrand tube checks. The solver re-settles hanging height, repeats
within bounded iteration limits, and certifies the exact rounded runtime cache.
It fails on nonconvergence. This is deterministic local shortening, not a proof
of global minimum or physical equilibrium; no authored route cache seeds the
solve. The setting is authoring-only, accepts only this value and topology, and
its omission preserves the existing section solver exactly.

For an evidenced open adjustment groove that guides a lead into a separate
visible bore, the optional `ropeSolver.grooveGuides` contract selects existing
native cylinder features, never route points. It is restricted to independent
leads in anchor sections and cannot be combined with `tightening`. Its
source binding is generated by the compiler and must match the actual
collider/CAD source; do not author a `sourceSHA256`. `byPoseID` must name
every canonical pose and every strand; each selection contains only `feature`
(the groove), `boreFeature`, and `exitSign` (`-1` or `1` along the native groove
axis). Different native groove choices, pose pitches and anchor offsets require
an explicit evidence/estimate disposition; they are not manufacturer facts.

Export that offline collider with `HANGTEN_ROPE_GROOVE_FEATURES` and
`HANGTEN_ROPE_BORE_FEATURES` set to comma-separated existing cylinder names.
The exporter records finite final-solid wall faces, exact geometry-only axial
bounds and the actual local bore aperture plane. A cutting cylinder's overshoot
is not an exterior mouth. The plane must meet that bore's finite outer wall
boundary, and its finite face must be adjacent to the aperture circle. Opposite
coaxial bores remain separate. With neither variable set, the exporter keeps
its original output exactly. Unsupported cylinder orientations fail explicitly.

When a selected longitudinal guide merges with a transverse notch and bore,
the circular rim may end inward from the exterior side plane. The extractor
then requires intersecting perpendicular native tools, shared final bore/guide
wall edges, a connected native void, an outward exterior face adjacent to the
guide, and zero-material aperture-disk and finite axis-crossing witnesses.
The recorded exterior mouth remains that actual side plane; the separately
recorded cylindrical-wall extent is not substituted for it. Missing or opposite
guides and remote parallel planes cannot certify this merged opening.

When the selected guide and bore axes, terminal and fixed support are
analytically coplanar, the bounded search retains that native axis-aligned
plane for its first search phase to avoid numerical drift in an unnecessary
degree of freedom. The plane is then always released and the native-derived
seed is checked and settled in full 3D. A bounded unit-tension chain Jacobian
step can correct small residuals from the independently reconstructed actual
facet forces:
endpoints stay fixed, at most five corrections of at most 10 micrometres are
allowed, and every trial recomputes full 3D clearance and material support.
These are numerical search bounds, not relaxed acceptance tolerances. Parallel,
inconsistent and noncoplanar cases retain the full 3D search from the start.
This search constraint is not a physical certificate: the final full 3D
solid/tube, seating, entry and actual-facet force gates still apply unchanged.

The guide solver generates section seeds through the selected native groove,
then releases those seed stations during bounded three-dimensional shortening
and hanging-height settling. It never reads an existing route cache as a seed.
The final nine-decimal cache must pass the unchanged full-radius continuous
solid and tube checks, finite groove traversal, finite bore/end-cap entry,
settled length and an active-material reaction check. An endpoint touch or a
clear route outside the groove is insufficient. If evidence authorizes entry
into an existing visible bore, a terminal may be inset only within its audited
finite clearance interval; no connection beyond its native display cutoff is
implied.

Different presentation rotations can resolve to exactly the same native
support origin and height direction. The solver may reuse that calculation
within one fresh invocation when the guide selections also match, but it
independently recertifies every output pose. It never uses a saved route cache
for this calculation. Reports distinguish presentation rotations from the
distinct native physics frames.

The reaction check is discrete frictionless feasibility at the numerical cord
offset, not an exact continuous rope model, global minimum, friction model or
safety claim. Its force scale is unit tension. Contacts contribute only to their
own segment endpoints with barycentric weights. The contact envelope is the
actual radius plus the existing 20 micrometre proposal margin and 10 micrometre
numerical allowance. A separate 10 micrometre closest-feature tie allowance
accounts for opposing triangulated junction features. Every direction needs a
nonempty cone of actual incident outward facet normals; nearby triangle radial
vectors alone are not material normals. The solver independently recomputes
both cone and nodal residuals and rejects unsupported forces. It additionally
recomposes the fitted forces from actual incident-facet cone coefficients,
checks that nodal residual at the same limit, and records the force-weighted
cone-error bound. Both the reconstructed nodal residual and the weighted bound
must be at most 1e-5; cancelling direction errors cannot hide amplified force
errors. Reports retain facet IDs, closest-distance gaps, cone coefficients and active contact forces
so those claims can be checked against the exact retained collision mesh.
All guide metadata remains authoring-only and is removed from generated
`board.json`; runtime still reads ordinary `cadRoutedCord`/`wrappedRoutes`.

Without groove guidance, the default `tightening: "fixed"` uses the selected
section plane. Every route mode certifies visible segments against the full
closed CAD solid using adaptive signed-distance
Lipschitz bounds, with a 10 micrometre numerical tolerance and bounded work.
Uncertifiable intervals fail. The same check covers the rounded runtime cache,
its actual terminal and reconstructed fixed support. Self-crossings, retracing
and nonlocal tube intersections also fail; intentional endpoint joins remain
valid. A radius that fills a mouth cannot also provide clearance: use an audited
cord display estimate when warranted, and preserve the evidenced native solid.

Embed reviewed authoring changes in the CAD document, run
`rtk proxy bash scripts/build-board-assets.sh --package <slug>`, then set up the
[persistent pinned environment and native collider export](../Tools/HangboardCAD/README.md#focused-cord-reproduction).
With that setup's `rope_python` and `rope_root`, reproduce the selected board's
generated artifact with:

```sh
rtk proxy "$rope_python" Tools/HangboardCAD/solve_threaded_rope.py \
  --package <slug> --solid "$rope_root/<slug>-solid.json" --check \
  --report "$rope_root/<slug>-check.json"
```

The generated cache contains only body-space `wrappedRoutes`. For this cached
`cadRoutedCord` path, apps transform those points and add the fixed world
support; they render transient non-pickable tubes without inferring missing
topology or solving live physics. Separately authored live-physics packages
use the physics-descriptor contract described above. The offline report
retains native clearance and length ratios for every pose.

For several model assets or reusable equipment instances, authoring schema 2
contains an `entries` array. Each entry names `presentationID`, optionally
`equipmentObjectID`, `suspension`, and optional
authoring `ropeSolver`. Each target occurs once. Generation validates every
descriptor hash in the generated artifact, preserves manifest number spelling, and stages only the
merged `board.json`. Pass `--presentation` and/or `--equipment-object` to the
solver to select the exact entry. Model hashes are generated from every
referenced descriptor, never retained in authored JSON.

Schema 2 also retains the single-presentation `instanceSuspensions` form used by
threaded-loop reusable pairs: `presentationID` and the exact
map of both equipment IDs to suspension setups, with optional shared
`ropeSolver` settings. The `entries` and `instanceSuspensions` forms are
mutually exclusive. Each form validates generated model hashes and native instance
identity; authoring solver settings are never staged into the runtime board.
The offline solver handles both forms. `--equipment-object` may select one
instance from a shared map; omitting it solves both. `--presentation` selects
an entry in the multi-presentation form.


## Pose-specific exterior loop bearings

`nativeRoutes` may include authoring-only `terminalsByPoseID`, mapping an
existing canonical pose ID to a complete `terminalsByStrandID`-shaped map.
Every override retains the declared strand IDs, station counts and axis rules.
Poses without an override use the global terminal map. Unknown poses, malformed
stations and a combination with `grooveGuides` are rejected. The optional
field is stripped with the other solver authoring settings before staging.

Penta Evo uses this for its source-supported rotation: the selected grip moves
to the lower band, so its exterior loop must bear against the newly upper
band. Stations are deliberately derived from the actual native bearing surface
plus the estimated cord radius and clearance. They are not hand-authored route
vertices or evidence of hidden passages. The existing native solver generates
and certifies each complete route and hanging height. Each pose is solved with
its effective station map before pose or section caching, even when rotations
match. These constrained display routes do not claim dynamic equilibrium.
