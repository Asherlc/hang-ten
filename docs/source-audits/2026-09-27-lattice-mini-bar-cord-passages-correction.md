# Lattice Mini Bar cord passage correction

Reviewed 2026-09-27 against the user-approved Lattice Mini Bar gallery: Web-1,
Web-2, Web-7, Web-8, Web-9, Web-10, and Web-11. Their exact URLs, retained
snapshots, and SHA-256 values are in
`2026-09-13-model-hangboard-cord-audit.json`. The user also supplied a loaded
photo and clarified the threading: there are two openings near each end,
connected by a passage **inside** the wood; the rope emerging from those
openings rises as **one continuous loop** per end. The blue curve beneath the
wood in Web-2 belongs to that same loop.

## What the photos establish

- [Web-1](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-1.jpg)
  shows both end loops tensioned and bearing near the underside of the bar.
- [Web-2](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-2.jpg)
  shows an ovoid end, two rising strands, and the continuous lower curve.
- [Web-7](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-7.jpg),
  [Web-8](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-8.jpg),
  [Web-10](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-10.jpg),
  and [Web-11](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-11.jpg)
  show loaded oblique views across different grips.
- [Web-9](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-9.jpg)
  adds a loaded end view. The hands obscure the exact opening edges.

The photos do not expose the channel inside the wood or provide a measured
channel diameter, mouth spacing, rope diameter, or exact camera/board pose.
Those dimensions remain **display estimates**. Lattice's how-to video was
consulted as supplemental research, but the approved seven gallery views and
the user's topology corrections govern this CAD authoring.

## Native geometry and transient cord

The native FreeCAD source retains one ovoid `EndProfile` and a 155 mm
`LengthPad`. Two `PartDesign::SubtractivePipe` features cut one smooth,
connected U channel near each end. The four mouth centers are at native
X = -69, -57, +57, +69 mm, Z = 24 mm on the estimated front surface;
the estimated channel diameter is 5.4 mm. The resulting solid recomputes
validly, and the materialless USDZ contains the wood and its contact surfaces
only. There is no rope mesh in the CAD source or USDZ.

`suspension.json` binds the four mouth points to the exported body and declares
two loops, one per end. Each loop follows one free leg from the common overhead
point to a mouth, passes through the hidden connected channel, then follows the
second free leg back to the same overhead point. `internalLoop.clearance` is
0.1 mm and the estimated cord radius is 2 mm. A single
`windingByPassageID` choice records which side of the ovoid each leg leaves its
mouth on. It is threading topology, authored once per passage, **not** a list
of pose-specific coordinates. For every selected grip, the app derives the
visible bearing path from the loaded body mesh, the four mouth positions, and
the fixed overhead point. The direction choices let one leg per loop bear
under the wood as the approved photos show. The rope is transient,
non-pickable, and absent from the USDZ.

The route solver offsets the ovoid section by the rope radius plus clearance.
A native FreeCAD solid-intersection check across all four poses and all four
visible leads measured a minimum **2.09 mm centerline-to-wood distance** on
the exterior route, giving about 0.09 mm surface clearance for the estimated
2 mm rope radius. The final lead segment enters its actual channel mouth
without crossing wooden solid. The invisible channel segment is represented
by the CAD void; its centerline is not rendered.

## Visual and package review

The front, side, and top before/after CAD preview is
`.context/frantic-kiwi/internal-cad-preview/front-side-top-before-after.png`.
The approved-photo comparisons are
`.context/frantic-kiwi/mini-bar-Web-{1,2,7,8,9,10,11}-vs-CAD.png`, and the
four-pose end and side matrices are `mini-bar-end-pose-matrix.png` and
`mini-bar-Web-1-all-pose-matrix.png` in the same workspace directory. The
review renderer depth-sorts rope and wood; it uses hand-chosen approximate
camera directions and canonical poses. It is a topology and contact review,
not a photogrammetric match. Knots and hands are absent from the display.

The compiled USDZ and descriptor hashes match, and the sidecar is bound to
the descriptor's `modelSHA256`. Package validation and all 722 package tests
passed. The focused and full iOS test targets passed in isolated iPhone 17 Pro
simulators. The launched app was captured for all four selected grips at
`.context/frantic-kiwi/mini-bar-app-{ergonomic-jug,edge-10,edge-20,mini-pinch}.png`.
The simulators were deleted and deletion verified. The exact native
validation commands and final hashes are recorded by the delivery lock.
