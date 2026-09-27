# Lattice Mini Bar cord passage correction

Reviewed 2026-09-27 after the user identified through-holes in the Mini Bar.
This corrects the cord interpretation in the August presentation audit, the
September CAD provenance, and the offline Bullet prototype. The approved
gallery is still the same physical revision.

The user then confirmed **two separate bores per end** and supplied an
additional photo of the bar in use. This is the topology for the CAD revision:
four transverse bores total, two at each end, with an exterior bight between
the two visible mouths at each end.

## Evidence

- [Lattice Web-1](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-1.jpg)
  shows cord entering small openings in the wooden side near both ends, with
  exterior bights visible below. The retained snapshot is
  `2026-09-13-model-cord-snapshots/lattice-mini-bar-Web-1.jpg` (SHA-256
  `610cfaa96a95d80ae0d37ef4bbf2b1d881b47d0813d7d0eb4f9db9b5c30270de`).
- [Lattice Web-2](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-2.jpg)
  shows the cord curving around the end section. The end photo alone does not
  reveal the passage axis inside the wood. Its retained September snapshot
  has SHA-256 `3b4c28e84d46972cd6f2d3be241d148c8fe1eac9aefce54bb0d223470165f037`.
- Lattice's [Mini Bar product page](https://latticetraining.com/product/mini-bar-portable-hangboard/)
  contains a review describing wear near the “rope holes.” Lattice's reply
  confirms that cord position can slip under initial load and be readjusted.
- Lattice's [How to Use the Mini Bar video](https://www.youtube.com/watch?v=hHt20hop3UU),
  especially 00:28–00:32 and 01:40–02:00, shows strands emerging from
  openings near the ends while exterior bights remain visible. The 00:30
  frame is retained for inspection at
  `.context/frantic-kiwi/video-frames/frame-030.jpg`.

## CAD and simulation discrepancy

The current `lattice-mini-bar.FCStd` body is a single `EndProfile` pad
(`LengthPad`) over 155 mm with no local bore or pocket feature. The exported
body has only the two end X coordinates; it cannot contain passages at the
cord positions near each end. `suspension.json` stores two representative
points per end but labels their Y/Z coordinates as display estimates. They
are not verified bore endpoints: one of the points at each end is about
10.9 mm inside the current exported surface.

The Bullet prototype pins an inferred point on a bounding circle at each
strand X coordinate. Those pins are not the product's hole boundaries. Its
zero-of-eight contact finding applies only to that **solid-bar surrogate**;
it does not test whether a cord threaded through the actual Mini Bar can
contact its surface. The prototype must not be promoted into the app or used
as a physical fidelity verdict.

The gallery and video prove openings and exterior bights. They do not supply
an unambiguous interior bore path or measured diameter. A CAD revision must
model deliberately chosen passage geometry and label its dimensions as
estimates, then recompile the USDZ and update the hash-bound sidecar. The cord
remains outside the USDZ as transient geometry; the CAD only contains wood.

## Authored correction

The revised native FreeCAD source retains the ovoid `EndProfile` and 155 mm
`LengthPad`. `CordBoreCenters` is a fully constrained four-circle Sketcher
profile; `CordBores` is a 90 mm PartDesign pocket through the full section.
The deliberately estimated bore centers are X = -69, -57, +57, +69 mm and
native Z = 24 mm, with 5.4 mm diameter. The pocket cuts through both long
faces. Native section inspection at Z = 24 mm found the two face intersections
at Y = -67.183 and -5.124 mm; the suspension sidecar converts these to model
Z = +0.067183 and +0.005124 m. At Z = 17 mm, the existing open pinch relief
would split each nominal bore into separate wood segments, so that position
was rejected during authoring.

The revised USDZ contains only the wooden body and contact surfaces. The
sidecar binds four directed through-bores to `mini_bar_body`, with a transient
exterior bight at each end. Each pose's exterior contact points were calculated
from the CAD's circular outer section, the bore mouths, and the overhead
anchor, then retained in the sidecar because the current through-bore runtime
contract requires explicit routes. The cord centerline lies 2.1 mm outside
the arc for an estimated 2 mm radius. The native FreeCAD solid intersection
check found no centerline penetration in any of the eight pose/branch routes
away from the intended internal bore spans. Bore centers, diameter, cord
radius, mouth coordinates, exterior contact points, 120 mm anchor offset, and
0.82 m per-branch rendering capacity are **display estimates**, not
manufacturing measurements or a claim about supplied rope length. The
through-bore topology comes from the user's explicit correction and Lattice's
approved gallery. The native profile, bore positions, and route should be
revisited if measured bare-board evidence becomes available.

The front, side, and top comparison against the prior committed asset is
`.context/frantic-kiwi/mini-bar-bore-comparison.png`. It shows four openings
on the long face while the end section remains ovoid. A four-pose side review
of the CAD section and transient centerline is
`.context/frantic-kiwi/mini-bar-cord-side-poses.png`; a current-source iPhone
Simulator screenshot of the default jug pose is
`.context/frantic-kiwi/mini-bar-app-front.png`. The CAD compiler, package
validator, cord audit, and all 57 focused iOS suspension tests pass on the
isolated iPhone 17 Pro simulator. These checks
do not yet prove full tube clearance or visual quality from every in-app orbit
angle. The current RealityKit renderer uses the retained per-pose routes for
through-bores, so this correction establishes physical topology and a
no-penetration centerline but does not yet provide the user's requested generic
holes-plus-anchor runtime solver.
