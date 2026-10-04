# 3D hangboard suspension and Apple On-Demand Resources

This guide is the diagnosis, authoring, and verification reference for cords on
Hang Ten model-media boards. Use the repository skill
`audit-3d-hangboard-suspension` when a 3D board is missing an expected cord or
when an Apple offline/On-Demand Resources cache is suspected.
For connected internal passages and mesh-derived exterior bearing, read
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

Current validated `sourceFact`, retained evidence, and audit outcome are the
decision authority. Older design documents are historical context, not a
reason to reverse a later source-backed ruling. Native `yy.baguette-evo` uses
source-backed `cadRoutedCord` from its CAD-contained
`HangTenSuspensionAuthoring`, compiled into source/descriptor-bound
`assets/suspension.json`, authored with `ropeSolver.method: "nativeRoutes"`,
alongside orientation metadata. Preserve that current contract; do not remove its suspension or
restore a historical topology because an older orientation design said
otherwise.

## Select the narrowest truthful topology

For a CAD board, preserve the evidenced connection graph and follow
[CAD cord authoring](HANGBOARD_CORD_AUTHORING.md). Connected internal mouth
pairs use the standard CAD passage void, measured channel length and
`twoBranchCord` (or `threadedLoopCord`) with `internalLoop`. Source-backed
independent visible leads, exterior wraps and unknown interior joins use
`cadRoutedCord` with authoring `ropeSolver.method: "nativeRoutes"`; do not
invent a hidden connection. Generate every canonical pose against the actual
native solid through the pinned build's `compile_suspension.py` and native
solvers, reproduce the generated artifact with `solve_threaded_rope.py --check`,
and retain native-solid clearance, length, tube and topology checks. The table
below governs older non-CAD packages; migrate their cords to the native method
matching the evidence when they move to CAD. Do not retain hand-authored routes
or `pairedLeadCord` on a CAD board; extend the solver with evidence and tests
when the supported native methods do not fit. Captain Fingerfood POCKET's
existing `HangTenBoardManifest` suspension remains the intentional legacy
exception pending a separate evidence-backed cord revision. Consolidation
preserves that existing CAD-contained representation without changing topology.

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

Canonical poses may provide `cordContactPoints`: complete, nonempty ordered
exterior routes keyed by both paired-lead IDs or all four directed-passage IDs.
For a branch, the first passage's override runs from the anchor toward the
entry mouth, and the second runs from its entry mouth back toward the anchor.
These override the branch's entry/exit contacts only; the bore and the fixed
route between bore exits remain unchanged. Connected `internalLoop` point
mouths may hold generated settled-route caches; other point-only passages
and single cords cannot use these overrides. Parsers validate the resolved route,
including full length and distinct adjacent points.

Older non-CAD Captain pose-specific `attachmentPoints` delimit the visible
cord at the selected upper channel. They are clipped display endpoints, not
evidence for additional physical mouths or a hidden interior connection.
Native revisions instead follow their current CAD source audit.

For native Captain Fingerfood DUAL, the retained maker title photo shows both
leads descending into the front cavity's two floor openings. Its existing CAD
bores and front mouth centers are unchanged by the 2026-09-30 review correction.
Each native lead declares authoring `mouthAxis: [0, 0, 1]` in the importer basis
to fix the front entry side before native route generation. A path that reaches
the front terminal through the rear mouth may pass collision checks while
contradicting this observed threading. The two leads remain independent visible
strands; no hidden rear connection is established. See the
[DUAL source audit](source-audits/2026-09-29-remaining-cad/captain-fingerfood-dual/README.md).

Convert retained source coordinates into the descriptor/importer basis before
using them as model points. Baguette Evo's retained Blender markers are Z-up,
front -Y; the imported model is Y-up, front +Z, so the correct mapping is
`(x, y, z) → (x, z, -y)`. Its four evidenced bores therefore run along model Z.
The Baguette `paired-12-8-6` and `rounded-tray` cameras use a 30° oblique
display estimate: looking straight along the hanging spans hid the cord behind
the board. The oblique views keep the selected face and a visible hanging V.

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

For exterior point-passage branches, `meshWrap.clearance` selects the shared
mesh-driven route solver. The Mini Bar uses `internalLoop` instead: two
connected U-shaped channels in its FCStd, each with two mouth points in
`HangTenSuspensionAuthoring`. The user confirmed one continuous loop per end, including
the visible lower curve in Lattice's end photo. `windingByPassageID` records
which side of the ovoid each lead follows. This one-time threading choice is
necessary because mouth and anchor coordinates alone admit two exterior
paths. The CAD-section solver computes settled bearing points for every grip
pose from the native solid and caches them in generated `assets/suspension.json`; the renderer
uses that cache as transient geometry. No cord is baked into the USDZ. Mouth
positions, channel and cord diameters, anchor offset,
and clearance are labeled display estimates. CAD authoring retains topology,
dimensions, solver settings, evidence, pose rotations/cameras, and optional
`offsetXZ: [x, z]`; it contains no hashes, settled heights, or solved routes.
The generated artifact's source hash, model hashes, and authoring payload must
match the current source and descriptors; package validation checks those bindings.

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
   as a source. POCKET's pre-existing manifest suspension is the legacy exception
   described above. Inspect the generated
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

