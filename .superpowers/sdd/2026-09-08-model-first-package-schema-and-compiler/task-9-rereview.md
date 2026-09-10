# Task 9 documentation rereview

Range reviewed: original Task 9 documentation commit `6248ecd4`, correction
`a2b2dff1` (`docs: clarify canonical hold ownership`), and the current three
Task 9 README files.

Verdict: **APPROVED**. The prior Important finding is resolved, and no other
documentation inaccuracies were found.

## Prior finding resolved

`Tools/HangboardModels/README.md:17-20` now says that canonical raster
presentations “collectively must form an exact, single-owner partition of all
logical hold IDs.” This is the contract implemented by
`Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:1052-1083`,
which counts ownership across all original raster presentations and requires
each logical ID to occur exactly once. It correctly permits a hold inventory
to be partitioned across multiple canonical raster presentations.

The checked-in `Hangboards/captain-fingerfood-dual/board.json:16-29,161-178,
281-292` exercises this case: `primary` owns `straight-edge-20` and
`outer-jug`, while `reverse` owns `curved-edge-20` (`:400-415` lists the
logical IDs). The corrected wording therefore no longer instructs authors to
duplicate every hold into every canonical raster presentation.

## Contract and derived-rule review

- The migration skill’s exact rule (`.codex/skills/migrate-hangboard-to-3d/SKILL.md:25-28`)
  matches the corrected ownership statement. Derived raster presentations and
  model derivation/inversion rules in `Tools/HangboardModels/README.md:17-29`
  match parser enforcement at `board_catalog.py:403-510,802-860,1084-1095`.
- The three Task 9 docs consistently describe logical v2 data separately from
  typed presentation media, model-only packages, hash-bound descriptors,
  byte-preserving staging, and the absence of a live model migration:
  `README.md:7-13,45-50,226-269`,
  `Tools/HangboardPackages/README.md:29-41,116-164`, and
  `Tools/HangboardModels/README.md:3-93`.
- The packet CLI description is accurate: `README.md:237-242`,
  `Tools/HangboardPackages/README.md:141-148`, and
  `Tools/HangboardModels/README.md:43-53` match
  `Tools/HangboardModels/validate_evidence_packet.py:13-27`.
- The compiler CLI and output description are accurate:
  `README.md:244-260`, `Tools/HangboardPackages/README.md:150-164`, and
  `Tools/HangboardModels/README.md:55-92` match
  `compile_model_package.py:125-207,478-495`. The implementation reimports
  the actual USDZ, derives the descriptor, and publishes exactly the USDZ and
  `.model.json` files.
- No reviewed README introduces an image-driven geometry workflow or grants
  target-board geometry migration. The plan’s Task 9 scope remains
  documentation/integration verification only (`docs/superpowers/plans/2026-09-08-model-first-package-schema-and-compiler.md:410-437`),
  with final verification listed separately at `:439-444`.

## Fresh verification

- `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed with 61 complete packages and `drafts: []`.
- Inventory census: 61 `Hangboards/*/board.json` files, all schema v2; 96
  declared presentations, all `raster`; 0 `model` presentations. This
  confirms the 61/61 raster, 0 model checkpoint stated in all three docs.
- The literal plan command’s package/test invocation reached system Python,
  which has no pytest module. The same requested suite through the existing
  workspace venv passed: `531 passed in 40.01s`.
- `rtk proxy python3 -B Tools/HangboardModels/validate_evidence_packet.py
  --help` passed and showed the documented positional `packet` CLI. Compiler
  argument inspection confirms the documented `--blend`, `--board-json`, and
  `--output-directory` options. A fresh Blender `--help` invocation terminated
  with the known sandbox USD startup signal 11 before script execution; this
  is an environment limitation, not a documentation finding.
- `rtk git diff --check 6248ecd4^ a2b2dff1` and
  `rtk git diff --check a2b2dff1^ a2b2dff1` produced no output.

No implementation, package, or README files were changed by this rereview.
