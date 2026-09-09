# Review package: 3985dd06

## Scope

Independent review of `3985dd06` (`test: align model package parsers`) against
the Task 8 brief, the approved model-first plan, `AGENTS.md`, and the complete
`migrate-hangboard-to-3d` skill.

## Changed files

- `.superpowers/sdd/2026-09-08-model-first-package-schema-and-compiler/task-8-report.md`
- `HangTenTests/BoardPackageStoreTests.swift`
- `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
- `Tools/HangboardPackages/tests/test_model_first_packages.py`

No production parser, model, staging, or catalog source file is changed by the
commit.

## Review evidence

The shared fixture matrix is a single JSON array at
`HangTenTests/Fixtures/BoardPackageValidationFixtures.json:62-152`. It contains
exactly the required eleven named cases, with language-specific expected
categories. Both consumers read the same `model` base board, descriptor, and
base64 model bytes. Python applies the ordered mutations and writes the package
at `Tools/HangboardPackages/tests/test_model_first_packages.py:38-99`; Swift
applies the same operations and writes the package at
`HangTenTests/BoardPackageStoreTests.swift:3111-3159`. Both use production
parsers, not reimplemented validation.

Python parameterization and rejection assertion are at
`Tools/HangboardPackages/tests/test_model_first_packages.py:402-420`. Swift
asserts the complete ordered name list and checks each declared error case at
`HangTenTests/BoardPackageStoreTests.swift:32-64`; its category switch accepts
only `.invalidPackage` or `.malformedJSON` as declared by the fixture.

Fresh checks:

- `rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q` — `42 passed in 0.16s`.
- Directly invoking each shared Python case produced a `ValueError` with the
  rule-specific production-parser reason for all eleven cases.
- `git diff --check 3985dd06^ 3985dd06` passed.
- `python3 -m json.tool HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
  passed.
- `git diff --quiet 3985dd06^ 3985dd06 -- HangTen/ HangTen/Models Tools/HangboardPackages/src`
  returned exit 0, confirming no production parser/source diff.

The independent Swift invocation used the recorded UUID and workspace-local
output paths but returned exit 74 before compilation: CoreSimulatorService was
unavailable and Xcode could not resolve uncached Git package dependencies due
the restricted network. The implementation report records its earlier
successful run as `107 passed`, `0 failed`, `0 skipped`. The failed
independent attempt's exact `DerivedData-review-task8` and result-bundle paths
were removed afterward.

## Resource audit

The implementation report records the exact simulator UUID, ownership marker,
pending/owned manifest protocol, preliminary UUID cleanup, and final artifact
cleanup. At review time both `.context/paseo-owned-simulators` and
`.context/paseo-pending-simulators` exist at zero bytes, and the review-created
DerivedData/result paths are absent. Historical simulator deletion cannot be
requeried while CoreSimulatorService is unavailable, but there is no contrary
repository evidence and no resource leak introduced by the fixture changes.

## Verdict

No findings. Task 8 satisfies the shared eleven-case fixture, deterministic
mutation, language-specific assertion, no-production-parser-change, and
cleanup/report requirements.
