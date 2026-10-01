# Fixed-cord geometric board rotation

The user requested a main-based implementation without depending on the live
physics branch, then clarified: “Keep the cord fixed while the board turns.”
Base: `cd78de5c8ad19147a42373eedf4d70d0142ea65c`; branch:
`corded-board-geometric-pivot`; owner: `large-hyena`. No commits from the cord
physics branches were imported.

## Final behavior

Pitch changes only the board transform. The entire canonical cord, including
free spans and guides, remains untouched. The board turns around its authored
attachment axis, independently for each instance. A single through-bore uses
its mouth-to-mouth line. Multiple passages use their centers and widest
separation through their mean; paired leads use the attachment line. A single
attachment falls back to the canonical view's horizontal axis through that point.
The axis includes authored instance reflection and stays fixed through yaw.

Clavellium rotates around the line joining its two passage points, preserving
both points rather than only their midpoint. The camera fits the board's local
rotation envelope from rest, then stays exactly fixed through pitch. This also
keeps the cord stationary on screen. Manual yaw and zoom retain their existing
camera interaction. Reset restores the exact canonical body pose.

Automatic adjustment uses the canonical board pose to avoid accumulated tilt,
animates over 0.28 seconds, and refreshes projected contact controls. Reduce
Motion and inactive scenes apply immediately; gestures and lifecycle changes
cancel superseded animation.

The normal loader starts no live rope controller. Existing solver integration
tests explicitly opt in. Solver files, physics descriptors, suspension metadata,
CAD, USDZ, materials and catalog flags are unchanged. This is a geometric display
hinge, not a collision or equilibrium solve; the canonical cord is not rerouted
around a turning board.

## Superseded evidence

The first implementation moved only the camera. The second rotated the board
about the cord midpoint, moved its attached guides and reconnected free spans,
and changed camera distance during pitch. Neither implements the clarified
fixed-cord behavior. Their `actual-*` evidence is historical, not final proof.

## Verification

The fixed-cord regression first failed eight assertions against the second
implementation: the camera moved, cord transforms changed, and each Clavellium
passage point moved about 11.877 mm at 20 degrees. One test completed in 1.920
seconds with no compile failure. Receipt:
`.context/geometric-cord-pivot/fixed-cord-red.log`. The exact owned diagnostic
capture spawned after the failed test was stopped after the completed failure
receipt was retained; no test process or unrelated simulator was terminated.

All 289 affected native tests pass: 59 RealityKit scene, 6 model, 159 package
store and 65 suspension presentation tests (optimized Debug, 46.734 seconds
of test execution). Final test/build receipts and capture provenance are retained as
`.context/geometric-cord-pivot/fixed-cord-*`. Native tests assert actual body
rotation, unchanged full cord transforms, unchanged full camera transform, both
fixed passage points, and exact reset. Existing cases cover automatic selection,
unchanged selection, paired attachments, bore mouths, independent instances,
viewport fit, package loading, suspension presentation and opt-in live solvers.
The simulator sequence captures rest, rotation both ways and return, from an
optimized Debug build matching the passing test configuration. Its frames share
the same camera and cord geometry. The unobscured cord image patch at
(450, 980)–(750, 1300) is pixel-identical across the three rotation states.
Contact sheet: `.context/geometric-cord-pivot/large-hyena-fixed-cord-sequence.png`;
loop of captured states: `large-hyena-fixed-cord-rotation.gif`. Normal Debug
build-for-testing also succeeds, but its first runtime launch showed a blank
screen; those blank captures are discarded, not presented as visual validation.
Source/build/capture provenance is in `fixed-cord-provenance.json`.

## Resources

Simulator `ADB72BAC-D51A-4779-A49A-9D78B0FE390D`, named
`Hang Ten Paseo large-hyena Review`, was registered immediately and guarded by
EXIT/INT/TERM cleanup. Final deletion and removal of workspace DerivedData are
verified in `.context/geometric-cord-pivot/fixed-cord-cleanup.json`.
Shared resources and other worktrees were left alone.
