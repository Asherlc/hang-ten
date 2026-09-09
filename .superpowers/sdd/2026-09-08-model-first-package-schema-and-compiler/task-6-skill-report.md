# Task 6 skill report

## Scope

Updated only `.codex/skills/migrate-hangboard-to-3d/SKILL.md` and this report.
No app code, board packages, schemas, generated assets, or server resources
were changed.

## Durable rules integrated

- Discover the live package inventory at execution time. Bulk conversion must
  be deterministic and idempotent, preserving recognized fields or rejecting
  documents; duplicate and unknown legacy members must not be silently lost.
- Audit every package before and after migration with type- and order-sensitive
  comparisons covering logical metadata, presentation relationships, geometry
  structure and scalars, and assets. Follow with converter check, exact version
  counts, package validation, and both language suites.
- Require nonempty original raster media to partition logical holds exactly
  once. Derived raster media must be original-to-derived and raw-equal to its
  source; reject empty/redundant media, duplicate or missing owners, drift, and
  chains.
- Treat optional closed-schema members as omission-only; present values decode
  their concrete type, and explicit `null` fails consistently across languages.
- Preserve ordered raw JSON structure and scalar kind across languages. Keep
  integers exact with Python-compatible zero normalization; compare finite
  floating values after binary64 decoding without merging numeric kinds.
- Apply the iOS validation lifecycle to migration XCTest: register an exact
  owned UUID before use, retain cleanup through RED/GREEN and compile failures,
  clean failed preliminary devices, bound polling, summarize xcresults, and
  remove simulator and workspace test artifacts before handoff.

## Validation

```text
.context/hangboard-packages-venv/bin/python /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/migrate-hangboard-to-3d
Skill is valid!

rtk git diff --check
passed with no output
```

The final approved Task 6 review artifacts supplied the migration countercases
and cross-language parity evidence used to make these rules explicit. No new
simulator or runtime validation was needed for this documentation-only change.
