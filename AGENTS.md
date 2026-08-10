# Agent instructions

## Delegation

Use a fresh subagent for every implementation task or configuration change.
When an approved implementation plan exists, follow subagent-driven
development with per-task implementation and review checkpoints. Do not
make implementation changes directly in the controller session.

When you are the subagent assigned by a controller, implement the assigned
task directly; do not spawn nested subagents or delegate it again.

## Resource lifecycle

Put generated output under `.context` or another explicitly workspace-owned
path. Include `CONDUCTOR_WORKSPACE_NAME` in every external resource name and
record its ownership immediately. Install an exit trap that shuts down and
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

## CodeGraph

When `.codegraph/` exists, use CodeGraph before grep/find to understand or
locate code. The primary shell workflow is `codegraph explore "<query>"`; the
equivalent project-aware MCP tool may be used when available. When
`.codegraph/` is absent, initialize from the repository root with
`codegraph init .` only when indexing is desired, then verify with
`codegraph status`. Generated `.codegraph/` state is local and ignored, and
should not be committed. Use `codegraph sync` after source changes when
maintaining an existing index.
