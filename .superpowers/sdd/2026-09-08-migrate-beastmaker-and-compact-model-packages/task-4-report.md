# Task 4 — model-package promotion

Date: 2026-09-09

## Scope and approval gates

Promoted the approved model-only exports for Beastmaker 1000 and Metolius
Wood Grips Compact II. Logical board metadata, equipment records, hold IDs,
hold order, and primary presentation identity/name/aspect/default values are
unchanged. The two presentations now use only model media with the required
orthographic camera (`viewDirection [0,0,-1]`, `up [0,1,0]`, `fitPadding 0.08`).
All canonical raster hold geometry and target PNG assets were removed.

The retained Beastmaker reports now record the controlling session's explicit
visual-fidelity approval of the corrected `c3a15af5` front, three-quarter, and
clay-detail renders. This is the human approval for the corrected actual
export; native SceneKit/runtime validation remains a separate integration
task. Compact's durable export report records approval of the final renders,
as recorded by `e4130730`.

## Source selection and hashes

The Beastmaker source selection was resolved against the Task 2 and Task 3
records. The later Task 3 compiler output at
`.context/shaky-rat-beastmaker-1000/package/` matches its retained
`export-verification.json` and records the required 112,064 explicit
triangles. Its exact promoted bytes are:

| Board | USDZ SHA-256 | Descriptor SHA-256 |
| --- | --- | --- |
| Beastmaker 1000 | `e15bae1d9664b834ee68853cecba47076617bdd382458b26700d18e321e146e3` | `2c392869087b6729870010d7606dd3a500eb659d48f80fe851115ff62b71984b` |
| Compact II | `220c68ea5519b0bed80cd2aac08b35f5f2c2a7d2200596f62c3a84996efb94a3` | `300a26886362dd0c510c729e1a9fd4e6a35f47497aed5e7f12d33a2fdb7068fe` |

The earlier Task 2 `package-round-2/` Beastmaker export
(`0251193c0c32e620b9aa153b354ad976a55b63fecab43d18c9828ba1afdf894c` /
`b09a66150dee26e295b09a6de0cd8b86abef7afd46f37a6d538bc191e1e769fe`) was
not promoted. The destination assets were independently
rehashed byte-for-byte against the selected source packages, and each
descriptor's `modelSHA256` matches its actual destination USDZ.

## Final package and resource changes

Each target package contains exactly:

```text
board.json
assets/primary.usdz
assets/primary.model.json
```

The descriptor inventories match the logical holds exactly: 22 Beastmaker
hold IDs and 19 Compact II hold IDs. The authorized legacy resource
`HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz` was deleted, along
with its four exact Xcode project references (resource build file, file
reference, Resources-group child, and Resources-phase entry). The source
boundary tracked-path manifest was regenerated for the post-removal tracked
inventory. No unrelated resources were removed.

## Verification

- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  — PASS (61 complete packages, 0 drafts).
- `python -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`
  — PASS (42 passed).
- `python -B -m pytest Tools/HangboardModels/test_model_descriptor.py -q`
  — PASS (33 passed).
- `python -B Tools/HangboardModels/test_model_reports.py` — PASS (12 tests).
- Semantic preservation audit — PASS: all non-media board fields and
  presentation metadata match HEAD; no `holdGeometry`, raster media, PNG,
  fallback, or canonical 2D path remains in either target package.
- Exact final-tree audit — PASS: each target has only `board.json` and the two
  declared model assets; descriptor hold/node IDs equal logical IDs.
- Source-boundary inventory audit — PASS after the authorized legacy resource
  removal is reflected in the index.
- `git diff --check` — PASS before commit.

Task 4 fix-round RED verification reproduced 7 failures and 21 passes in the
pre-existing `test_approved_board_packages.py` suite: its generic owner and
asset checks plus Compact-specific cases assumed raster-only media. The suite
was updated to preserve raster coverage for unrelated boards while asserting
the model-only contract for both targets, including PNG-fallback rejection.
GREEN verification now passes all 29 tests. The model-aware validator,
model-first suite, descriptor suite, report suite, and the new Compact
package-vs-standalone-resource XCTest coverage are also included in this fix.

`xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator
-configuration Debug -derivedDataPath .context/shaky-rat-task4-fix-deriveddata
CODE_SIGNING_ALLOWED=NO build-for-testing` — PASS; both app and test bundles
were produced. The workspace-owned DerivedData and build log were removed and
their exact path was verified absent after the build.

This task does not claim native SceneKit, simulator, or app interaction
validation.
