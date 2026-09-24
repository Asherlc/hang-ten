# Agent instructions

## Delegation

Use a fresh subagent for every implementation task or configuration change.
When an approved implementation plan exists, follow subagent-driven
development with per-task implementation and review checkpoints. Do not
make implementation changes directly in the controller session.

When you are the subagent assigned by a controller, implement the assigned
task directly; do not spawn nested subagents or delegate it again.

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
precedent. An operator must deliberately draw and review every canonical hold
path in `board.json`; exact left/right mirroring is preferred when the product
is actually symmetric.

The apps only read bundled packages; there is no in-app board editor. When
the checked-out schema supports shape constraints, author an operator-selected
constraint directly in `board.json` for holds that are genuinely circles,
ovals, pills, rounded rectangles, or rectangles. Freeform paths remain valid
for irregular holds. A constraint is editing metadata only: the saved path
remains the sole rendering, highlighting, and hit-testing source of truth.
Never infer a constraint from pixels.

A model package with a native FreeCAD source (`Hangboards/<slug>/<slug>.FCStd`)
is different: the FCStd is its only source. Its `board.json` is generated from
the FCStd's `HangTenBoardManifest` property at build time (package validation,
iOS and Android staging) and is never committed; the validator rejects an
on-disk copy. Change the metadata with `Tools/HangboardCAD/set_board_manifest.py`;
see `Tools/HangboardCAD/README.md`. Building or validating packages needs the
FCStd Git LFS objects, not pointers.

Do not use image-driven hold detection, segmentation, generated masks or
contours, source registration/alignment, vectorization, automatic path
simplification, automatic cropping, or proposal/refine/promote geometry
workflows. Do not reintroduce tooling or guidance for those approaches. The
accepted process is direct path authoring, package validation, and human visual
review in the app.

## 3D suspension and On-Demand Resources

For missing or changed cords on model-media boards, use the repository-local
`audit-3d-hangboard-suspension` skill and read
[`docs/3D_SUSPENSION_AND_ODR.md`](docs/3D_SUSPENSION_AND_ODR.md). The USDZ is
the only Apple On-Demand Resource; suspension is bundled package metadata and
renders as transient, non-pickable geometry. Current retained source facts and
evidence govern representation decisions, not superseded design assumptions.

## CodeGraph

When `.codegraph/` exists, use CodeGraph before grep/find to understand or
locate code. The primary shell workflow is `codegraph explore "<query>"`; the
equivalent project-aware MCP tool may be used when available. When
`.codegraph/` is absent, initialize from the repository root with
`codegraph init .` only when indexing is desired, then verify with
`codegraph status`. Generated `.codegraph/` state is local and ignored, and
should not be committed. Use `codegraph sync` after source changes when
maintaining an existing index.
