# Task 1 implementation report

## Baseline

- Task commit: `ea35639bc7b806ff0e3dcedd9a1c020dfd796c46` (`Register new model ODR packages in Xcode project`)
- Task-review parent/baseline: `71e6c56159400ccbc5deb005bc2e579a4b369ac3`
- The project file had no pre-existing diff.
- The parent project file contained 345 left-hand-side object declarations; the task commit contained 357. Reproducible counting method: `rg -c '^\\s+[A-F0-9]+ .* = \\{' HangTen.xcodeproj/project.pbxproj` (run against each revision). This counts the OpenStep `objects` dictionary declarations, rather than every reference to an ID elsewhere in the project file; the task commit likewise has 357 unique object definitions.
- The HangTen Resources phase is `CC0000000000000000000003`.

## Implementation

Modified only `HangTen.xcodeproj/project.pbxproj` with six ODR build-file/file-reference/Resources-phase triplets:

| slug | PBXBuildFile ID | PBXFileReference ID |
| --- | --- | --- |
| `dewoodstok-woodbord` | `D10000000000000000000015` | `D20000000000000000000015` |
| `escape-unlimited` | `D10000000000000000000016` | `D20000000000000000000016` |
| `evolv-kilter-basic-long` | `D10000000000000000000017` | `D20000000000000000000017` |
| `metolius-wood-grips-deluxe-ii` | `D10000000000000000000018` | `D20000000000000000000018` |
| `moon-armstrong` | `D10000000000000000000019` | `D20000000000000000000019` |
| `target10a-linebreaker-base` | `D1000000000000000000001A` | `D2000000000000000000001A` |

Each reference uses `lastKnownFileType = folder`, the required derived ODR path, and `sourceTree = "<absolute>"`; each build file uses the required `hang-ten-model-<slug>` tag. Each Resources entry occurs exactly once in the HangTen Resources phase.

## Tests and checks

- `python3 -m pytest -q Tools/HangboardPackages/tests/test_board_package_staging.py` — not run successfully: `No module named pytest`.
- `plutil -lint HangTen.xcodeproj/project.pbxproj` — `OK`.
- Custom static check — `PASS`: six exact build-file lines, six exact file-reference lines, exactly-once Resources-phase entries, required paths/tags, unique object-definition IDs, and balanced OpenStep delimiters.
- `git diff --check` was attempted; Git LFS emitted an unrelated pre-existing clean-filter error while inspecting the dirty worktree (`.context/migration/dewoodstok-woodbord/source.blend`).

## Self-review and concerns

- Diff contains only the six requested triplets in the Xcode project file.
- The six selected build/reference ID pairs were absent from the complete pre-edit object-ID enumeration.
- Unrelated migration/LFS changes were preserved and not staged.
- Concern: the focused pytest dependency is unavailable in the environment; equivalent static and plist checks pass.

## Commit and push status

- `ea35639bc7b806ff0e3dcedd9a1c020dfd796c46` changes only `HangTen.xcodeproj/project.pbxproj` relative to `71e6c56159400ccbc5deb005bc2e579a4b369ac3` (18 insertions).
- Historical task-time remote status: pending/not verified. This report did not retain a local remote-ref confirmation, so it does not claim that the task commit was pushed successfully.
- Any later controller push is separate from the historical task status above and requires its own remote verification.
