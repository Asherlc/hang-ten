# Geometric cord-point view pivot

The user requested rebuilding cord-point X-axis rotation directly on `main`,
without depending on the live physics branch. Base:
`cd78de5c8ad19147a42373eedf4d70d0142ea65c`. Worktree: `large-hyena`;
branch: `corded-board-geometric-pivot`. The original
`corded-board-cord-rotation` branch remains preserved separately. No commits
from that branch or `feat/live-hangboard-physics` were imported.

## Behavior and boundary

Main's rotation interaction is a camera orbit. The shared viewer now pitches
around the midpoint of the authored cord attachments or passage mouths in the
current placed board pose. Through-bores use both mouths; point passages use
one. Original model coordinates are reflected when a display mesh has a baked
reflection. Separate instances contribute their placed suspension points.
Yaw keeps the existing canonical framing pivot. Uncorded boards keep the
existing framing behavior. The complete board/cord envelope is refit relative
to the resulting camera target. Reset returns exactly to the canonical view.

The normal loader uses bundled suspension geometry directly and does not start
a live rope controller. Main already includes an earlier solver and Clavellium
physics descriptor: those remain untouched and are available through explicit
`useLivePhysics: true` loader calls. The two existing loader-based live solver
integration tests now opt in explicitly. No solver, physics descriptor,
suspension metadata, CAD, USDZ, model descriptor, material, or catalog flag was
changed. This change is a geometric viewing rule; it does not claim mechanical
simulation, cord-constrained translation, or physical equilibrium.

## Verification

The behavioral RED on main ran
`testClavelliumPitchOrbitsAroundItsCordPointsWithoutPhysics`: the normal loader
started live physics and pitch shifted the midpoint's camera-space Y by about
4.61 mm. One completed test reported five assertion failures in 45.185 s;
receipt: `.context/geometric-cord-pivot/red.log`.

After the change, all 288 affected native tests pass in 43.863 s, optimized
Debug (`SWIFT_OPTIMIZATION_LEVEL=-O`): 58 RealityKit scene, 6 model, 159 package
store, 65 suspension presentation tests. The new tests cover Clavellium pitch
with and without yaw, unchanged body/cord geometry, exact reset, Nature Stone
Hanger paired attachments, Flash Board through-bore mouths, and placed Rock
Ring instances. The Mini Bar all-grip viewport test now includes positive,
negative and combined yaw/pitch. Existing hold visibility, selection, resource,
clear/reappear, suspension, and explicitly enabled live solver tests pass.
Receipt: `.context/geometric-cord-pivot/green.log`.

Normal Debug `build-for-testing` also succeeds:
`.context/geometric-cord-pivot/normal-build.log`. Existing SDK asset diagnostics
and duplicate-resource/build-script warnings were emitted; no test failures
remain. Source hashes, commands, capture sequence and build provenance appear
in `.context/geometric-cord-pivot/provenance.json`.

Current-source native app review covered Clavellium's initial view, manual
upward/downward tilt, automatic top-pinch selection and return to the front
angle. The last physical AXe tap aimed at the projected 20 mm center but hit
90 mm Pinch Back, as the screenshot shows; that selected grip returned to the
front view. It is not reported as a successful 20 mm pick. Exact camera reset
is independently verified by the native regression. Screenshot contact sheet:
`.context/geometric-cord-pivot/geometric-pivot-sequence.png`. Actual commanded
gesture coordinates and selected contacts are retained in provenance; angles
are not inferred from pixels.

## Cleanup

The isolated simulator `FA773ED9-118A-4C4E-8665-4B71FF7FB213`, named
`Hang Ten Paseo large-hyena Review`, was registered immediately and guarded by
EXIT/INT/TERM cleanup before creation. It is deleted and absent from simulator
inventory. Pending/owned manifests and workspace DerivedData are absent.
XCTest summaries were retained before DerivedData deletion. Verification:
`.context/geometric-cord-pivot/cleanup.json`. Shared resources and other
worktrees were left alone.
