---
name: migrate-hangboard-to-3d
description: Use when migrating an existing Hang Ten hangboard to an interactive 3D display model, or refining its geometry, exported materials, picking, or app integration.
---

# Migrate a hangboard to 3D

Deliver a faithful, 3D-only display model with selectable physical contacts. Migration replaces the target board's raster presentation and canonical 2D hold geometry; the 3D model and its package metadata become the sole source of truth for rendering, highlighting, and hit-testing. Preserve logical hold IDs, saved identities, and source-backed metadata. This is not manufacturing CAD or a source for training prescriptions.

## Establish the contract once

Identify the exact board revision and read its existing package and source audit. Reuse verified manufacturer references; research only missing evidence. Record sourced dimensions separately from estimated positions, thickness, radii, and sections. Derive physical contact IDs from the package: Compact II's 19 contacts are an example, not a universal count. Remove the migrated target's raster asset and canonical 2D hold paths from product resources; retain its stable IDs and source-backed metadata in the 3D-only package representation. When an already-migrated board that still carries legacy raster assets or paths is included in scope, bring it to this same contract. Omit all screw holes, mounting holes, and mounting hardware from every hangboard display model. Document each omission as a deliberate display simplification; never imply that the physical product lacks those features.

Read relevant sections of the [working example](../../../Tools/HangboardModels/README.md), then inspect only the generator functions needed. Treat any dual 2D/3D structure in an older example as legacy, not as a requirement to preserve raster assets or paths. Follow `add-hangboard` for source-backed package metadata, while applying this skill's 3D-only migration contract.

In the retained evidence packet, each source-backed logical inventory entry cites an exact retained source snapshot, and retained snapshot paths are unique across manufacturer and commerce tiers. Sourced claims carry stable claim identities and retained-source links. When one claim identity has both manufacturer and commerce evidence, record the conflict and a non-empty ruling; commerce-only gap evidence remains valid when clearly tiered and linked.

Visually verify each snapshot's depicted face before using its filename or label to map logical holds. If a filename or label conflicts with the visible inventory, record the correction and keep it confined to the evidence mapping; never pass that correction into geometry authoring.

Before any Astra geometry task, pass a multi-angle visual evidence gate for every board. The retained packet must contain at least two actual visual source snapshots for the exact revision, each with its SHA-256 hash, source URL/publisher, and a view label, and the views must be materially distinct. Use a manufacturer-published front plus an oblique, side, back, or profile view when available; manufacturer evidence is first-tier and must be sought first. An authorized retailer or distributor may fill a documented missing angle only when clearly tiered as commerce evidence. Duplicate crops or variants, diagrams without profile information, search thumbnails, generated renders, legacy raster assets or paths, and ambiguous board revisions do not satisfy the two-view count. Record what each view supports and does not support. A human must approve the exact multi-angle set before Astra; lower-cost workers gather it, and Astra receives every approved image. If no trustworthy second angle exists, stop at this gate and ask the human rather than hiding the uncertainty.

General web or image searches may be used for discovery and to locate candidate views of the exact revision, but search results and thumbnails cannot satisfy this gate. Before retaining a candidate, verify its publisher and source tier; retain only manufacturer evidence or documented commerce-gap evidence under the rules above.

Discover the live package inventory at execution time rather than trusting a stale plan or expected count. A bulk converter must be deterministic and idempotent: preserve every recognized field or reject the document, and reject duplicate or unknown legacy members instead of silently dropping them.

Before and after schema migration, run a type- and order-sensitive semantic audit over every discovered package. Compare logical metadata and order, presentation ownership and derivation, every geometry piece/member/path command and scalar kind/value, and asset inventory; then run converter `--check`, exact schema-version counts, full package validation, and both language suites.

## Separate logical data from model geometry

Keep physical identity, source-backed logical holds, equipment, and positions in `board.json`. Use explicitly tagged raster/model presentations so unrelated raster boards can coexist with migrated boards. A package containing model media is model-only: it must declare no raster presentation or PNG, whether original or derived; presentation derivation is supported only between raster presentations. Exact declared-versus-actual asset equality complements but does not replace this package-level media-isolation rule. Each migrated package owns a required USDZ and an explicit mesh-to-logical-hold-ID binding; multiple disconnected mesh pieces may share one ID. The mesh is the sole geometry for rendering, highlighting, and picking: do not retain parallel raster paths or hand-edited spatial bounds.

