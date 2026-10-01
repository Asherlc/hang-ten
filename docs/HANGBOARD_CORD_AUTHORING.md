# Authoring cords on CAD hangboards

## The standard method

Every corded CAD board uses this method: the cord's hidden passage is a void
in the native FreeCAD solid, the topology lives in `suspension.json` as a
`twoBranchCord` (or the single-loop `threadedLoopCord`) with `internalLoop`, the channel length is measured from CAD
with `Tools/HangboardCAD/measure_channel_spines.py`, and the visible routes
and hanging height are solved against the exported CAD solid with
`Tools/HangboardCAD/solve_threaded_rope.py`. Do not hand-place cord contact
points, anchors that stand in for a solve, or `pairedLeadCord` leads on a CAD
board. The runtime's convex-section fallback and hand-authored
`pairedLeadCord` / `singleCord` metadata remain only for older non-CAD
packages; migrate a board's cord to this method when the board moves to CAD.

These boards use it:

| Board | Channel | Section plane | Notes |
| --- | --- | --- | --- |
| Lattice Mini Bar | curved `PartDesign::SubtractivePipe`, two mouths on one face per end | `mouth-x` (default) | constant-section bar; four grip poses |
| Crimptonite Helium Mobile | straight `Part::Cylinder` through-bore, front and back mouths per end | `anchor` | mouths sit in the rounded ends; one loop of cord through both holes |
| Metolius Rock Rings | connected `Part::MultiFuse` void with linked ordered spine | none (direct-leg solve) | one continuous loop per displayed ring; exact native-solid clearance |

Rock Rings extend the topology to one branch with two mouths and retain the
whole measured channel centerline in `internalLoop.channelPointsByBranchID`.
The solver settles the board from total cord length and checks both free legs
and the interior path against the native solid in FreeCAD Python. The spine is
rendered as transient cord geometry, hidden by the body except at its openings.
Schema-2 sidecars attach this setup to each independent instance of the same
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

`suspension.json` stores two point mouths per loop, their body node, branch
pairing, one overhead anchor, estimated radius and rest length, canonical
board poses, a positive clearance, `internalLoop.windingByPassageID`, and
`internalLoop.channelLengthByBranchID` measured from the CAD pipe spines.
The passage IDs and pair order are part of the topology. The sidecar is bound
to the model descriptor's `modelSHA256` and checked by package validation;
`board.json` is generated from the FCStd manifest plus this sidecar.

`Tools/HangboardCAD/export_rope_collision_solid.py` tessellates the final,
watertight FreeCAD wood solid as an authoring intermediate. The reusable
`solve_threaded_rope.py` intersects that solid at each mouth, offsets the
section by the cord radius plus declared clearance, and finds the shortest
collision-free exterior path in the passage's winding direction. It includes
the CAD-measured hidden channel length, then lowers the board beneath the
fixed support until the longer of its two loops uses the declared length.
The other loop may have at most 0.5 mm slack. Every visible segment is sampled
at 0.5 mm against the native 3D solid before the solver updates the sidecar.

The resulting translations and centerline contacts are a **generated cache**
under each `canonicalPoses` entry in `suspension.json`. Authors specify mouths,
threading, channel length, loop length, and overhead support, then rerun the
tool; they do not draw pose contacts. `--check` regenerates the cache and
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
would work. See [the experiment and its measured limits](../Tools/HangboardRopePrototype/README.md).

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
4. The model has two branches, four distinct point mouths, and one winding
   choice for each mouth. Each branch's `passageIDs` lists its paired mouths
   in traversal order.

The `threadedLoopCord` extension instead requires one branch with two distinct
mouths, its complete ordered native channel spine, and unobstructed rising
legs. It does not use a section plane or surface winding; exact native-solid
checks enforce cord radius plus the configured internal-loop clearance.

**Channels.** A channel is either a curved `PartDesign::SubtractivePipe`
(its Sketcher spine is measured) or a straight `Part::Cylinder` through-bore
(its axis is measured). A through-bore's two mouths lie in the same section,
which the bore cuts in two; the solver bridges that gap to recover the
exterior outline and reopens only the notch at the mouth it is solving.

**Section planes.** The sidecar's optional, authoring-only
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

## Authoring sequence for another board

1. Inspect the exact product revision from several manufacturer views and
   record the route graph and unknowns in a source audit. Confirm whether
   each cord is one piece, where it enters and exits, and whether any segment
   is hidden in the board. Request owner input for genuinely occluded facts.
2. Author the body and connected channel in the native FCStd. Confirm the
   shape recomputes, the mouths open at the declared coordinates, and the
   exported USDZ has neither cord nor material bindings. Record estimated
   diameters and offsets as estimates.
3. Put suspension in the adjacent `suspension.json` for a CAD package. Bind
   all mouths to the body node, pair each loop, supply the overhead anchor,
   and choose each winding from the evidence. Measure the paired-mouth length
   from each channel's spine (pipe spine or bore axis) with
   `Tools/HangboardCAD/measure_channel_spines.py`; record it in
   `internalLoop.channelLengthByBranchID` and rerun the tool with
   `HANGTEN_CHANNEL_VERIFY=1` to catch sidecar drift. For every canonical grip,
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
   on the loop length, not on that offset. Then export the final native
   solid, run `solve_threaded_rope.py --apply`, then rerun with `--check`.
   When a winding is in doubt, compare each mouth's route length and turn for
   both directions; the physical one is normally the short route over the
   nearest edge.
   Generated pose routes are a cache in the sidecar, not operator-drawn
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

The Mini Bar's generated routes found at least 2.097 mm exterior
centerline-to-wood clearance with a 2 mm estimated rope radius. Those numbers
are specific to its display model; they are not a general rope or safety
specification.
