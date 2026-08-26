# Swift and macOS CI Speed Design

## Goal

Reduce pull-request feedback time and macOS runner consumption without weakening the existing iOS, metadata, CodeQL, release, or Workbench validation guarantees.

## Design

The iOS CI workflow will stop reacting to pull-request title and description edits, use the XCTest job as the required Debug simulator build, avoid a redundant focused XCTest rebuild, and target an installed iPhone 17 Pro simulator. The existing stable `Build (Debug simulator)` gate remains, but it reports the XCTest job result. Simulator tests use at most two parallel workers.

App Store metadata validation remains available for metadata-only pull requests. When an iOS test job is already required, validation runs inside that macOS job rather than consuming another runner. SwiftPM source checkouts use a cache shared through an explicit cloned-package directory; cache keys include the runner OS, runner architecture, and the resolved dependency lockfile. Compilation timing summaries remain in logs for later measurement.

The Workbench pull-request workflow moves platform-independent Python and Node tests to Ubuntu. A stable result-reporting gate uses `always()` to report portable and native failures without treating skipped prerequisites as success; the costly macOS artifact build remains path-gated separately. The macOS build caches the native Swift package build directory and runs the proven Debug-mode native tests, while the app build remains Release with debug symbols. The macOS release workflow runs the same portable checks before its native build and uses the same native-package cache convention. The cache improves subsequent SwiftPM work but does not promise Release test/build product reuse. A checked-in Workbench `Package.resolved` makes dependency resolution and cache keys deterministic.

## Validation

These are configuration-only changes. Validate them with YAML parsing, shell syntax checking for the changed validation script, Swift package resolution/build metadata checks where practical, repository-provided workflow/action consistency checks, and diff inspection. Do not add source-text regression tests.
