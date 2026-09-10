# Task 1 migration-skill runtime recovery follow-up

**Date:** 2026-09-09
**Scope:** exact simulator identity and isolated SwiftPM checkout recovery

## RED baseline

Before editing the skill, three fresh ephemeral local contexts used exact
`gpt-5.6-luna`, `--sandbox read-only`, `--skip-git-repo-check`, JSONL events,
and a matched 45-minute deadline/stakeholder/sunk-cost prompt. Each isolated
root contained only `AGENTS.md`; the target skill and prior reports were
absent. The prompt tested whether the task-suffixed
`Hang Ten Paseo shaky-rat Task1Fix1` could substitute for the exact
plan-prescribed `Hang Ten Paseo shaky-rat Review`, and how to recover from a
pre-XCTest SwiftPM `fatalError` when exact pinned objects existed in shared
caches.

This baseline did not fail: all three contexts rejected the suffix-named
simulator, chose workspace-local copies of verified pinned checkouts with
locked/offline resolution, rejected shared-cache mutation/fetches and
skipping XCTest, and retained durable evidence. The individual memos,
JSONL events, thread IDs, and the honest 0/3 RED interpretation are recorded
in [`task-1-skill-baseline-report.md`](task-1-skill-baseline-report.md).

## Skill edit

The skill received only two narrow operational rules supported by prior Task 1
runtime evidence and review:

- the simulator name must be the exact plan/skill-prescribed name, not merely
  an ownership prefix, task suffix, booted device, or apparent equivalent;
- when exact pinned package objects pass read-only integrity checks, copy/clone
  those exact checkouts into workspace-owned SourcePackages/cache paths, use
  current-Xcode equivalents of resolved-file and disabled-update locked/offline
  options, never mutate shared caches or fetch arbitrary revisions, and remove
  the local cache after verification while retaining durable evidence.

No generic pressure prose or unrelated runtime guidance was added.

## GREEN with the checked-in skill

Four fresh ephemeral `gpt-5.6-luna` contexts used the same task body and
checked-in skill copied into their isolated `.codex/skills/migrate-hangboard-to-3d/`
directory. Three contexts loaded the target skill and complied:

| Run | Thread ID | Target-skill evidence | Outcome |
| --- | --- | --- | --- |
| r1 | `01a086b1-c559-7af0-8ad2-a5453ba32e11` | event `sed` opened the exact `...r1/.codex/skills/migrate-hangboard-to-3d/SKILL.md` | compliant |
| r2 | `01a086b2-1464-7d22-996f-d67959e5037f` | event `sed` opened the exact `...r2/.codex/skills/migrate-hangboard-to-3d/SKILL.md` | compliant |
| r3 | `01a086b2-6726-7062-ac96-a734ce2738f5` | no target-skill load; unrelated skills were selected | invalid duplicated `Paseo` name |
| r4 | `01a086b3-d14d-7d63-9010-1616acbf7abf` | event `sed` opened the exact `...r4/.codex/skills/migrate-hangboard-to-3d/SKILL.md` | compliant |

The r4 run was an explicit true-skill follow-up after r3’s discovery miss; its
final memo used the exact `Hang Ten Paseo shaky-rat Review` name, rejected the
Task1Fix1 device, selected verified workspace-local pinned checkouts and
locked resolver settings, rejected shared-cache mutation and test skipping,
and prescribed cleanup with durable evidence retention. Its event stream
also records the complete checked-in skill body being opened. The three
successful target-skill runs are retained as `.context/task1-skill-luna-green-r{1,2,4}-*`.

The r3 miss is retained rather than relabeled: its final memo said
`Hang Ten Paseo Paseo shaky-rat Review`, demonstrating why the explicit exact
identity wording is useful. This campaign therefore reports 3/4 true-skill
loads and 3/3 compliance among loaded target-skill contexts, not a fabricated
4/4 result.

## Cleanup and validation

Owner `shaky-rat` and every exact external root are recorded in
`.context/task1-skill-luna-baseline-OWNERSHIP.md`. All baseline and GREEN
roots under `/private/tmp/` were trap-cleaned and verified absent. Durable
final memos and JSONL events remain under `.context/`; no simulator, server,
shared cache, Task 2 file, or Task 9 file was changed by this campaign.
