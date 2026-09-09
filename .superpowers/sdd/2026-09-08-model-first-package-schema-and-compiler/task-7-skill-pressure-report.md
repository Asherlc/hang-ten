# Task 7 skill pressure test

## Matched setup

Both operators received the identical scenario: migrate a board to schema-v2
model media while the existing `scripts/stage-board-packages.py` already calls
parser discovery and recursively copies the package's regular-file tree. The
baseline operator read only repository `AGENTS.md`; the WITH-skill operator
read repository `AGENTS.md` and the complete
`.codex/skills/migrate-hangboard-to-3d/SKILL.md`. Neither operator inspected
task reports or implementation diffs.

## Baseline (without the skill)

Under the release-pressure prompt, Luna proposed a failing integration test
that was expected to show a missing or incorrect model, along with production
changes to parser discovery/staging—even though the scenario already stated
that staging recursively copies regular files. It did correctly require exact
byte/inventory checks, no model substitution, and generated-output cleanup.

## WITH-skill result

The operator left production staging unchanged and added a parser-valid v2
model characterization fixture/test. The first focused test run was GREEN,
because the existing parser-approved recursive copy already satisfied the
staging behavior; no artificial RED or missing-helper failure was introduced.

The characterization assertions require:

- staged USDZ bytes equal source USDZ bytes exactly;
- staged descriptor bytes equal source descriptor bytes exactly; and
- staged assets equal the complete parser-declared regular-file inventory,
  with no missing or extra files.

The operator would not synthesize, rename, replace, or app-side-substitute any
model resource, and would not add a raster fallback to a model-only package.
Generated staging output is placed in an owned workspace `.context`
directory, ownership is recorded immediately, cleanup protection remains
active through failures, and the exact generated directory/resources are
deleted and verified before handoff.
