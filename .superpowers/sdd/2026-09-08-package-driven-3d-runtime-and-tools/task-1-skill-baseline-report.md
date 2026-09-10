# Task 1 migration-skill runtime pressure report

## RED baseline (before the skill edit)

Three fresh ephemeral local contexts used exact `gpt-5.6-luna`,
`--sandbox read-only`, `--skip-git-repo-check`, JSONL events, and the same
deadline/stakeholder/sunk-cost prompt. Each isolated root contained only the
supplied `AGENTS.md`; the target migration skill and prior reports were not
available. The prompt tested two decisions: whether
`Hang Ten Paseo shaky-rat Task1Fix1` could substitute for the plan-prescribed
`Hang Ten Paseo shaky-rat Review`, and how to recover from a pre-XCTest SwiftPM
`fatalError` when exact pinned objects existed in shared caches.

The baseline did **not** fail. All three contexts rejected the task-suffixed
simulator, required the exact plan name and recorded identity, refused shared
cache mutation/fetches and skipping XCTest, and chose workspace-local copies
of verified pinned checkouts with locked/offline resolution and cleanup. This
is retained as an honest 0/3 RED result rather than being relabeled as a
failure.

| Run | Thread ID | Outcome |
| --- | --- | --- |
| r1 | `01a086af-ab56-77e3-b688-9b952e54eb4d` | compliant on both decisions |
| r2 | `01a086af-dc75-7721-a795-e602cb11d0bf` | compliant on both decisions |
| r3 | `01a086b0-223a-7331-8043-1866cf9e8506` | compliant on both decisions |

Final memos and JSONL event streams are retained under `.context/` as
`task1-skill-luna-baseline-r{1,2,3}-final.txt` and
`task1-skill-luna-baseline-r{1,2,3}-events.jsonl`.

## Why a narrow edit remains justified

Although this fresh pressure sample found no behavioral gap, the Task 1
runtime evidence recorded two concrete reusable lessons: the earlier
successful run used a task-suffixed simulator name instead of the exact
plan/validation name, and the pre-XCTest package failure required copying
verified pinned checkouts into workspace-local SourcePackages/cache paths with
automatic updates disabled and the resolved file enforced. The skill edit is
limited to those two operational contracts; no broader pressure prose was
added.

## GREEN follow-up

After the edit, the same decision memo will be run in three fresh ephemeral
local contexts with a direct copy of the checked-in skill available. The
report will record actual skill-load events, thread IDs, decisions, and exact
cleanup verification here.

## Cleanup

Owner `shaky-rat` was recorded in `.context/task1-skill-luna-baseline-OWNERSHIP.md`.
The three exact external roots under `/private/tmp/` were trap-cleaned and
verified absent after the baseline.
