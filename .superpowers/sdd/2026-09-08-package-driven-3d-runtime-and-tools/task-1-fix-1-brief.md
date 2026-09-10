# Task 1 fix 1 — media-aware workout matching coverage

Close the Task 1 review gaps without changing production behavior unless a
focused regression proves that behavior is wrong.

- Add native `WorkoutActivityRecordingTests` coverage for a synthetic model
  descriptor's `facePlaneAABB`, absent selected-media mappings, and the rule
  that workout matching/side/symmetry logic never borrows geometry from a
  non-default presentation.
- Retain and execute Compact II's existing round-sloper substitution test.
- Give the existing fractional-depth fallback fixture actual selected raster
  geometry; its prior implicit empty raster media is unavailable by the Task 1
  contract and cannot legitimately participate in matching.
- Diagnose the pre-XCTest package failure with read-only shared-cache
  inspection and a copied, workspace-local SwiftPM source-package directory.
  Do not mutate a shared cache or fetch any unpinned revision.

The package-lock failure must be reported honestly: Xcode's original nested
checkout error has no diagnostic beyond `fatalError`; evidence may establish a
safe isolated workaround but not invent a deeper cause.
