# Complete Hangboard Visual Audit Design

## Goal

Audit every completed direct-child package under `Hangboards/` against the exact
Workbench rendering path and authoritative external evidence, then improve only
the packages whose metadata or geometry can be corrected without unsupported
inference. The result must preserve low-complexity, exact-path interaction
geometry and make the entire review repeatable for future boards.

## Scope and evidence

The catalog boundary is every direct child containing `board.json` at the audit
commit. Primary manufacturer product pages, manuals, dimensional diagrams, and
official product images are preferred evidence. Secondary sources may locate
primary material but cannot justify changed hold facts. Every changed metadata
field must map to a cited source; unsupported optional fields are removed rather
than guessed.

## Rendering and review

A generic Workbench capture command loads each board through the existing HTTP
API and browser editor, waits for the canonical primary image and every SVG hold
path, and captures the board canvas at a fixed viewport. It accepts any catalog
inventory and contains no product IDs, coordinates, masks, or per-board tuning.
The audit retains labeled before and after contact sheets plus every individual
per-board before/after capture in the source-audit assets, and records per-board
hold, geometry-piece, and editable-point counts.

Visual inspection checks that every documented hold is represented, no artwork
or highlight drifts from its physical contact, paired geometry is consistent
unless evidence shows asymmetry, and the silhouette matches official front and
oblique evidence. A package is unchanged when evidence does not support a
specific correction.

## Geometry changes

The existing generic simplifier is the first low-point-count pass. Any further
redesign must use the same normalized shapes and validation contracts for all
boards, preserve the logical hold and piece inventories unless authoritative
evidence proves them wrong, and pass native-pixel error gates. Product-specific
code paths, hand-authored masks, special-case coordinates, and per-board tuning
are forbidden.

## Validation and deliverables

Package validation, Workbench tests, simplifier idempotence, presentation
idempotence, generic simulator build-for-testing, and an owned-simulator visual
check are required. The PR contains the source-audit report, labeled before and
after contact sheets covering every completed board, all full-resolution
per-board before/after captures, the reusable capture method, and only
evidence-backed package changes.
