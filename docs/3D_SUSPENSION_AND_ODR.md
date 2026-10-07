# 3D hangboard suspension and Apple On-Demand Resources

This guide is the diagnosis, authoring, and verification reference for cords on
Hang Ten model-media boards. Use the repository skill
`audit-3d-hangboard-suspension` when a 3D board is missing an expected cord or
when an Apple offline/On-Demand Resources cache is suspected.
For native internal passages and exterior bearing, read
[CAD cord authoring](HANGBOARD_CORD_AUTHORING.md) before editing a package.

## The shipping boundary

A model presentation crosses two different delivery paths:

| Content | Source | Shipping path | Runtime role |
| --- | --- | --- | --- |
| Board identity, positions, `media.suspension`, and display configuration | Flat FCStd manifest plus validated generated `assets/suspension.json`, staged as `board.json` | Main app bundle | Parsed into `BoardModelMedia`; selects transient cord geometry |
| Model descriptor and its expected `modelSHA256` | Generated `assets/*.model.json` | Main app bundle | Validates model identity, bounds, nodes, attachments, and physical-contact bindings |
| Material-free board mesh | Generated `assets/*.usdz` | Apple On-Demand Resources (ODR) in production | Decoded by RealityKit after access and SHA-256 validation |

`scripts/stage-board-packages.py` copies each validated regular-file package
tree into the app resources while excluding each model presentation's
`assetPath` and the standalone generated `assets/suspension.json` after merging
its runtime metadata. The flat source `Hangboards/<slug>.FCStd` sits outside
the package tree and is never staged. Excluded USDZ files are staged for ODR
separately. For a CAD package the script writes `board.json` generated from the
FCStd's `HangTenBoardManifest` and validated suspension artifact into the staged package.
Therefore `board.json` and the descriptor remain ordinary bundled metadata; the
cord is not part of the downloaded model asset. Android stages with the same
script (`--target android`), which keeps the USDZ inline instead of splitting it
out for ODR.

Run `rtk proxy bash scripts/build-board-assets.sh` before package validation,
or `rtk proxy bash scripts/build-runtime-assets.sh` before a fresh-checkout app
build. The pinned native build derives the USDZ, descriptor, and optional physics
descriptor and solved suspension artifact from retained source inputs. Cord and
simulation authoring is embedded in document-level `App::PropertyString`
`HangTenSuspensionAuthoring` and `HangTenRopePhysics`. These runtime files are ignored by Git;
CI consumers download the producer artifact before staging. The authoring
boundary is described in [generated artifacts](GENERATED_ARTIFACTS.md).

`BoardPackageStore` parses and validates bundled package metadata, registers an
ODR `BoardModelResource` for an on-demand USDZ, and passes the parsed suspension
through `BoardModelMedia`. `BoardModelView` acquires the production resource
with `NSBundleResourceRequest`; DEBUG Simulator builds may resolve the signed
packaged ODR file directly because the simulator installer does not register
the nested asset pack with the ODR service.

The model cache is an in-flight load coalescer keyed by board ID, presentation
ID, and descriptor `modelSHA256`; it is not a persistent scene cache.
`BoardModelResourceLease` retains successful ODR access through model loading
and scene use, then balances it with `endAccessingResources()` on deinit.
`BoardModelRealityCache` verifies the resource file's exact SHA-256 against the
bundled descriptor before `BoardModelRealityLoader` loads it through ModelIO
into the RealityKit scene.

The practical conclusion is firm: if the expected board mesh loads but a cord
does not render, invalidating or redownloading Apple's offline ODR asset cannot
repair it. Inspect the bundled `board.json`, selected position, parser result,
and transient suspension-renderer path. ODR is a plausible boundary only when
the model is unavailable, its resource URL cannot be resolved, its bytes do not
match the descriptor, or RealityKit cannot decode it.

## Cord-point display tilt

The normal RealityKit viewer uses bundled suspension geometry without starting
live rope simulation. Pitch rotates each corded board instance about the line
through its authored cord attachments or passage centers. A single attachment uses the canonical view's
horizontal axis through that point. Multiple points use their widest separation
through their mean. Authored reflection is retained when calculating this axis.

