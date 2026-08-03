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