## Use the extracted verification and review boundaries

For the shipped Beastmaker 1000 and Compact II model packages, route the
shared actual-export checks through
`Tools/HangboardModels/model_verification.py`:
`ModelVerificationConfig` describes the closed package contract and
`verify_model_package(package, config, render=False)` performs the cheap
filesystem, ordered-inventory, and descriptor-hash checks before importing
Blender, then verifies imported materials and geometry. `verify_beastmaker_1000.py` and
`verify_wood_grips_compact_ii.py` remain compatibility CLI adapters; use
`beastmaker_config()` and `compact_ii_config()` for board-specific
configuration and probes. Retain their existing report fields and
`--skip-renders` behavior. Do not route Flash through this shared
configuration: `verify_tension_flash_board.py` remains a separate baseline
verifier until Flash's independently approved migration and two-branch gate
is complete.

Freeze behavior before an extraction with
`model_characterization.capture_model_baseline(package, board_json)` and
compare it using `assert_baseline_matches(actual, expected)`. The
characterization includes the recursively discovered regular-file inventory,
exact model/descriptor hashes, descriptor data, and ordered logical IDs; it is
a preservation check, not a geometry source. Keep staging as the existing
recursive regular-file copy and prove source-to-stage byte parity with its
staging characterization rather than adding a second model-resource path.

For a reviewed model package, load the closed bookkeeping document with
`migration_manifest.load_migration_manifest(path)`. It rejects unknown,
duplicate, explicit-null, escaping-path, and geometry/bounds members and
requires the declared model assets, logical order, omissions, verification
configuration, review views, and artifact hashes. After package verification,
`render_model_gallery.render_model_gallery(package, manifest, output)` may
produce fixed review artifacts only in the canonical workspace `.context`,
under an owner-prefixed output directory. The gallery consumes the verified
USDZ, never source images or a source blend, and its owned output must be
cleaned after review.

For portable single-cord presentations, keep pure solving in
`SuspensionProfileSolver.solveSingle(pose:profile:bounds:) throws` and call it
through the existing `SuspendedBoardPresentation` facade. The solver's
`SolvedSuspension`/`SolvedCordBranch` results and failure mapping are part of
the compatibility contract; retain the invisible anchor, transient
non-pickable cord layer, finite canonical poses, and explicit unavailable
state. The compatibility API may already expose a two-branch solve overload, but it is not
a supported extraction route. Do not route or adopt Flash through it, or change
Flash's verifier, generator, package, geometry, or presentation behavior, until
Flash passes its separate evidence, geometry, package, native-picking, and
human-review gate.

## Suspended portable presentations

For a portable-suspension parser/runtime, reject a migration unless all
of the following are decidable from package data:

- exactly one model USDZ and descriptor;
- an optional, explicitly tagged `singleCord` suspension declaration;
- one physical attachment point bound to an importer-visible descriptor node;
- exactly one finite canonical pose for every supported position, and no pose for an unknown position;
- a display-only invisible anchor plus positive cord length and radius; and
- no baked cord/anchor mesh, second face model, raster fallback, hand-authored hold bounds, or hold-node attachment shortcut.

When `suspension` is present on model media, author `attachment.nodeID` against
the hash-bound, importer-visible model descriptor and record its model-frame
`pointInModel`; the attachment must not be a logical hold node. Record the
invisible-anchor display estimate, cord rest length, radius, and material
estimates separately from source-backed physical facts. Author normalized,
finite canonical pose transforms keyed by the existing `positionID` values.
Logical holds remain metadata-only, and positions select faces/configurations
and their canonical poses rather than creating duplicate contacts or copying
model geometry. Unsupported cord dimensions or knot details remain explicitly
labeled estimates.

The retained evidence packet must record the exact board revision, every usable
face/position, attachment evidence, a position-to-logical-hold mapping with
supporting evidence, two approved materially distinct visual snapshots (adding
an attachment-region view when available), and every deliberate display
simplification, including the invisible anchor and omitted mounting
environment. Preserve the current multi-angle human approval gate before
Astra; no geometry-generation pass proceeds until that exact approved set is
retained.

Raster original presentations must be nonempty and form an exact, single-owner partition of the logical hold inventory. Derived raster presentations may reference only originals, and their raw geometry must equal the declared source exactly, including ordering and scalar kinds/values. Reject redundant empty media, duplicate or missing owners, geometry drift, and derived-to-derived chains.

