# Agent instructions

## Merging

When the user asks to merge, substantively address every outstanding code
review comment and resolve it only after the requested change is complete. Do
not dismiss or resolve comments merely to allow the merge.

## Resource lifecycle

Put generated output under `.context` or another explicitly workspace-owned
path. Derive the owner from `${PASEO_WORKTREE_PATH:-$PWD}`'s final path
component and include it in every external resource name. Record that ownership
immediately.
Install an exit trap that shuts down and
deletes each exact resource owned by this workspace, and verify deletion
before reporting completion. Leave shared, standard, and unknown resources
alone. The archive hook is a failsafe, not permission to skip an agent's own
cleanup.

Keep working plans, investigation diaries, command output, and cleanup receipts
in `.context`. Commit current reusable guidance and source mappings that justify
authored product or training facts. Update an existing guide or source mapping
when it covers the change; keep completed execution history in Git and CI.

## Training-plan Fidelity

All plan instructions, grip and finger cues, and accessory or instruction-box
text must be traceable to a specific real training-plan source. Faithful
adaptations are allowed only when the source fact is identifiable and the
adaptation is explicitly labeled. Never invent exercise names, counts,
durations, grip prescriptions, accessory text, or coaching claims and present
them as sourced. For any new or changed routine content, document the source
URLs and audit mappings used to justify each field. Omit unsupported fields or
UI text rather than filling gaps from board metadata or model assumptions.

## Hangboard geometry authoring

Author hangboard geometry directly from primary manufacturer evidence, following
the Trango Rock Prodigy Pivot package as the structural and path-style
precedent. Catalog board geometry and metadata live in the retained native
FreeCAD source. Deliberately author and review its contact regions; prefer exact
left/right mirroring when the product is actually symmetric. For supported
raster packages, deliberately draw and review every canonical hold path in
`board.json`.

The apps only read bundled packages; there is no in-app board editor. When
the checked-out schema supports shape constraints, author an operator-selected
constraint directly in `board.json` for holds that are genuinely circles,
ovals, pills, rounded rectangles, or rectangles. Freeform paths remain valid
for irregular holds. A constraint is editing metadata only: the saved path
remains the sole rendering, highlighting, and hit-testing source of truth.
Never infer a constraint from pixels.

A catalog board retains one flat native source, `Hangboards/<slug>.FCStd`.
Its `HangTenBoardManifest` generates `board.json` at build time; the file is
never committed and an on-disk copy is rejected. Change board metadata with
`Tools/HangboardCAD/set_board_manifest.py`. The document-level
`App::PropertyString` properties `HangTenSuspensionAuthoring` and
`HangTenRopePhysics` retain cord and simulation inputs; edit them with
`Tools/HangboardCAD/set_cad_authoring.py`. Suspension authoring contains only
topology, dimensions, solver settings, evidence, pose rotations/cameras, and
optional `offsetXZ: [x, z]`. Model/source hashes, settled heights, and solved
routes belong only in generated `Hangboards/<slug>/assets/suspension.json`.
The package generator validates that artifact against the current CAD source,
authoring inputs, and model descriptors, then merges it into bundled
`board.json`. Both app platforms stage generated resources only. See
`Tools/HangboardCAD/README.md`. Building or validating packages needs the
FCStd Git LFS objects, not pointers.

Generated board USDZ, `*.model.json`, `*.physics.json`, and
`assets/suspension.json` files are ignored build outputs. Run
`rtk proxy bash scripts/build-board-assets.sh` with pinned
FreeCAD 1.1.3/OpenUSD 26.8 before package validation. For a fresh checkout or
Xcode build, run `rtk proxy bash scripts/build-runtime-assets.sh`; it also
exports the grip hand using Blender 5.2.0. The checked-in
`HangTen/Resources/PlanLibrary.json` is the canonical training-plan source;
edit that audited data directly and preserve its source mappings.
Commit source documents and source audits. Keep generated
grip hand mesh JSON out of Git. CI compiles from sources
once and delivers its artifact to the validation and app-build consumers.
See [`docs/GENERATED_ARTIFACTS.md`](docs/GENERATED_ARTIFACTS.md).

