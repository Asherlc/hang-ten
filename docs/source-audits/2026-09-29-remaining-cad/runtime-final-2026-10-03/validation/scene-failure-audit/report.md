# Native scene failure audit

Workspace: `placid-badger`. Scope: read-only geometry and runtime diagnosis, followed by the explicitly reserved two-method test correction. No canonical geometry, material, manifest, or suspension edits by this agent. No Simulator or build operations by this agent.

## CAD pitch failure: production contract violation with one stale coordinate

The original run in `commands/full-green.log` reported paired-attachment pivot displacement of approximately 7.653388 mm for Nature Stone Hanger and 1.75533 mm for Flash. A float32 replay of the original helper reproduces those values from current accepted metadata; see `cad-hinge-numeric-evidence.json`.

The helper treated both the first and last points of every cached route as attachment stations. For native CAD lead routes, the first point can be an exterior wrap lip or guide point. Combining it with the actual terminal changes both the average pivot and the farthest-pair axis. Nature's original test pivot still equals the current terminal mean. Flash's old pivot has a separate 0.669699 mm Z offset from its current terminal mean.

Replacing only those pivot coordinates would leave a real body/cord contract violation. Native cached routes include distributed, non-collinear bearing stations on the board solid. Even a horizontal axis through the actual terminal mean would move fixed-route bearing stations by up to 17.046086 mm on Nature and 14.812543 mm on Flash at 20 degrees. The cache was certified against the source-solved body transform, not an arbitrarily pitched body under a stationary cord.

`docs/HANGBOARD_CORD_AUTHORING.md` specifies body-space `wrappedRoutes`, the fixed world support, transient tubes, and no live physics solving for this cached `cadRoutedCord` path. `SuspendedBoardPresentation.swift` composes the solved board transform and selected model transform before building the body and routes. The minimal correction is camera orbit for `cadRoutedCord`, retaining both source-solved body and complete cord transforms. Keep the existing attachment-axis board tilt for non-CAD single, paired-lead, and two-branch profiles.

The root agent has applied this correction in `BoardModelRealityTypes.swift:1495` and owns its new native orbit regression. Meaningful validation requires unchanged body/cord matrices during camera orbit, a changed camera/projection, and exact reset; replacing the old CAD pivot assertion with a new guessed hinge would weaken the native clearance gate.

## Forge winding and spacing failures: stale representation expectations

The old normals test required a runtime reflected instance; current accepted Forge is one full native paired export. Its left half is authored by native `Part::Mirroring`, and both halves are already in the USDZ. No runtime reflected instance is expected. The related spacing test expected two model roots and then indexed root 1, causing a fatal error when the actual imported root count was one.

The source USD audit in `forge-authored-normal-winding.json` covers the body and all 20 contact meshes: 21 nodes, 20,748 nondegenerate triangles, zero inward winding/normal disagreements at the existing Swift thresholds. Asset SHA-256: `6af1091171a5251914983b6d9c17859eb7e85fe35e15628d5c3c164fe2b8ba61`. The body itself contributes 8,784 triangles, split 4,392 per side, with inner X bounds ±0.076200001 m and outer X bounds ±0.400050014 m. This is authored USD evidence; it does not claim a RealityKit test pass.

The two reserved methods in `HangTenTests/BoardModelRealityTests.swift` now preserve strict native checks:

- `testMirroredBoardNormalsAgreeWithRenderedTriangleWinding` recursively reads actual imported body/contact meshes and instance transforms. Forge must have one native root, 20 contacts, 21 descriptor nodes, exact contact IDs, at least 20,748 checked triangles, zero inward normals, and equally populated nonzero left/right triangle sets. Other boards retain runtime reflection and source winding checks.
- `testRockProdigyPairsPreserveSpacingAndIndependentContactEntities` reads all actual Forge imported mesh coordinates, including body points. It requires a positive center gap, symmetric inner/outer and Y/Z bounds, exact contact inventory, distinct paired contact entities, and symmetric per-pair bounds. Natural and Training Center retain their two-instance contracts. Root-count guards precede indexed access.

Only these two methods were edited by this agent. `git diff --check` passed after the final scoped patch. Build and native XCTest results belong to the root agent's owned verification; this report makes no passing-runtime claim.