Logical holds store metadata only. Never add empty or zero sentinel geometry, cached frames, or presentation IDs for compatibility: typed presentation media solely owns hold membership, geometry, and resolved frames, and consumers resolve through the selected presentation. During an intentionally temporary v1/v2 transition, keep v1 spatial fields in a loader-private adapter and normalize them immediately into typed raster media. Remove silent compatibility overloads so compiler failures expose callers that still need explicit typed-media migration; remove the adapter when catalog conversion completes.

In closed schemas, an optional member means omission only: when present, decode its concrete type and reject explicit JSON `null` consistently in every language.

Gate raster image decoding strictly on the raster discriminator. Model assets receive regular-file, descriptor, exact-byte hash, and inventory validation; never send model bytes through ImageIO or a raster fallback. Native descriptor validation must match the compiler's nine-decimal ties-to-even behavior for centers and derived extents. For finite values whose ULP is wider than the rounding quantum, avoid lossy decimal scale/unscale; reject non-finite derived arithmetic.

When canonical JSON member order is part of the descriptor contract, inspect an order-preserving raw representation before keyed decoding. The scanner must accept valid JSON whitespace and escaped strings and enforce an explicit recursion/nesting bound; keyed-container iteration cannot recover source order.

Cross-language raw JSON equality preserves object/list order and scalar kind. Keep integers arbitrary and exact with Python-equivalent zero normalization; compare finite floating tokens by decoded binary64 value, including equivalent precision, exponent, and signed-zero forms, while keeping integer and floating kinds distinct.

Malformed cross-parser contract cases use one declarative shared fixture matrix: common base board/descriptor documents and model bytes, ordered mutations, and language-specific expected rejection categories. Have every parser suite consume that matrix and retain focused single-rule tests; do not independently author equivalent malformed documents in each language.

Derive spatial centers and bounds used by workout matching from the mesh in a defined board coordinate frame. A build-generated index bound to the model hash may provide these values without eagerly decoding every USDZ during catalog loading. Keep camera configuration separate from physical metadata, and never silently promote estimated model geometry to physical dimensions.

Descriptor tooling exposes generated spatial values as read-only outputs, with no public construction path for hand-authored bounds or centers. Normalize from raw mesh extrema before rounding. Reject non-finite source coordinates and any non-finite derived span, normalized coordinate, center, or rounded value. Serialize stable, sorted output using one declared rounding precision; descriptor v1 uses nine decimal places.

Carry model media through demonstrated package validation and staging. Remote GitHub model-package sync is currently deferred/unsupported unless a future task separately implements and verifies it; do not describe it as shipped. Inspect existing staging before changing it; if it already recursively copies the parser-approved regular-file package tree, leave production staging unchanged and add a characterization fixture/test. For a v2 model fixture, prove staged USDZ and generated descriptor bytes equal their source bytes and staged assets exactly equal the parser-declared inventory. Staging must not synthesize, rename, replace, or app-side substitute model resources. Record and clean generated staging directories/resources. Workbench must explicitly disable model geometry editing it does not support; do not reconstruct raster geometry to enable it. A missing or malformed USDZ is a package validation/build defect, with an explicit unavailable state if encountered at runtime.

## Build shape before finish

Use Astra (`gpt-6-astra`) only for authoritative final 3D geometry generation, authored geometry refinement, difficult geometry judgment, and physical-shape corrections. A controller using another model must hand those tasks to Astra with the visual evidence and the defect to correct; only Astra owns the final geometry-generation pass. If Astra is unavailable, flag that limitation instead of silently substituting another model. Honor explicit user requests for another model or for comparison candidates.