Repository commands from the checkout root:

```sh
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests -q
rtk proxy env PYTHONPATH=Tools/HangboardModels \
  .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardModels -q
rtk python3 -m compileall -q Tools/HangboardPackages/src
rtk git diff --check
```

When an explicit source-audit document is available, additionally run
`rtk scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest
<cord-audit.json>`. Use the native source and rope solver checks in the
[CAD cord guide](HANGBOARD_CORD_AUTHORING.md) for connected or independently
routed CAD suspension; the retired Blender board tools are not a validation lane.

Use the native solid-intersection and all-pose checks described in
[CAD cord authoring](HANGBOARD_CORD_AUTHORING.md), alongside current package
and RealityKit iOS tests. The obsolete SceneKit clearance helpers were retired.
A convex-hull-only clearance check cannot establish that the mouth transition
avoids the wooden solid.

Also parse each edited JSON document directly and run the focused XCTest
selectors for `SuspendedBoardPresentationTests`, `BoardModelTests`, and
`BoardPackageStoreTests`. If Python `pytest`, Simulator runtimes, or SwiftPM
dependencies are unavailable, report the exact missing prerequisite; passing
CLI validation does not become a substitute for a blocked test lane.

`git diff --check` can report whitespace inside a deliberately byte-preserved
retained HTML snapshot. Inspect the exact path and diff before deciding whether
it is a source artifact rather than authored whitespace; never rewrite retained
evidence bytes merely to silence the check.

## Current-source iOS review and Xcode deadlocks

Use `validate-hang-ten-ios` and read `docs/IOS_SIMULATOR_VALIDATION.md` plus
`docs/IOS_RUNTIME_SERVICES.md` completely. Create the exact isolated Simulator
name `Hang Ten Paseo <workspace_name> Review`, register its explicit UUID in
the pending and owned manifests before use, target only that UUID, build into
workspace `.context/DerivedData`, and keep cleanup traps active across success,
failure, timeout, and interruption.

Treat `xcodebuild` progress as bounded. A host can deadlock before compilation
when `SWBBuildService` stalls while probing the compiler with a command shaped
like `clang -v -E -dM -isysroot … -x c -c /dev/null`. If build output and
process state show that same probe making no progress:

1. Record the exact build command, destination UUID, last build-service phase,
   and bounded timeout.
2. Run the exact compiler probe once outside the build service as a diagnostic.
   If it succeeds, that distinguishes a build-service/host failure from source
   compilation; it does not make the app build valid.
3. Stop only exact processes and resources created by this workspace. Never
   kill shared Xcode, CoreSimulator, SwiftPM, or other agents' processes and do
   not delete global DerivedData.
4. Retry at most through one controlled current-source path or use a CI
   artifact whose commit provenance includes the current renderer and bundled
   metadata. A stale local/prebuilt app is not acceptable visual evidence.
5. If current-source native review remains blocked, report it as blocked and
   retain no misleading screenshots.

For every canonical suspended pose, inspect the board/cord junction, free-leg
clearance, self-intersection, camera framing, active contact, and ignored cord
picking. Exercise selection clear/reappear, camera orbit followed by canonical
reset, and workout-driven position resolution. Simulator captures establish
app integration, not guaranteed physical-device PBR parity.

## Cleanup and completion

Generated reports, hashes, and captures belong under an owner-prefixed
workspace `.context` path. Record every exact external resource immediately.
Cleanup must archive/delete only the owned Simulator UUID, remove the exact
workspace DerivedData/result bundles/capture staging created by the run, and
verify those resources are absent. Leave shared, standard, and unknown
resources alone.

Completion requires all of the following:

- retained exact-revision source evidence supports the current suspension
  decisions, and any supplied closed audit covers every discovered model package;
- the chosen topology and every numeric estimate are evidence-traceable;
- USDZ/descriptor bytes and hashes remain unchanged unless model geometry was
  explicitly in scope and independently reviewed;
- focused and affected full test lanes pass, or each environmental block is
  stated precisely;
- current-source native screenshots cover every canonical pose and show the
  visible non-pickable cord without clearance or selection defects; and
- all exact workspace-owned external resources and temporary artifacts are
  removed and their cleanup verified.
