# Task 1 review package — media-aware logical matching

Review target: `e1e53c19ab3f12c517fb32793d4c49304c353392` (`feat: resolve board matching geometry from media`).

Reviewed against:

- `docs/superpowers/plans/2026-09-08-package-driven-3d-runtime-and-tools.md`, Task 1;
- `docs/superpowers/specs/2026-09-08-beastmaker-1000-3d-design.md` (logical/media separation and matching data flow);
- `AGENTS.md`, `.codex/skills/migrate-hangboard-to-3d/SKILL.md`, and `.codex/skills/validate-hang-ten-ios/SKILL.md`;
- Task 1 brief and implementation report in this directory.

## Static evidence

| Contract | Evidence | Result |
| --- | --- | --- |
| Logical holds contain metadata only | `HangTen/Models/TrainingModels.swift:620-632` declares no presentation, frame, or descriptor-bounds member. | Meets static contract. |
| Raster matching frame is the union of selected presentation pieces | `TrainingModels.swift:724-735` obtains the selected raster pieces, unions their `CGRect`s, and rounds the derived extent. | Meets static contract. |
| Model matching frame comes from selected descriptor AABB | `TrainingModels.swift:736-737`; `BoardModelFacePlaneAABB.holdFrame` at `72-83`. | Meets static contract. |
| Only resolvable holds enter media-aware consumers | `TrainingBoard.holds(in:)` at `884-889`; Board map calls it at `BoardMapView.swift:94-98`; workout candidates call it on exactly `board.defaultPresentation` at `WorkoutActivityRecording.swift:418-425`. | Meets static contract. |
| No cross-presentation matching fallback | The predecessor fallback visible in `e1e53c19^:WorkoutActivityRecording.swift:764-767` is replaced by the single default-presentation resolve at `e1e53c19:WorkoutActivityRecording.swift:765-767`. | Meets static contract. |
| Compact II substitution remains scoped through the new candidate set | `BoardTargetSubstitutionTests.swift:248-257` expects `sloper-round-center`; the resolver now derives candidates at `WorkoutActivityRecording.swift:418-425`. | Test exists, but was not executed in this review. |

`BoardMapPresentationSelection` continues to use `containsHold` solely to choose a presentation (`BoardMapView.swift:209-223`); it does not provide a frame. Rendering and detail-map entries subsequently use `BoardMapPresentationContent`, which calls `holds(in:)` (`BoardMapView.swift:17-31`, `86-103`). No static cross-presentation geometry borrowing remains in this caller chain.

## Test and dependency evidence

The required focused XCTest command did not compile or begin XCTest. The implementation report's final attempt is reproduced by `.context/shaky-rat-task1-green-2.log`:

```
xcodebuild: error: Could not resolve package dependencies:
  fatalError
  Couldn’t check out revision ‘f196cbb98e0388381d57908f2f5a9bdc385cde68’:
  Couldn’t check out revision ‘982b4c787285d213653bd2a504d6a86b52227cea’:
```

`HangTen.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved` pins those revisions to Sentry 8.58.4 and analytics-connector-ios 1.3.2. Read-only cache inspection found both commits in each examined corresponding bare repository under `/Users/asherlc/Library/Developer/Xcode/DerivedData/HangTen-*/SourcePackages/repositories/`; `git cat-file -e <revision>^{commit}` succeeded. The cache references map them to their expected tags. `git fsck --connectivity-only` reported no integrity error (only ordinary dangling commits in some Sentry caches).

Therefore the available evidence rules out a missing pinned revision in the existing shared cache. It does not identify a definitive resolver root cause: Xcode emitted no underlying checkout detail. The fresh `.context/DerivedData` had no private `SourcePackages` cache, and reusing or mutating the global shared cache would violate the isolated-workspace lifecycle. A fresh simulator/XCTest retry would repeat package resolution before test execution, so no XCTest was run by this reviewer.

## Review checks run

- `git diff e1e53c19^ e1e53c19 --check` — clean.
- Direct source/caller audit of `resolvedFrame(in:)`, `holds(in:)`, Board map content/detail paths, `BoardTargetResolver`, `holdIDs(inPosition:)`, and all in-tree `holds(in:)` call sites.
- Read-only package-pin, commit-object, tag-reference, and repository-connectivity checks described above.

No simulator or other external resource was created by this review.
