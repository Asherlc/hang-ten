# Import Hangboard Model Packages Design

**Status:** approved direction; implementation awaits review of this written contract.

## Goal

Import the four model packages in `/Users/asherlc/Downloads/models` into Hang Ten:

- replace the raster presentation of `metolius-simulator-3d`;
- replace the raster presentation of `soill-training-tiles`;
- replace the raster presentation of `yy-baguette-evo`;
- add the supplied standard Nature Climbing Stone Hanger as a new `nature-stone-hanger` board.

The migrated packages are model-only: their USDZ model and generated descriptor are the sole rendering, highlighting, hit-testing, and display-derived matching source. Existing logical hold IDs and source-backed metadata remain stable for the three replacements. The new Nature board receives metadata only from the retained package evidence and does not inherit metadata from the visually similar Stoak or Stone Hanger Mini boards.

## Package mapping and identity

The supplied packages are authoritative for the model geometry, object inventory, materials, markers, and validation reports. Their GLB exports are not copied directly into shipped board packages because the repository contract requires `assets/primary.usdz` plus a generated `assets/primary.model.json` descriptor.

The importer/compiler will convert or reopen each supplied model in the repository's canonical `hang-ten-board-v1` frame, preserve importer-visible object names, bind each selectable mesh to a logical hold ID, generate descriptor bounds and centers from actual exported mesh vertices, and hash the exact shipped USDZ bytes. Where ZIP mesh names differ from existing logical IDs, an explicit checked-in mapping is required; no positional inference or 2D-path reuse is allowed.

Required mapping surfaces:

- Metolius: `hold_01_*` through `hold_18_center` map to the existing `jug-*`, `round-sloper-*`, `edge-*`, and `pocket-*` IDs in `metolius-simulator-3d`.
- Training Tiles: `hold-L-*` and `hold-R-*` map to the existing left/right pocket, sloper, middle-edge, and bottom-edge IDs in `soill-training-tiles`; the model's mirrored mesh names do not replace the stable app IDs.
- Baguette Evo: retain the existing `edge-*` and `rounded-tray` IDs, including all five presentations' existing logical inventory, while the model presentation becomes the default single presentation.
- Nature Stone Hanger: create logical IDs matching the package's eight contacts (`edge-front-15mm-incut`, `edge-front-15mm-flat`, `edge-front-20mm-wood-flat`, `edge-front-20mm-granite`, `edge-reverse-10mm-incut`, `edge-reverse-10mm-flat`, `edge-reverse-06mm-flat`, `edge-reverse-06mm-incut`), and preserve the two cord-passage markers through the suspended-board package contract as nonselectable model metadata.

The Nature package is the standard Granite Stone Hanger, not `nature.stoak-board-iii`, `nature.stone-hanger-mini`, or `nature.stone-hanger-mini-karma8a`; its distinct catalog ID and metadata prevent accidental identity overwrite.

## Model conversion and app integration

Implementation will reuse the existing model-first package parser, compiler, staging, SceneKit loader, and model view. It will selectively port the suspended-board support from branch `load/3d-hangboard-models`, including the two-branch package contract, deterministic cord solver, parser parity fixtures, and `SuspendedBoardPresentation` integration/tests as needed by the Nature markers. The latest hardened branch commits are the source for this support; unrelated Flash Board content and legacy raster fallbacks are excluded.

Each migrated package will contain exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`. Its PNG and canonical 2D `holdGeometry` are removed. The new Nature package follows the same model-only tree. No model package may retain a raster fallback, standalone duplicate model resource, generated path cache, or undeclared asset.

The model display camera will be orthographic and bound to the package's validated bounds. SceneKit loading must remain asynchronous and cached, with cloned materials for independent selection highlights, stable accessibility identifiers, correct preview/active/cleared highlight behavior, and an explicit unavailable state for invalid runtime assets. Cord rendering or routing must use the Nature package's two external branch markers and its declared unknown hidden route; it must not invent a central attachment or unsupported tunnel geometry. Branch validation must reject repeated endpoints, non-closure contacts, impossible/self-intersecting paths, and invalid marker/order data.

## Source and fidelity boundaries

The ZIP README, package manifests, hold maps, evidence snapshots, validation reports, and model hashes are retained under workspace-owned `.context` output or the board's source audit as appropriate. Manufacturer facts remain distinct from estimated display geometry. Mounting holes, screws, hardware, logos, and hidden cord routing are deliberate display omissions unless the supplied package explicitly models a supported visible marker. The model is display geometry, not manufacturing CAD or a source for new training prescriptions.

## Validation and review

Before promotion, each package must pass:

1. source/package inventory and exact-asset validation;
2. descriptor-to-USDZ hash, node-role, logical-inventory, bounds, and material validation;
3. actual USDZ reimport with source materials removed, including triangle/material continuity checks;
4. native SceneKit picking checks for every mapped contact and a body/non-contact probe;
5. the repository board-package tests and the relevant Hang Ten XCTest/build checks;
6. human visual review of matched front, oblique, clay/detail, and selected-highlight views.

The final audit must list every ZIP source, mapping decision, omitted feature, unresolved source claim, validation command/result, and any cord-branch code imported from `load/3d-hangboard-models`. Existing board-specific routines and saved board identities must continue to resolve against the preserved logical IDs.