Do not use image-driven hold detection, segmentation, generated masks or
contours, source registration/alignment, vectorization, automatic path
simplification, automatic cropping, or proposal/refine/promote geometry
workflows. Do not reintroduce tooling or guidance for those approaches. The
accepted process is direct path authoring, package validation, and human visual
review in the app.

That prohibition governs the flat 2D `board.json` hold paths. For a native 3D
CAD source it does not forbid measuring the approved display mesh's cross-section
into a vector sketch profile: that is the accepted 3D migration step ("extract the
profile as an ordered boundary loop of the reference's cross-section"), authored
deliberately as a Sketcher profile. Never infer a 3D profile from pixels.

Every geometry change must be shown, not just described: render front/side/top
previews of the changed board next to an export built from the prior committed
source and present them before reporting the change complete. A geometry change without screenshots is
not reported as done.

## Model material policy

All USDZ models must ship without materials or textures. Meshes are unbound so
the renderer uses its default appearance. Do not add PBR materials, image
textures, or color adornments to generated USDZ files. The retained native
compiler, `Tools/HangboardCAD/compile_board.py`, produces unbound meshes from
FreeCAD objects without `MaterialName`. There is no Blender board compiler.

## 3D suspension and On-Demand Resources

For missing or changed cords on model-media boards, use the repository-local
`audit-3d-hangboard-suspension` skill and read
[`docs/3D_SUSPENSION_AND_ODR.md`](docs/3D_SUSPENSION_AND_ODR.md). The USDZ is
the only Apple On-Demand Resource; suspension is bundled package metadata and
renders as transient, non-pickable geometry. Current retained source facts and
evidence govern representation decisions, not superseded design assumptions.

For a corded CAD board, preserve the evidenced connection graph and follow
[`docs/HANGBOARD_CORD_AUTHORING.md`](docs/HANGBOARD_CORD_AUTHORING.md). For
connected internal mouth pairs, the standard method models the hidden passage
as an FCStd void, uses `twoBranchCord` (or `threadedLoopCord`) with
`internalLoop` in `HangTenSuspensionAuthoring`, and measures its channel length with
`measure_channel_spines.py`. For source-backed independent visible leads,
exterior wraps, or mouths whose hidden connection is unknown, use the
`cadRoutedCord` topology and authoring `ropeSolver.method: "nativeRoutes"`;
never invent a hidden join to fit the connected-passage method. Generate every
canonical pose against the actual CAD solid through the pinned build's
`compile_suspension.py` and retained native rope solvers; reproduce generated
routes with `solve_threaded_rope.py --check` and retain native-solid clearance,
length, tube and topology checks. Change CAD authoring parameters and rebuild;
never apply solved heights or routes into the source. Do not hand-author cord routes or keep a
`pairedLeadCord` when a board moves to CAD; extend the solver with evidence and
tests when the supported native methods do not fit. Existing manifest-only
`pairedLeadCord` setups remain in Captain Fingerfood POCKET, J. Bryant FTG-32,
both Lattice MXEdge Lift sizes, and Metolius Light Rail II. Preserve their
evidenced facts during unrelated edits; new or revised cord authoring must use
native solver inputs and computed routes. Their retained caches do not
authorize new hand-authored routes or establish native route certification.

## CodeGraph

When `.codegraph/` exists, use CodeGraph before grep/find to understand or
locate code. The primary shell workflow is `codegraph explore "<query>"`; the
equivalent project-aware MCP tool may be used when available. When
`.codegraph/` is absent, initialize from the repository root with
`codegraph init .` only when indexing is desired, then verify with
`codegraph status`. Generated `.codegraph/` state is local and ignored, and
should not be committed. Use `codegraph sync` after source changes when
maintaining an existing index.
