# 3D hangboard suspension and Apple On-Demand Resources

This guide is the diagnosis, authoring, and verification reference for cords on
Hang Ten model-media boards. Use the repository skill
`audit-3d-hangboard-suspension` when a 3D board is missing an expected cord or
when an Apple offline/On-Demand Resources cache is suspected.

## The shipping boundary

A model presentation crosses two different delivery paths:

| Content | Source | Shipping path | Runtime role |
| --- | --- | --- | --- |
| Board identity, positions, `media.suspension`, and display configuration | `board.json` | Main app bundle | Parsed into `BoardModelMedia`; selects and solves transient cord geometry |
| Model descriptor and its expected `modelSHA256` | `assets/*.model.json` | Main app bundle | Validates model identity, bounds, nodes, attachments, and physical-contact bindings |
| Board mesh and embedded materials | `assets/*.usdz` | Apple On-Demand Resources (ODR) in production | Decoded by SceneKit after access and SHA-256 validation |

`scripts/stage-board-packages.py` copies each validated regular-file package
tree into the app resources while excluding only each model presentation's
`assetPath` (and a CAD package's `<slug>.FCStd` authoring source, which is never
bundled). It stages those excluded USDZ files for ODR separately. For a CAD
package it writes the `board.json` generated from the FCStd's
`HangTenBoardManifest` into the staged package, since none is committed.
Therefore `board.json` and the descriptor remain ordinary bundled metadata; the
cord is not part of the downloaded model asset. Android stages with the same
script (`--target android`), which keeps the USDZ inline instead of splitting it
out for ODR.

`BoardPackageStore` parses and validates bundled package metadata, registers an
ODR `BoardModelResource` for an on-demand USDZ, and passes the parsed suspension
through `BoardModelMedia`. `BoardModelView` acquires the production resource
with `NSBundleResourceRequest`; DEBUG Simulator builds may resolve the signed
packaged ODR file directly because the simulator installer does not register
the nested asset pack with the ODR service.

The model cache is an in-flight load coalescer keyed by board ID, presentation
ID, and descriptor `modelSHA256`; it is not a persistent scene cache.
`BoardModelResourceLease` retains successful ODR access through SceneKit decode
and scene use, then balances it with `endAccessingResources()` on deinit.
`BoardModelAsset` accepts only a regular file whose exact SHA-256 matches the
bundled descriptor before decoding it as an `SCNScene`.

The practical conclusion is firm: if the expected board mesh loads but a cord
does not render, invalidating or redownloading Apple's offline ODR asset cannot
repair it. Inspect the bundled `board.json`, selected position, parser result,
and transient suspension-renderer path. ODR is a plausible boundary only when
the model is unavailable, its resource URL cannot be resolved, its bytes do not
match the descriptor, or SceneKit cannot decode it.

## Diagnose by symptom

| Symptom | First boundary to inspect | Do not use as a shortcut |
| --- | --- | --- |
| Correct model loads, expected cord absent | Bundled `media.suspension`, selected `positionID`, parser dispatch, transient scene layer | ODR cache purge or USDZ replacement |
| Model is explicitly unavailable | ODR acquisition/debug packaged URL, resource lease, regular-file check, SHA-256, SceneKit decode | Raster fallback or a guessed model path |
| Wrong or stale mesh appears | Installed app/build provenance, ODR tag and descriptor hash, staging output | A screenshot from an unproven prebuilt app |
| Cord moves incorrectly for one contact/face | Position-to-pose mapping, attachment override, solved destination state | Independent animation or camera changes that hide the defect |
| Cord is selectable or blocks a contact | Native picking and scene-category configuration | Moving the cord visually without proving clearance |

A prebuilt app or CI artifact is valid visual evidence only when its commit is
at or after both the renderer implementation and the bundled metadata being
reviewed. A build that predates either boundary must not be presented as proof,
even if its USDZ hashes happen to match.

## Re-audit the current inventory

Discover model packages at execution time; never copy a historical package
count into a decision. The closed manifest is
`docs/source-audits/2026-09-13-model-hangboard-cord-audit.json`, with its human
review at `docs/source-audits/2026-09-13-model-hangboard-cord-audit.md` and
retained snapshots beneath `docs/source-audits/2026-09-13-model-cord-snapshots/`.
The validator requires exact equality between discovered model packages and
audit records.

Every record has these independent parts:

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
reason to reverse a later source-backed ruling. The current Baguette Evo record
is the important regression example: `yy.baguette-evo` deliberately has
`documentedSuspension`, a represented `twoBranchCord`, and retained
exact-revision manufacturer evidence. Its model media may also retain
orientation metadata; those fields are not mutually exclusive in the current
schema. Do not remove its suspension because an older orientation design said
otherwise.

## Select the narrowest truthful topology