The entire cord stays in its canonical pose, including guides and free spans.
Pitch changes only the board transform. The camera fits the board's local
rotation envelope at rest and keeps the same transform during pitch, so the
cord also stays fixed on screen. Yaw and manual zoom retain their existing
camera interaction. Reset restores the exact canonical board transform.
Automatic hold adjustment is calculated from the canonical pose to avoid
accumulating tilt and animates over 0.28 seconds; Reduce Motion applies it
immediately. Manual gestures and lifecycle changes cancel superseded animation.

This is a geometric display hinge, without a rope collision or equilibrium
solve. Canonical cords are not rerouted when the board turns. Uncorded boards
retain camera pitch when all instances are uncorded. In a mixed scene,
uncorded instances rotate about the framing target with the inverse of that
camera pitch, preserving their pitch view alongside the fixed cord. The loader's `useLivePhysics` opt-in retains the existing
solver integration test lane.

## Diagnose by symptom

| Symptom | First boundary to inspect | Do not use as a shortcut |
| --- | --- | --- |
| Correct model loads, expected cord absent | Bundled `media.suspension`, selected `positionID`, parser dispatch, transient scene layer | ODR cache purge or USDZ replacement |
| Model is explicitly unavailable | ODR acquisition/debug packaged URL, resource lease, regular-file check, SHA-256, ModelIO/RealityKit load | Raster fallback or a guessed model path |
| Wrong or stale mesh appears | Installed app/build provenance, ODR tag and descriptor hash, staging output | A screenshot from an unproven prebuilt app |
| Cord moves incorrectly for one contact/face | Position-to-pose mapping, attachment override, solved destination state | Independent animation or camera changes that hide the defect |
| Cord is selectable or blocks a contact | Native picking and scene-category configuration | Moving the cord visually without proving clearance |

A prebuilt app or CI artifact is valid visual evidence only when its commit is
at or after both the renderer implementation and the bundled metadata being
reviewed. A build that predates either boundary must not be presented as proof,
even if its USDZ hashes happen to match.

## Re-audit the current inventory

Discover model packages at execution time; never copy a historical package
count into a decision. Validate current suspension directly from the native
manifest, embedded suspension authoring, and generated `assets/suspension.json`,
and read each board's retained
source audit. There is no supplied catalog-wide cord-audit manifest.

The optional `audit-cords --manifest <cord-audit.json>` command accepts an
explicit closed source-audit document and requires exact equality between its
records and the discovered model packages. A generated suspension artifact does not have
that schema and must not be passed as an audit manifest.

When using a closed cord audit, each record has these independent parts:

- `sourceFact`: `documentedSuspension` or `noDocumentedSuspension`;
- `decision`: `represented` or `excluded`;
- a topology for represented records and `null` for exclusions;
- a nonempty ruling;
- retained exact-revision evidence with source tier, URL, unique snapshot path,
  and verified SHA-256; and
- explicit human approval with reviewer, date, and notes.

Both represented and excluded decisions require retained evidence. Optional
user-provided rope or bungee evidence can establish a suspended presentation,
but it does not establish that the accessory is supplied, integral, rated, or
safe for a particular load.

Current retained evidence and the audit outcome govern representation decisions.
Preserve each board's CAD-contained topology and solver inputs; a package name
or older design assumption does not establish an unseen connection.

## Select the narrowest truthful topology

