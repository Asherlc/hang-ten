# Hangboard Collection Model Imports — Design

## Scope

Migrate the six structurally checked GLB deliveries from
`~/Downloads/hangboard-collection` to the catalog's schema-v3, contact-first,
model-only format:

- Metolius Climber's Edge
- Metolius Contact
- Metolius Simulator 3-D
- So iLL Training Tiles
- The Hangboard
- Trango Rock Prodigy Training Center

The other 30 collection manifest entries are explicitly missing or failed
validation and are out of scope. The user approved this exact six-board set on
2026-09-15.

## Architecture

Each catalog package remains the authority for the physical board identity and
its `contacts[]` inventory. The migration replaces its raster presentation
with one USDZ and a hash-bound descriptor generated from imported,
importer-visible model nodes. The descriptor is the only rendering, highlight,
hit-testing, and resolved-spatial-geometry source; raster assets and canonical
paths are removed from every migrated package.

The importer is supplied an explicit per-board source manifest and node-to-
contact mapping. It never infers bindings from mesh names or source imagery.
Non-contact geometry is tagged as `body`; absent, unsupported, or ambiguous
contacts fail the package rather than producing a fallback surface.

## Evidence and Facts

Before import, retain and audit at least two materially distinct visual sources
per exact revision. Prefer the board's existing manufacturer source audit;
supplement it with the downloaded model package's evidence only where its
publisher, URL, hash, review date, and supported facts are recorded. Preserve
only source-backed catalog contact facts. Model bounds, centers, face-plane
bounds, camera framing, and display pose are derived output or explicitly
labeled display estimates, never new factual metadata.

Mounting screws and hardware are omitted from display models. Existing
unsupported model details, including estimated bore locations and unverified
rear geometry, are neither promoted into board facts nor made selectable.

## Package Contract

Each imported package has exactly one default `media.type: "model"`
presentation, an `assets/primary.usdz`, and an
`assets/primary.model.json` descriptor. The descriptor's sorted contact keyset
must exactly equal `board.json`'s `contacts[].id` inventory, and every contact
must bind to one or more importer-visible contact nodes. The USDZ SHA-256 in
the descriptor must match the promoted file.

Existing saved board IDs, revision identities, source-backed contact IDs, and
positions are preserved. Any old raster declarations, image assets, contact
geometry, cached frames, or fallbacks are removed so invalid model loading
fails closed to the explicit unavailable state.

## Delivery and Verification

The implementation is divided into independently reviewable board groups, but
each board is complete only when its source audit, model import, descriptor,
and mapping validate together. The retained model-tool pytest suite, package
validation with final inventory, staging parity, Swift model/picking tests,
and a workspace-owned simulator review must pass. Simulator review inspects
normal and selected contact rendering, picking, and clipping for all six
boards. Generated review output remains under `.context` and owned simulator
resources are recorded and deleted by the required cleanup trap.

No source image tracing, automated geometry inference, raster fallback, or
contact identity rewrite is permitted.
