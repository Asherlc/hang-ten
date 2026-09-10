# Task 9 independent review

Range: `6248ecd4^..6248ecd4` (`docs: describe model-first package tooling`)

Verdict: **REQUEST CHANGES** — one Important documentation finding.

## Finding

### P1 — Raster ownership sentence contradicts the v2 contract

`Tools/HangboardModels/README.md:17-20` says that “a canonical raster
presentation must own every logical hold exactly once.” The schema does not
require each canonical presentation to contain the whole inventory. It requires
the original raster presentations collectively to form an exact, single-owner
partition. `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:1052-1083`
counts ownership across all original presentations, and the existing
`Tools/HangboardPackages/tests/test_model_first_packages.py:508-520` names and
tests that partition behavior.

The live `Hangboards/captain-fingerfood-dual/board.json:16-29,281-292` is a
checked-in counterexample: its original `primary` presentation owns
`straight-edge-20` and `outer-jug`, while its original `reverse` presentation
owns `curved-edge-20`. The current sentence would tell future package authors
to duplicate all logical holds into every canonical raster presentation and
misdescribe a valid package as invalid. Qualify it to say that canonical raster
presentations collectively own every logical hold exactly once.

## Confirmed

- `README.md:7-13,41-50,226-260`, `Tools/HangboardPackages/README.md:29-41,116-164`,
  and `Tools/HangboardModels/README.md:3-93` consistently describe logical
  schema-v2 data separately from tagged presentation media, model-only package
  isolation, hash-bound descriptors, byte-preserving staging, and the explicit
  absence of a live model migration. The implementation agrees at
  `board_catalog.py:454-510,835-860,1046-1095,1248-1319` and
  `compile_model_package.py:125-207`.
- The live inventory check found 61 `Hangboards/*/board.json` documents, all
  with `schemaVersion: 2`; their 96 declared presentation media entries are
  all `raster`, with zero model packages. The canonical validator reported 61
  complete packages and `drafts: []`.
- The packet command is an actual CLI at
  `Tools/HangboardModels/validate_evidence_packet.py:13-27`; its documented
  invocation is valid. The packet documentation retains the primary-source
  policy: HTTPS URLs, retained regular files beneath the packet directory,
  exact hashes, manufacturer-first evidence, documented commerce gaps, and no
  geometry/proposal fields. The validator enforces the retained-source and
  provenance/conflict rules at `evidence_packet.py:116-143,188-241,279-331`.
- The documented compiler command matches the Blender entrypoint arguments at
  `Tools/HangboardModels/compile_model_package.py:478-495`. Its source performs
  actual USDZ reimport and descriptor generation, rejects malformed or
  mismatched geometry/material/binding state, and publishes only the two
  declared assets (`:125-207`). The README does not imply that either target
  board already has model geometry or that this plan authorizes geometry work.
- No reviewed documentation introduces an image-driven geometry workflow.
  Instead, `Tools/HangboardModels/README.md:32-53` requires retained evidence,
  rejects coordinates/contours/masks/vectors/tracing/alignment and numeric
  shape prescriptions in the packet, and defers geometry authoring and visual
  review to a later scoped step.

## Verification

- `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed with 61 complete packages and no drafts.
- The literal focused command from `task-9-brief.md` reached the system
  Python, which has no installed `pytest` module. The same requested suite run
  through the existing workspace venv passed: `531 passed in 39.24s`.
- Additional focused documentation/model/parser tests passed: `103 passed in
  1.21s`.
- `rtk git diff --check 6248ecd4^ 6248ecd4` passed with no output.
- Packet `--help` and compiler source/argument inspection passed. A fresh
  Blender 5.2.0 `--help` invocation terminated with the known sandbox USD
  startup signal 11 before script execution; this is an environment limitation
  and not a documentation finding. The prior Task 3 report records the same
  exact documented Blender entrypoint succeeding outside that sandbox.
- The target commit changes only the three requested README files. This review
  adds no implementation or documentation changes beyond this artifact and
  creates no persistent external resources.
