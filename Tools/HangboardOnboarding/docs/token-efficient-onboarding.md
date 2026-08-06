# Token-efficient onboarding

Send one batched semantic request for the registered source image. Its response
contains exactly five fields per observed physical grip: generic hint key,
piece index, grip type, visual mode, and one coarse cell on a 20×8 grid. Keep
explanations, contours, boxes, dimensions, accepted IDs, and pixel geometry out
of the model response; deterministic local processing owns geometry.

The immutable cache identity includes the registered pixel SHA-256, prompt
SHA-256, compact schema version, provider ID, model ID, and request kind. An
exact hit must replay canonical response bytes without invoking the client.
Cache-only misses, corrupt envelopes, schema changes, and provider/model changes
fail closed. The file-backed proposal provider remains the default.

Run local tracing and every existing containment, connectivity, non-overlap,
topology, determinism, and visual-review gate before escalation. If one region
is ambiguous, escalate only that high-resolution crop with minimal downscaled
board context, request the same five compact fields for that region, and rerun
local refinement once. Do not lower a gate or infer an unseen grip by symmetry.

Runtime reporting separates `model` activity from `localProcessing`. Cached
replay has zero calls and zero tokens. Historical token counts stay null unless
provider telemetry measured them, so percentage token reduction also stays
null with a reason. Compact/full serialized byte counts may be shown only as a
clearly labeled non-token proxy. Any live measurement is credential-dependent;
without configured provider credentials, run cache-only replay and make no live
call.

## Compact subagent brief

Use `fork_turns=none` and send only this information:

```text
Objective: <one concrete outcome>
Worktree: <absolute path>
Task: <one bounded task>
Edit allowlist: <files or directories>
Artifact paths: <accepted inputs and requested outputs>
Pinned hashes: <input and parity SHA-256 values>
Focused command: <one test or replay command>
Return only: commit, changed files, focused test result, artifact paths
```

Keep runtime token evidence and development-agent context accounting separate.