For a CAD board, preserve the evidenced connection graph and follow
[CAD cord authoring](HANGBOARD_CORD_AUTHORING.md). Connected internal mouth
pairs use the standard CAD passage void, measured channel length and
`twoBranchCord` (or `threadedLoopCord`) with `internalLoop`. Source-backed
independent visible leads, exterior wraps and unknown interior joins use
`cadRoutedCord` with authoring `ropeSolver.method: "nativeRoutes"`; do not
invent a hidden connection. Generate every canonical pose against the actual
native solid through the pinned build's `compile_suspension.py` and native
solvers. For focused reproduction, adapt and run the complete
[owned-shell example](../Tools/HangboardCAD/README.md#focused-cord-reproduction)
for the board and its native solid features. Export the collider and run the
solver check inside that same shell, before its cleanup removes the environment
and collider.
Retain native-solid clearance, length, tube and topology checks. Extend the solver
with evidence and tests when the supported native methods do not fit.

Five CAD sources retain legacy `pairedLeadCord` directly in their manifests,
without `HangTenSuspensionAuthoring`: `captain-fingerfood-pocket`,
`j-bryant-ftg-32`, `lattice-mxedge-lift-large`, `lattice-mxedge-lift-small`, and
`metolius-light-rail-2`. Preserve these existing representations pending separate
evidence-backed revisions. They do not authorize new hand-authored CAD routes.
The table below describes the supported legacy forms and connected branches.

| Type | Package meaning | Evidence and geometry boundary |
| --- | --- | --- |
| `singleCord` | One attachment and one branch to a shared invisible display anchor | Use only when one physical attachment is established. The attachment binds to an importer-visible body/attachment node, never a selectable contact node. |
| `pairedLeadCord` | Two independent exterior leads from two distinct attachment points to one invisible anchor | Represents visible leads without inventing a lead-to-lead or hidden interior route. Optional ordered `contactPointsInModel` may preserve an evidenced exterior over-lip route before the terminal attachment; per-pose attachment-point overrides must retain both lead IDs and remain distinct and in bounds. |
| `twoBranchCord` | Two branch routes through four uniquely identified passages arranged as two ordered pairs | Use directed entry/exit bore routes only when the complete through-route is evidenced. For `internalLoop`, each pair is two point mouths connected by a CAD channel and requires a winding choice for each mouth. Never fabricate a hidden bore from a visible mouth. |

Attachments and passages bind against importer-visible IDs in the hash-bound
descriptor. Preserve contact IDs as selectable contacts, not suspension
anchors. Cord guides, anchor placement, radius, rest length, material, pose,
and camera values remain `displayEstimate` unless a source establishes the
specific numeric fact.

Native solved routes belong in generated `assets/suspension.json`; authoring
inputs retain no hashes, settled heights or route caches. Complete canonical
pose coverage and source/authoring/model bindings are required before staging.

Captain Fingerfood DUAL uses independent front-entry leads. Its authoring
`mouthAxis: [0, 0, 1]` fixes the evidenced entry side in importer coordinates;
a collision-free path entering from the rear would still contradict the
threading evidence. See the
[DUAL source audit](source-audits/2026-09-29-remaining-cad/captain-fingerfood-dual/README.md).
Convert source points into the descriptor/importer basis before authoring them.

A source's total rope length and the renderer's branch `restLength` answer
different questions. For two equal exterior leads made from a published 1 m
total, a 0.5 m per-lead value is acceptable only as an explicitly documented
display estimate derived from the total. It must not be described as a measured
0.5 m lead. For a two-branch route, each branch's `restLength` follows that
branch's complete displayed route, not the product's undivided total.

A user may approve a shorter visual presentation without changing the retained
published physical length. Record that choice as a user-approved
`displayEstimate`, not a revised source fact. Shorten the invisible anchor
offset and the corresponding per-lead/per-branch rest length coherently;
halving `restLength` alone changes slack without moving the hanging geometry's
support point and can make the route unsolvable. For every canonical pose,
`restLength` must remain at least the required solved route length: endpoint
separation for a direct lead, the free span plus ordered contact route for a
routed paired lead, or the full fixed exterior passage route plus its free
spans for a routed branch. Re-run all-pose clearance and framing after any such
display adjustment.

Suspension is a deterministic transient layer above the validated USDZ. Keep
the anchor invisible, cord geometry non-pickable and absent from accessibility,
and board pose, solved cord, and camera framing committed atomically for a
selected position. Do not bake cord, hook, nail, stand, mounting environment,
cached geometry, or a raster fallback into the USDZ. Do not add a visible
attachment just to explain the presentation.

The Mini Bar has two connected U-shaped CAD channels, with one continuous
loop per end and an explicit winding at each mouth. The native solver measures
channel length and generates settled bearing routes for every canonical grip.
See [CAD cord authoring](HANGBOARD_CORD_AUTHORING.md) for this and the supported
independent-lead, exterior-wrap and groove-guided methods.

## Make an evidence-backed correction

1. Reproduce the failure with the exact board, presentation, and position.
   Record whether the model loaded and whether the app build contains the
   current renderer and metadata commits.
2. Validate the package and inspect its current source audit and retained
   evidence before editing. Validate a closed cord-audit manifest when one is
   supplied. If the source fact is unresolved, stop at evidence
   collection and human review.
3. Add a failing focused test or negative manifest mutation for the missing
   contract. Prove the failure is caused by missing/incorrect suspension data
   or runtime behavior rather than by the test fixture.
4. Prefer the smallest approved correction. When model geometry and node
   bindings are unchanged, edit authored suspension metadata and preserve the
   generated USDZ and descriptor bytes. Catalog packages retain native
   flat `Hangboards/<slug>.FCStd` sources; their `board.json` is generated from
   the FCStd and validated `assets/suspension.json` at build time. Edit
   `HangTenSuspensionAuthoring` with `Tools/HangboardCAD/set_cad_authoring.py`
   (which leaves every geometry member byte-identical), then run
   `rtk proxy bash scripts/build-board-assets.sh --package <slug>` to regenerate
   every pose. Never save solved heights or routes into CAD or edit the artifact
   as a source. The retained legacy manifest suspensions are described above.
   Inspect the generated
   result with `Tools/HangboardCAD/board_manifest.py --package <slug>`. Runtime changes belong in
   `BoardPackageStore`, `SuspendedBoardPresentation`, or `BoardModelView` only
   when a focused regression demonstrates a runtime defect.
5. Re-run the focused test, package/audit validation, relevant native tests,
   and current-source visual review. Retain hashes, commands, results, and
   screenshots in a workspace-owned path.

Package validation must fail closed. Invalid lengths, nonfinite values,
unknown/duplicate poses, missing node bindings, unsolved curves, collisions,
or a selectable/nearer cord enter the explicit unavailable state; they do not
fall back to another topology, straight line, alternate face, or raster image.

## Verification matrix

Use the smallest focused lane first, then the full lanes invalidated by the
change.

| Boundary | Required evidence |
| --- | --- |
| Source decision | Current per-board evidence supports the decision; when a closed audit is supplied, it accepts every discovered model package and agrees with independent `sourceFact`, evidence, and approval |
| Package/schema | Parser rejects unknown/duplicate members and invalid topology, poses, nodes, frames, finite/positive dimensions, and too-short rest lengths |
| Asset boundary | USDZ and descriptor paths and bytes are unchanged for metadata-only corrections; suspension artifact matches source hash, authoring payload, and model descriptors; staged USDZ bytes match descriptor SHA-256 |
| Solver/renderer | Relevant `SuspendedBoardPresentationTests`, `BoardModelTests`, and package-store tests pass for real packages and malformed fixtures |
| Geometry | Every canonical pose passes sampled length, self-intersection, board/tube clearance away from the attachment interface, and camera framing |
| Picking/accessibility | The active contact remains the nearest descriptor-bound triangle; cord groups cannot become a hit or accessibility element |
| Native visuals | Current-source app captures cover every pose in front, oblique, and active-contact states, plus clear/reappear, orbit/reset, and workout-driven selection |

From the checkout root, rebuild and validate the current package:

```sh
rtk proxy bash scripts/build-board-assets.sh --package <slug>
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk git diff --check
```

For a supplied closed source audit, also run
`rtk scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest <cord-audit.json>`.
Reproduce native routes using the [pinned environment and collider export](../Tools/HangboardCAD/README.md#focused-cord-reproduction)
and `solve_threaded_rope.py --check`. Run affected package/native tests and the
focused `SuspendedBoardPresentationTests`, `BoardModelTests` and
`BoardPackageStoreTests`; expand validation when the changed boundary affects
other consumers. See [package testing](../Tools/HangboardPackages/TESTING.md).
A convex-hull-only check cannot establish clearance at a real mouth.

## Current-source iOS review

Use `validate-hang-ten-ios` and the [isolated simulator guide](IOS_SIMULATOR_VALIDATION.md).
Build the current source into workspace-local DerivedData and target only the
recorded simulator UUID. A prebuilt app or CI artifact must include the renderer
and metadata changes under review. Bound stalled commands and clean up only
processes and resources created by this workspace. A blocked build is not visual
acceptance evidence.

For every canonical suspended pose, inspect the board/cord junction, free-leg
clearance, self-intersection, framing and active contact. Exercise ignored cord
picking, selection clear/reappear, orbit/reset and workout-driven selection.
If native board geometry changes, also present front/side/top previews beside
exports built from the prior committed source. Simulator captures establish app
integration; repeat device-specific appearance and delivery checks on hardware.

Keep raw reports, hashes and captures under an owner-prefixed workspace
`.context` path. Record external resource ownership immediately, keep cleanup
traps active and verify deletion of those exact resources before completion.
Retain reviewed physical-source decisions and necessary visual evidence in the
source audit. Report any missing build/test prerequisite precisely.
