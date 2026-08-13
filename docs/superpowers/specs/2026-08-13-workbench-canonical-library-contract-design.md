# Workbench Canonical Library Contract Design

## Goal

Restore published-board loading in Hangboard Workbench after the canonical package migration by making `Hangboards/` the only repository board-library location.

## Root Cause

The package migration made `Hangboards/` the canonical board source, but the workbench still validates a checkout and configures `RepositoryBoardLibrary` around the obsolete `Tools/HangboardPipeline/boards/` path. That library expects Stage-4 onboarding runs (`run.json` and stage artifacts), whereas the canonical source now contains validated packages (`catalog.json`, `board.json`, `artwork.json`, and `assets/primary.png`). A directory rename alone would therefore replace an unavailable legacy dependency with an incompatible format.

## Design

The workbench checkout contract is updated in every owning layer:

- Python server validation requires `Hangboards/`, the pipeline source package, the workbench server, and `.git`.
- A canonical-package library reads and validates `Hangboards/catalog.json` and its registered packages. It supplies the existing workbench library interface: snapshot, lookup, a stable revision token, and an isolated runtime materialization operation.
- Opening a published package produces a complete, editable runtime revision below `.context/hangboard-workbench/`. The materialized stage artifacts are derived from the package's primary image and authoritative artwork metadata; they are working copies only. Saving or revising never reads from, writes to, or falls back to `Tools/HangboardPipeline/boards/`.
- The native macOS checkout picker validates the same canonical markers and tells users the same requirement.
- Documentation names `Hangboards/` as the published-board source.

No fallback path is permitted. A checkout containing only `Tools/HangboardPipeline/boards/` is invalid for the workbench.

## Contract Test

Add a server-level regression test that constructs a valid canonical checkout with `Hangboards/` and a registered, valid package, invokes the normal workbench startup path, and proves the full opening contract: `GET /api/library` returns that canonical board, `GET /api/boards` returns the runtime list, and opening the returned board ID creates a usable runtime revision. The test must fail if checkout validation, package discovery, or opening reverts to the legacy board directory.

Native checkout-selection tests will also assert that `Hangboards/` is required and `Tools/HangboardPipeline/boards/` alone is rejected.

## Error Handling

Missing or malformed canonical package content remains a repository diagnostic, not a hidden fallback to a legacy source. Invalid checkout selection continues to show the existing actionable checkout error.

## Verification

Run the focused Python server tests, JavaScript workbench tests affected by the opening contract, and the macOS Swift package tests. Start the server against this repository and confirm `/api/library` and `/api/boards` return successful JSON responses.