Route model cost by task complexity and verification results, never by preference. Luna is the default for routine bounded work, including primary-source research synthesis, suspended-presentation evidence collection and structuring, package/schema work, attachment and pose metadata, catenary math, deterministic validation, tests, documentation, renderer integration, routine integration, and review. Escalate to Terra only after a bounded Luna attempt exposes intricate non-geometry schema, tooling, renderer, or cross-platform integration work, or fails verification with an unresolved issue that is no longer routine. Before invoking Astra, lower-cost workers must gather and structure the primary-source manufacturer evidence (and clearly tiered retailer gap evidence where authorized) into the retained evidence packet, including the suspended presentation evidence gate. Astra is reserved exclusively for final physical board shape and fidelity judgment or corrections after that approved evidence gate; it does not own suspension evidence, cord estimates or catenary math, schema, tooling, package conversion, renderer integration, validation, or tests. Lower-cost workers may also handle schemas and data models, reusable exporter and validator tooling, deterministic export and render execution, packaging, demonstrated staging, app integration, and visual or picking checks. Remote GitHub model sync remains deferred/unsupported; generic unavailable/read-only Workbench behavior remains the supported model-editor boundary. No geometry worker may alter a board face, cord estimate, camera, or attachment solely to mask a validation failure: route geometry or fidelity defects back to Astra, while keeping tooling, schema, material-export, suspension, and integration defects with lower-cost workers. Hand off stable hold IDs, the coordinate frame, sourced-versus-estimated evidence, tagged editable geometry, and validation expectations. Inventory checks do not prove fidelity; retain human visual review.

Directly author analytic silhouettes, sections, and recesses from visually reviewed evidence; do not trace or segment pixels. Author symmetric geometry once where the product is symmetric. Give every physical contact its canonical identity, preserving disconnected pieces when necessary.

Do not promote a per-contact or sloper depth callout to overall body/display thickness; when body depth is unknown, keep it explicitly as an authored estimate. For recesses or pockets near the body silhouette or a stepped transition, validate complete physical wood ligaments both around exterior-adjacent recesses and between neighboring pockets across the full hold inventory, using authored geometry and actual-export probes or rays rather than a camera mask. Route geometry or fidelity failures to Astra for correction; lower-cost workers verify them and must not hide them with camera, lighting, or visual-only adjustments. Keep these rules shape-based and do not overfit board-specific numeric values.

Mirrored coordinates do not guarantee mirrored rendered surfaces for nonplanar quads. Triangulate corresponding surfaces deterministically with reflected diagonals, or otherwise verify the mirrored actual surfaces and rays in the export.

Model real mouth/back fillets, jug rolls, and continuous curves. A global bevel and smooth normals cannot repair blocky geometry. Inspect inexpensive front and oblique clay views, including a close pocket section, before expensive texture baking and galleries. Then use an original material appropriate to the product and enough tessellation to preserve reviewed curvature at mobile viewing sizes. Match material fidelity effort to the user's brief; generic original wood is acceptable when a species match is not required. Shipped wood display models use one committed canonical light-neutral material source shared by every exporter; each USDZ embeds the exact same source bytes so it remains self-contained offline. A canonical PNG color texture must also be self-contained at the color-management boundary: embed explicit standard-sRGB transfer and chromaticity metadata in the source and require the same metadata in the exact embedded USDZ bytes. USD material color-space tags alone do not prove that an app-renderer bridge will decode an unprofiled PNG consistently. Changing that source requires the deterministic rebuild and actual-export verification of every discovered shipped wood model; do not substitute a runtime override.

Timebox cross-renderer material matching to one evidence-driven diagnosis and one controlled correction. Before declaring an embedded texture missing, directly prove or disprove its actual-export material assignment, image payload and dimensions, UV connection, and rendered sampling; a pale or low-contrast result is not evidence of a disconnected texture. If parity remains unresolved and the human does not require texture fidelity, record their approval of one shared renderer-neutral fallback, such as matte warm white, author it once in the canonical exporter source, rebuild every shipped wood model, and stop texture tuning.

When independent comparisons are requested, give candidates identical evidence and briefs, isolate their code and artifacts, and do not share candidate work between them. Compare matched cameras and lights, inspect front, oblique, clay, and detail views before selecting, and record render-engine differences that affect comparison. Complete the requested draft comparison before production integration; the number and identity of candidates belong to the user's request, not this workflow.

## Prove the actual export

Reuse the [export verifier](../../../Tools/HangboardModels/verify_wood_grips_compact_ii.py), adapting board-specific expectations. Reimport actual exports in isolation with source materials/images removed; check dimensions, inventory, textures, triangle count, and visual continuity. Package validation or the build must require the model asset and reject missing, malformed, materialless, or wrong-inventory exports as defects.

Run the documented Blender entrypoint without test-harness import-path injection to prove it bootstraps its own imports. Imported material images must resolve to usable loaded data with positive dimensions; a non-null image object alone is insufficient.

