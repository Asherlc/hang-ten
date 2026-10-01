# Evo, Honestone and Original Grindstone native CAD delivery — 2026-09-29

This batch migrates only `yy-verticalboard-evo` (25 contacts),
`tension-honestone` (15), and `tension-grindstone-original` (12).
The distinct Grindstone Mk2 and Pro revisions are unchanged. All 52 original
contact dictionaries and all non-presentation factual metadata match the
baseline exactly. No training content changes.

The exact retained, hash-bound visual evidence received explicit human approval
before native authoring; see [evidence approval](2026-09-29-next-three-cad-evidence.md).
Original Grindstone uses explicitly labeled Northern Rocks archival commerce
photographs because the retired manufacturer photograph is unavailable.

## Sources and geometry

- [Evo source audit](2026-09-29-yy-evo-cad.md): constrained native sketches,
  rounded/scalloped tiers, real blind and inclined pockets, five sourced ramps,
  through handle, and 25 live contact binders.
- [Honestone source audit](2026-09-29-honestone-cad.md): constrained native loft
  sections, four compound stepped cavities, real 10° incut center floor,
  sourced lower lip radius, variable macro slopers, and 15 live contacts.
  Right-side physical bindings correct the legacy raster's reversed depth order.
- [Original Grindstone source audit](2026-09-29-original-grindstone-cad.md):
  constrained native tiers and pockets, eleven blind backed cavities, a through
  50 mm center cavity, a noncontact phone slot, and twelve live contacts.

Published values remain distinct from documented estimated display dimensions.
Mounting hardware, engraving and materials are omitted. FCStd files are the
editable sources; metadata is embedded with `set_board_manifest.py` and
`board.json` is generated only at build time. Raster media and committed JSON
fallbacks are removed. There are no frozen imported geometry features.

## Integration and verification

Apple ODR registers the USDZ alone for each board. DEBUG simulator staging
copies those exact models into `HangTenDebugSimulatorModels`. Android stages
all package runtime assets. Both platforms receive generated metadata and the
same descriptors, with no CAD authoring source or raster fallback.

Independent OpenUSD reopen checks find 26/16/13 unbound mesh nodes, respectively,
zero Material/Shader prims and zero material bindings. Descriptor model hashes
match the shipped USDZ files. Full inventory validation and Android/iOS/ODR
staging parity pass.

Native regression tests reopen and recompute every source, inspect constrained
sketches and physical cavities, and persist real depth edits through save/reopen.
The RealityKit regression loads all 52 exact contacts and requires their model,
collision and input-target components. Simulator review shows selected contacts
highlighted on each of the three actual models.

Independent fresh-process rebuilds on FreeCAD 1.1.3 and the pinned OpenUSD
toolchain pass for all three packages: USDZ bytes match exactly, descriptors
match, and each descriptor binds its shipped asset hash. Source bytes remain
unchanged. Python CI-equivalent validation passes: **489 passed, 11 optional native-export
checks skipped, 24 subtests passed**. All three new native source-edit regressions
run in that suite; their independent pinned export checks are recorded above.
The model/package-only suite separately passes **420 tests, 1 skipped,
24 subtests**. The optional catalog-wide rebuild was stopped after fixture and
dependency updates invalidated its original collection; it is not claimed.

A read-only independent integration review found no important or critical
issues. The full Swift unit suite passes: **1,234 tests, 3 skipped, zero failures**
on a dedicated iPhone 17 Pro / iOS 26.5 simulator. The 52-contact regression
also checks that each collision entity resolves to its exact logical contact ID.
The final Xcode build passes, as do the source-boundary checks.

Shared delivery-lock integration remains pending: PR524 is still queued on
GitHub macOS CI with auto-merge enabled. The final lock must include it through
refreshed `origin/main`. Earlier cold foreground-launch attempts encountered
SpringBoard FrontBoard semaphore collisions; direct test-host launch completed
the full suite. No shared runtime or unknown resource was reset or removed.

## Visual review artifacts

Workspace-owned review output is under `.context`:

- `supreme-zebra-next-cad-evo/previews/evo-prior-vs-cad.png`
- `supreme-zebra-next-cad-honestone/honestone-comparison.png`
- `supreme-zebra-next-cad-grindstone/previews/prior-comparison.png`
- `supreme-zebra-next-cad-validation/ios-yy.verticalboard-evo-center-handle.png`
- `supreme-zebra-next-cad-validation/ios-tension.honestone-edge-20-left.png`
- `supreme-zebra-next-cad-validation/ios-tension.grindstone-original-edge-50-center.png`

Front, side and top comparisons were presented beside the prior committed front
rasters, followed by in-app screenshots. The prior packages had no 3D side/top
assets, and those missing views are explicitly labeled. All seven source
photographs remain committed in the adjacent evidence directory.

Generated artifacts are workspace-owned. Simulator runs register exact UUIDs
before boot, install cleanup traps, and verify deletion. No HTTP server is used.
This batch must not be merged without a separate explicit user request.