| Type | Package meaning | Evidence and geometry boundary |
| --- | --- | --- |
| `singleCord` | One attachment and one branch to a shared invisible display anchor | Use only when one physical attachment is established. The attachment binds to an importer-visible body/attachment node, never a selectable contact node. |
| `pairedLeadCord` | Two independent exterior leads from two distinct attachment points to one invisible anchor | Represents visible leads without inventing a lead-to-lead or hidden interior route. Optional ordered `contactPointsInModel` may preserve an evidenced exterior over-lip route before the terminal attachment; per-pose attachment-point overrides must retain both lead IDs and remain distinct and in bounds. |
| `twoBranchCord` | Two branch routes through four uniquely identified passages arranged as two ordered pairs | Use directed entry/exit bore routes only when the complete through-route is evidenced. Never fabricate a hidden bore from a visible mouth. |

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
route between bore exits remain unchanged. Single cords and point-only
passages cannot use these overrides. Parsers validate the resolved route,
including full length and distinct adjacent points.

Captain pose-specific `attachmentPoints` delimit the visible cord at the
selected upper channel. They are clipped display endpoints, not evidence for
additional physical mouths or a hidden interior connection. Keep their ordered
over-lip routes clear of selectable lips and the white floor apertures.

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

## Make an evidence-backed correction

1. Reproduce the failure with the exact board, presentation, and position.
   Record whether the model loaded and whether the app build contains the
   current renderer and metadata commits.
2. Run the cord audit before editing. Inspect the current record and each
   retained snapshot. If the source fact is unresolved, stop at evidence
   collection and human review.
3. Add a failing focused test or negative manifest mutation for the missing
   contract. Prove the failure is caused by missing/incorrect suspension data
   or runtime behavior rather than by the test fixture.
4. Prefer the smallest approved correction. When model geometry and node
   bindings are unchanged, edit `board.json` suspension metadata only and
   preserve the USDZ and descriptor bytes. For a package with a native
   `<slug>.FCStd` source, there is no committed `board.json`; it is generated
   from the FCStd at build time. Change the suspension in the FCStd's
   `HangTenBoardManifest` with `Tools/HangboardCAD/set_board_manifest.py`
   (which leaves every geometry member byte-identical); inspect the result
   with `Tools/HangboardCAD/board_manifest.py --package <slug>`. Runtime changes belong in
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
| Source decision | Closed audit accepts every discovered model package; represented/excluded decisions agree with independent `sourceFact`, evidence, and approval |
| Package/schema | Parser rejects unknown/duplicate members and invalid topology, poses, nodes, frames, finite/positive dimensions, and too-short rest lengths |
| Asset boundary | USDZ and descriptor paths and bytes are unchanged for metadata-only corrections; staged USDZ bytes match source and descriptor SHA-256 |
| Solver/renderer | Relevant `SuspendedBoardPresentationTests`, `BoardModelTests`, and package-store tests pass for real packages and malformed fixtures |
| Geometry | Every canonical pose passes sampled length, self-intersection, board/tube clearance away from the attachment interface, and camera framing |
| Picking/accessibility | The active contact remains the nearest descriptor-bound triangle; cord groups cannot become a hit or accessibility element |
| Native visuals | Current-source app captures cover every pose in front, oblique, and active-contact states, plus clear/reappear, orbit/reset, and workout-driven selection |

Repository commands from the checkout root:

```sh
rtk proxy ruby Tools/HangboardModels/check_production_cord_clearance.rb
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh audit-cords --root Hangboards \
  --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_cord_audit.py -q
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests -q
rtk proxy env PYTHONPATH=Tools/HangboardModels \
  .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardModels/test_contact_model_descriptor.py \
  Tools/HangboardModels/test_contact_model_package.py \
  Tools/HangboardModels/test_import_contact_model_source.py \
  Tools/HangboardModels/test_verify_yy_baguette_evo.py -q
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_hard_cut_audit.py -q
rtk python3 -m compileall -q Tools/HangboardPackages/src
rtk git diff --check
```

The macOS clearance regression extracts the checked-out production model
types, solver, and verbatim `BoardModelView.hasClearance` gate and helpers. It
decodes every triangle from the four real, hash-checked USDZs and fails if any
of their 17 poses is rejected. It also checks that Captain visible terminals
stay in the selected upper channel and that each pose projects its anchor and
at least 10% of board width of every branch above the entire board silhouette
(with an eight-radius minimum). This is mesh/solver evidence; it does not
replace current-source iOS selection, picking, or screenshot review.

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

- the current closed audit truthfully covers every discovered model package;
- the chosen topology and every numeric estimate are evidence-traceable;
- USDZ/descriptor bytes and hashes remain unchanged unless model geometry was
  explicitly in scope and independently reviewed;
- focused and affected full test lanes pass, or each environmental block is
  stated precisely;
- current-source native screenshots cover every canonical pose and show the
  visible non-pickable cord without clearance or selection defects; and
- all exact workspace-owned external resources and temporary artifacts are
  removed and their cleanup verified.
