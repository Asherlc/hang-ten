# Workbench Canonical Library Contract Design

## Goal

Restore published-board loading in Hangboard Workbench after the canonical package migration by making `Hangboards/` the only repository board-library location.

## Root Cause

The package migration made `Hangboards/` the canonical board source, but the workbench still validates a checkout and configures `RepositoryBoardLibrary` around the obsolete `Tools/HangboardPipeline/boards/` path. The native app accepts the current checkout shape only if that removed directory exists, while the backend attempts to load boards from it. As a result, both opening-screen list requests fail in the released workbench.

## Design

The workbench checkout contract is updated in every owning layer:

- Python server validation requires `Hangboards/`, the pipeline source package, the workbench server, and `.git`.
- `RepositoryBoardLibrary` discovers packages directly from `Hangboards/` and never consults the removed pipeline board directory.
- The native macOS checkout picker validates the same canonical markers and tells users the same requirement.
- Documentation names `Hangboards/` as the published-board source.

No fallback path is permitted. A checkout containing only `Tools/HangboardPipeline/boards/` is invalid for the workbench.

## Contract Test

Add a server-level regression test that constructs a valid canonical checkout with `Hangboards/`, invokes the normal workbench startup path, and proves that both opening-screen data sources are available: `GET /api/library` returns the repository snapshot and `GET /api/boards` returns the runtime list. The test must fail if either checkout validation or repository-library discovery reverts to the legacy board directory.

Native checkout-selection tests will also assert that `Hangboards/` is required and `Tools/HangboardPipeline/boards/` alone is rejected.

## Error Handling

Missing or malformed canonical package content remains a repository diagnostic, not a hidden fallback to a legacy source. Invalid checkout selection continues to show the existing actionable checkout error.

## Verification

Run the focused Python server tests, JavaScript workbench tests affected by the opening contract, and the macOS Swift package tests. Start the server against this repository and confirm `/api/library` and `/api/boards` return successful JSON responses.
