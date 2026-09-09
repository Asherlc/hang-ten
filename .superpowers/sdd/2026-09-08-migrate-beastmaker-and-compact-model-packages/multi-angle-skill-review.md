# Multi-angle migration-skill review

Reviewed 2026-09-09 against commit `1c31be9b` (`docs: require multi-angle
model evidence`), `AGENTS.md`, the complete checked-in
`migrate-hangboard-to-3d` skill, `skill-creator`,
`superpowers:writing-skills`, and `superpowers:test-driven-development`.

## Finding and approval

**Approved for the observed GREEN gate behavior.** The new paragraph is a
narrow correction to the actual RED event: one straight-on Beastmaker image
was passed to Astra before the missing-angle problem was recognized. It binds
the decision to each board and exact revision, requires at least two retained
actual visual snapshots with SHA-256/source/view metadata, requires
materially distinct views, gives manufacturer evidence priority, limits
retailer/distributor material to clearly tiered documented commerce-gap
evidence, names the exclusion set, requires support/non-support notes and
human approval, and says Astra receives every approved image. The final stop
condition covers both an untrusted second view and missing approval.

The wording is technically consistent with the existing source-packet
contract. It does not turn a profile-less diagram, duplicate crop/variant,
search thumbnail, generated render, legacy raster/path asset, or ambiguous
revision into a qualifying view. It does not imply that commerce evidence
overrides manufacturer claims. The exact simulator identity rule remains
unchanged. The unsupported SwiftPM recovery paragraph is absent from the
checked-in skill, while the exact `Hang Ten Paseo <workspace_name> Review`
simulator name remains present.

## Fresh-context GREEN pressure samples

Five independent `codex exec` subprocesses used model `gpt-5.6-luna` with
`--ephemeral --sandbox read-only --skip-git-repo-check`. Each ran from the
workspace-owned temporary root
`.context/multi-angle-skill-review-luna`, whose copied private skill had the
same SHA-256 as the checked-in file:

```json
{
  "checked_in_skill_sha256": "0336bffc505f19a3f2e6a97108c8a1e8515e9e8b2e1c68807a36c4735f3a49e0",
  "copied_skill_sha256": "0336bffc505f19a3f2e6a97108c8a1e8515e9e8b2e1c68807a36c4735f3a49e0",
  "model": "gpt-5.6-luna",
  "skill_opened_before_memo": true,
  "samples": [
    {"rep": 1, "session_id": "01a0870d-b23e-71d1-9194-fe6a51fc2916", "result": "blocked; human approval and missing provenance requested"},
    {"rep": 2, "session_id": "01a0870e-a0b0-7372-a84c-7cce1c7c6be8", "result": "blocked; retailer held as conditional commerce gap"},
    {"rep": 3, "session_id": "01a0870e-a014-7cb3-b788-17d1a8eee8b7", "result": "blocked; exact two-image set and approval required"},
    {"rep": 4, "session_id": "01a0870e-a2fd-7a81-9081-fbef537a8e0b", "result": "blocked; hashes, tier, labels, and support limits required"},
    {"rep": 5, "session_id": "01a0870e-aab3-7ff0-9cf3-743c3d02898d", "result": "blocked; human asked to provide/approve trustworthy second angle"}
  ]
}
```

The same realistic packet was supplied in every run: a manufacturer front,
a profile-less diagram, a duplicate/crop, and a retailer oblique candidate for
the exact Beastmaker 1000 revision, under deadline pressure. All five agents
opened the private skill first. All five rejected the diagram and crop as
non-distinct; none invoked Astra. All five kept the retailer candidate
conditional on exact-revision/provenance metadata and commerce tiering, named
SHA-256/source URL/publisher/view label/support limits, required human
approval, and requested a human decision before proceeding. Their next-step
memos explicitly say to pass both/all human-approved images to Astra after the
gate is satisfied.

The evaluator could not perform a second positive-branch launch after these
five reps: the safety reviewer rejected another call because opening the
private skill in an external evaluator was treated as sensitive-data egress.
This does not weaken the observed blocker result; the checked-in sentence
“Astra receives every approved image” and all five memos cover the positive
handoff obligation. No evaluator wrote repository files or invoked Astra.

## Checks

- `.context/hangboard-packages-venv/bin/python /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/migrate-hangboard-to-3d` → `Skill is valid!`
- `git diff --check 1c31be9b^ 1c31be9b -- ...` → clean

The temporary evaluator root is owned by this workspace and is removed before
handoff; the unrelated pre-existing `Tools/HangboardModels/beastmaker_1000.py`
remains untouched.
