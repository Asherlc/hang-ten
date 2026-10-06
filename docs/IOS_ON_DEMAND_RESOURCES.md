# Apple On-Demand Resources for board models

Hang Ten ships each model board's declared `assets/*.usdz` through an Apple
On-Demand Resources (ODR) tag named `hang-ten-model-<package-slug>`. The base
app keeps every package's `board.json`, model descriptors and optional physics
metadata, so catalog validation can precede model access. There is
no raster, GitHub, or custom-server fallback.

ODR reduces the initial app bundle downloaded to a device. It does not remove
the models from the release submission: Xcode includes the asset packs in the
archive/upload, and App Store Connect hosts and distributes them with the app.

## Build setup

Before Xcode, run `rtk proxy bash scripts/build-runtime-assets.sh` from a checkout
with its Git LFS sources fetched. Native board USDZ, model descriptors, and
optional physics descriptors and `assets/suspension.json` are ignored build
outputs; `board.json` is generated from the manifest in flat
`Hangboards/<slug>.FCStd` and validated generated suspension during staging.
The FCStd also embeds cord/simulation authoring inputs; it is never staged.
CI consumers download these runtime files from the producer artifact.
See [generated artifacts](GENERATED_ARTIFACTS.md).

The `Stage Board Packages` phase first validates the complete compiled
packages, including the presence, format, and descriptor SHA-256 binding of
each USDZ. It then produces two build-only trees:

- `${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}/Hangboards` holds
  generated `board.json`, descriptors and optional physics. The standalone
  generated suspension artifact is merged into `board.json`, then omitted.
- `${DERIVED_FILE_DIR}/HangTenModelODR/<slug>/Hangboards/<slug>/assets` holds
  that package's unchanged declared USDZs for Xcode's tagged folder reference.

Each generated `Hangboards` folder reference has exactly one ODR tag in
`HangTen.xcodeproj/project.pbxproj`. Keeping the folder reference rooted at
`Hangboards` preserves the runtime path
`Hangboards/<slug>/assets/<model>.usdz` inside every asset pack. A package with
several model presentations keeps them under the same package tag.

The Debug target sets `EMBED_ASSET_PACKS_IN_PRODUCT_BUNDLE = YES` so local and
Simulator builds can serve their asset packs without an external host. Release
enables ODR but deliberately does not set an asset-pack URL prefix or embed
asset packs in the product bundle; App Store distribution therefore uses
Apple's default hosting.

At runtime, `BoardModelResourceAccess` creates a fresh
`NSBundleResourceRequest` for the package tag, waits for successful access,
then resolves the model from the main bundle. Its lease remains retained during
loading and scene use and balances access on release. DEBUG Simulator builds
may resolve the packaged ODR file directly when the installer has not registered
its nested asset pack. Request, path, hash, or RealityKit/ModelIO failures produce
the explicit unavailable state.

Suspension is bundled metadata rendered as transient geometry, so a loaded
model's missing cord is diagnosed in [the suspension guide](3D_SUSPENSION_AND_ODR.md).
Android staging keeps the same USDZs inline in generated packages.

Apple references:

- [Creating and assigning ODR tags](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/On_Demand_Resources_Guide/Tagging.html)
- [Accessing and downloading ODR](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/On_Demand_Resources_Guide/Managing.html)
- [App Store Connect ODR size limits](https://developer.apple.com/help/app-store-connect/reference/app-uploads/on-demand-resources-size-limits)

## Release verification

1. Generate the runtime files, then run the canonical package validator and the focused staging tests. Missing,
   malformed, extra, or hash-mismatched source assets must still fail before
   any build resource tree is installed.
2. Build Debug and inspect `HangTen.app/Hangboards`: descriptors and
   `board.json` files must be present, with no USDZ beneath that base
   directory. Inspect `HangTen.app/OnDemandResources`: there must be one asset
   pack per model tag, containing only its declared models under
   `Hangboards/<slug>/assets/`.
3. Archive Release without `EMBED_ASSET_PACKS_IN_PRODUCT_BUNDLE` and without
   `ASSET_PACK_MANIFEST_URL_PREFIX`. Confirm the archive/export reports the
   expected ODR tags and asset packs before upload.
4. After App Store Connect finishes processing, verify that the build reports
   hosted ODR asset packs and that the initial app download excludes their
   bytes. Install through TestFlight, load more than one model repeatedly, and
   exercise offline and low-space failure paths; failed requests must show
   `3D model unavailable` and must never display a raster or remote fallback.
