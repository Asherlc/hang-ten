# Geometric cord-point board tilt

The user requested rebuilding cord-point X-axis rotation directly on `main`,
without depending on the live physics branch. Base:
`cd78de5c8ad19147a42373eedf4d70d0142ea65c`. Worktree: `large-hyena`;
branch: `corded-board-geometric-pivot`. No commits from
`corded-board-cord-rotation` or `feat/live-hangboard-physics` were imported.

## Corrected behavior

The first implementation moved only the camera. Its original tilt sequence
left the board and cord unchanged relative to one another, as the user observed.
That evidence and the camera-only contract are superseded by this correction.

Pitch now changes the actual board transform about its own authored cord-point
midpoint. Through-bores contribute both mouths; point passages contribute one;
paired cords use their attachments. Each independent instance has its own
pivot. Authored reflection is retained when calculating the pivot, while the
renderer retains its existing baked reflection convention.

Overhead supports stay fixed. Canonical guides move rigidly with the board;
free spans reconnect to the fixed support. Existing cylinder transforms are
updated in place. Yaw remains a camera orbit; pure pitch keeps camera orientation
fixed. Framing includes each board's local rotation envelope. Reset restores the
exact canonical board and cord transforms. Automatic hold visibility is evaluated
in the canonical pose so selection changes cannot accumulate tilt. Automatic
adjustments animate for 0.28 seconds with projected controls refreshed; Reduce
Motion and inactive scenes apply immediately. Manual orbit, position changes,
disposal and inactivity cancel pending geometric animation.

The normal loader does not start a live controller. Existing solver integration
tests explicitly opt into `useLivePhysics: true`. Solver files, physics descriptors,
suspension metadata, CAD, USDZ, materials and catalog flags are untouched.
This is a kinematic display approximation: free-span lengths can change and
there is no gravity, rope-length constraint or sliding-contact equilibrium solve.
Canonical guide paths are retained rather than physically rerouted at each tilt.

## Verification

The corrected behavioral RED on the camera-only implementation ran
`testClavelliumPitchMovesBoardAroundCordPivotWhileSupportAndCameraStayFixed`:
the body matrix and top point did not move, and the camera orientation changed.
One test produced eight assertion failures in 2.012 seconds, with no compile
failure. Receipt: `.context/geometric-cord-pivot/actual-red.log`.

All 289 affected native tests passed with zero failures: 59 RealityKit scene,
6 model, 159 package store and 65 suspension presentation tests (optimized
Debug, 41.905 seconds of test execution). Final native test and normal Debug
build receipts are retained at
`.context/geometric-cord-pivot/actual-green.log` and
`.context/geometric-cord-pivot/actual-normal-build.log`. Tests require body motion,
fixed pivot, fixed support, fixed camera orientation, exact reset, automatic top
selection and clear, unchanged-selection stability, paired attachments,
through-bore mouths, independent instances, and all-grip Mini Bar viewport fit.
The affected suites also cover package loading, suspension presentation and the
explicitly enabled solver integration lane.

The corrected current-source simulator sequence shows Clavellium at rest,
manually pitched both ways, and automatically tilted for 100 mm Pinch Top.
Contact sheet: `.context/geometric-cord-pivot/actual-geometric-pivot-sequence.png`.
Semantic top taps initially did not select the hold. After returning to the
upward view, a physical tap at (201, 480) selected 100 mm Pinch Top, verified
by the selected-hold label and red highlight. Commanded gestures, source hashes
and receipts appear in
`.context/geometric-cord-pivot/actual-provenance.json`. Angles are not inferred
from screenshot pixels. Exact reset is verified by the native regression.

## Resource ownership

Simulator `DC20AC37-68AB-4B92-9F40-F7B1DE68E6DC`, named
`Hang Ten Paseo large-hyena Review`, was registered immediately and guarded by
EXIT/INT/TERM cleanup. Final deletion and removal of workspace DerivedData are
verified in `.context/geometric-cord-pivot/actual-cleanup.json`.
Shared resources and other worktrees were left alone.