Blender 5.2 may SIGSEGV while probing Metal capabilities in a managed Paseo sandbox, before Python, the scene, or assets load; do not attribute that boundary failure to geometry, materials, or the render engine, or pile on flags. Confirm it with exactly one minimal fresh-config, no-scene/no-file sandboxed `--background --factory-startup --python-expr` repro and, when authorized, one identical narrowly escalated host-context comparison. If the sandbox fails before the marker and host context succeeds, run the required Blender export/render only with narrow unsandboxed approval, using workspace-owned config/cache/temp/output, cleanup traps, and exact cleanup verification; do not restart or kill shared services. Checked-in Blender Python entrypoints must bootstrap sibling import paths from their own `__file__`, without relying on caller cwd, `PYTHONPATH`, or test injection.

USD importers may rename nodes. Carry stable source-piece correspondence on temporary export copies through export/import, then verify every body/hold piece's exact role and logical binding. Descriptor node IDs remain the actual importer-visible IDs. Counts and union bounds cannot prove correspondence when pieces share bounds. Never change source geometry, names, materials, or topology to pass validation.

Explicitly triangulate Boolean cap n-gons for USDZ export without changing editable geometry. Blender roundtrips alone missed SceneKit's untextured body and faces occluding pockets. Inspect the bundled asset natively: body and every contact need materials; nearest triangle hits must resolve to the expected IDs. Handle normalized USD names and parent nodes. Orthographic tests use parallel rays; CPU-only SceneKit tests need `SCNTransaction.flush()` before picking. For load-bearing native picking proof, construct each head-on SceneKit segment explicitly front-to-back in the mapped board frame: compute spans as positive `max - min`, derive the extension from that span, and assert the start is beyond the front face and the end beyond the back face before hit-testing. Use actual triangle intersections (`SCNHitTestOption.boundingBoxOnly` false or the verified default), flush transactions, and request closest-hit mode. A reversed segment may legitimately hit unbound body geometry first; diagnose that as ray direction, not occlusion. Retain the exact diagnostic script, commands/options, and results whenever native proof is load-bearing. Keep the expected nearest triangle's hold ID and the body probe nil as assertions.

## Integrate through the existing bridge

Inspect [BoardModelView](../../../HangTen/Views/BoardModelView.swift), package loading, and [regressions](../../../HangTenTests/BoardModelTests.swift). Extend identity, resource, and cache routing deliberately rather than copying a renderer or assuming a registry exists. Gate models to the exact supported revision and presentation. Do not retain or recreate a raster fallback for edited, inverted, unsupported, missing, or invalid states. Validation should make asset failure unreachable in a shipped package; if it escapes at runtime, fail closed to an explicit unavailable/error state.

Keep asynchronous cached loading, independent cloned materials, scene/camera rebinding on identity changes, stable accessibility elements, and on-demand rendering. Use head-on orthographic app framing with lighting that reveals recess depth. Match preview/rest and active highlight semantics; restore wood when cleared.

For a model satisfying the `Suspended portable presentations` contract,
integrate the
suspension presentation as one deterministic transient layer above the
validated USDZ. Transform the descriptor's local attachment point with the
selected canonical board pose, keep the anchor fixed and invisible, and solve
a uniform-cord catenary in the gravity plane whenever slack exists. Use a
straight segment only when rest length equals endpoint separation within the
declared numerical tolerance. The curve must be continuous at both endpoints,
sampled with finite values and fixed sample/material parameters, and remain
non-pickable and absent from the accessibility tree. Validate sampled-curve
length and self-intersection, and verify cord-tube clearance of at least the
cord radius plus declared clearance from the board mesh/rays away from the
approved attachment interface. Also verify camera-space framing of the active
hold, attachment, and visible cord segment. Do not add a visible nail, hook, anchor,
stand, ceiling, or surrounding mounting environment.

The following are required failure outcomes for validators and
`BoardModelView`: rest length shorter than anchor-to-attachment separation;
nonfinite or nonpositive cord length/radius or other cord parameters;
nonfinite, nonunit, or otherwise invalid pose transforms; a missing
attachment node; an unsolved or nonfinite curve; cord collision with the board
away from the attachment; and the cord becoming a selectable or nearer pick.
Each case must enter the current explicit model-unavailable/error state. None
may fall back to a straight line, another orientation model, raster rendering,
or a visible anchor/stand-in.

Selecting a hold or resolving a workout position must restore that position's
canonical board pose, destination-solved cord, and canonical camera framing
atomically in one action-free transaction. Build the deterministic cord before
committing the destination state; never independently animate or interpolate
cord samples away from the board pose. Manual gestures may change camera
azimuth, elevation, and allowed zoom only; they must never independently
rotate the suspended board or anchor. Verify camera orbit separately from
interactive detail picking. On the first migration, review selection snap,
orbit, reset after orbit, every supported position, cord/board continuity,
clear-and-reappear highlighting, workout-driven positions, and the explicit
unavailable state.

Derive a front-above key from the camera position without algebraically cancelling its camera-depth component. After `SCNTransaction.flush()`, verify the directional light's presentation-space forward vector points substantially along the declared camera view direction. Log the actual imported `SCNMaterial.lightingModel` when comparing renderers. SceneKit's physically based model requires Metal and can fall back to Blinn where Metal is unavailable, including affected Simulator configurations; treat Simulator captures as app-integration evidence, not guaranteed physical-device PBR parity.

After a canonical texture or exported material changes, validate its actual appearance through the app renderer as a separate boundary check; a Blender reimport/render establishes only Blender-side behavior. Compare controlled app and Blender captures before diagnosing any remaining mismatch as albedo or lighting, and do not make a second visual correction while app-renderer validation is pending. For albedo correction, hold camera, lighting, geometry, and material settings fixed; capture at least two controlled source-albedo samples through the actual app renderer, compare matched board-region pixels, solve the observed response toward a declared exposed-face target, and revalidate the chosen source in the app. Do not tune from Blender's color-managed appearance alone.

For a display-only 3D model (`onHoldTap == nil`, or the equivalent non-interactive configuration) embedded in an enclosing tappable SwiftUI card or plain `Button`, disabling model hit testing alone does not establish the parent’s tappable shape. Give the enclosing label/content an explicit hit shape covering the rendered model, and physically verify that a tap on the model surface triggers the parent. Keep detail-screen interactive model picking unchanged and verify it separately; nested overlay controls, such as favorite buttons, retain priority and receive a focused interaction check.

## Verify, retain, stop

Copy the reviewed asset into app resources and compare SHA-256 hashes. Verify the migrated package no longer ships or references the target's raster presentation or canonical 2D hold paths. On the first migration, use `validate-hang-ten-ios` to inspect normal/highlighted portrait and landscape views, physically tap every hold, and check preview, active, clearing, reappearance, and the explicit unavailable/error state. Tests complement visual review.

For every canonical suspended pose, retain front, oblique, and active-hold
captures. Retain native-picking proof that the active board contact is the
nearest descriptor-bound triangle mesh while the cord is ignored and cannot
become a nearer hit. On the first migration, the iOS review must cover
selection snap, camera orbit, reset after orbit, every position, board/cord
continuity, clear-and-reappear highlighting, workout-driven positions, and the
explicit unavailable state. Camera-orbit verification is a separate check
from interactive detail picking; passing one does not establish the other.

Native XCTest during migration follows `validate-hang-ten-ios`: create and record an exact owned UUID before use; keep cleanup protection alive across RED/GREEN and compilation failures; record and clean failed preliminary devices; use bounded polling and explicit xcresult summaries; and remove the simulator, workspace `DerivedData`, and result bundles before handoff.

Use the exact plan- and skill-prescribed simulator name (`Hang Ten Paseo <workspace_name> Review`). An ownership prefix, task-specific suffix, booted state, matching runtime, or apparent equivalence does not satisfy that identity contract. Record the exact name and UUID before the first XCTest command and use that UUID throughout.

Keep source/export hashes, evidence mappings, screenshots, and results under workspace-owned output; clean owned resources. Completion means reviewed fidelity, complete selectable inventory, valid native materials/picking, matching bundle hash, and passing relevant checks.

Batch independent reads with bounded output. Reuse evidence and scripts; delegate repository-required implementation tasks with file paths and a narrow contract instead of full histories. After a pass, rerun only checks invalidated by changes or failures. Use verifier format selection/skip-render options for unaffected visuals; regenerate galleries when partitions change or requested. Avoid repeated broad research, full suites, and all-hold renders for small lighting or camera edits.
