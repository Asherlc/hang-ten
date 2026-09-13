# Apple On-Demand Resources for board models

Hang Ten ships each model-only board's `assets/primary.usdz` through an Apple
On-Demand Resources (ODR) tag named `hang-ten-model-<package-slug>`. The base
app keeps every package's `board.json` and `assets/primary.model.json`, so the
catalog and descriptor can be validated before model access begins. There is
no raster, GitHub, or custom-server fallback.

ODR reduces the initial app bundle downloaded to a device. It does not remove
the models from the release submission: Xcode includes the asset packs in the
archive/upload, and App Store Connect hosts and distributes them with the app.

## Build setup

The `Stage Board Packages` phase first validates the complete canonical source
packages, including the presence, format, and descriptor SHA-256 binding of
each USDZ. It then produces two build-only trees:

- `${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}/Hangboards` holds
  normal base resources and omits only model USDZ files.
- `${DERIVED_FILE_DIR}/HangTenModelODR/<slug>/Hangboards/<slug>/assets` holds
  that package's unchanged `primary.usdz` for Xcode's tagged folder reference.

Each generated `Hangboards` folder reference has exactly one ODR tag in
`HangTen.xcodeproj/project.pbxproj`. Keeping the folder reference rooted at
`Hangboards` preserves the runtime path
`Hangboards/<slug>/assets/primary.usdz` inside every asset pack.

The Debug target sets `EMBED_ASSET_PACKS_IN_PRODUCT_BUNDLE = YES` so local and
Simulator builds can serve their asset packs without an external host. Release
enables ODR but deliberately does not set an asset-pack URL prefix or embed
asset packs in the product bundle; App Store distribution therefore uses
Apple's default hosting.

At runtime, `BoardModelResourceAccess` creates a fresh
`NSBundleResourceRequest` for the package tag, waits for successful access,
then resolves the model from the main bundle. The request remains retained by
the loaded model scene and ends when that scene leaves the view/cache
lifecycle. Request, path, hash, or SceneKit failures all produce the existing
explicit unavailable state.

Apple references:

- [Creating and assigning ODR tags](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/On_Demand_Resources_Guide/Tagging.html)
- [Accessing and downloading ODR](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/On_Demand_Resources_Guide/Managing.html)
- [App Store Connect ODR size limits](https://developer.apple.com/help/app-store-connect/reference/app-uploads/on-demand-resources-size-limits)

## Release verification

1. Run the canonical package validator and the focused staging tests. Missing,
   malformed, extra, or hash-mismatched source assets must still fail before
   any build resource tree is installed.
2. Build Debug and inspect `HangTen.app/Hangboards`: descriptors and
   `board.json` files must be present, with no `primary.usdz` beneath that base
   directory. Inspect `HangTen.app/OnDemandResources`: there must be one asset
   pack per model tag, each containing only its exact
   `Hangboards/<slug>/assets/primary.usdz` hierarchy.
3. Archive Release without `EMBED_ASSET_PACKS_IN_PRODUCT_BUNDLE` and without
   `ASSET_PACK_MANIFEST_URL_PREFIX`. Confirm the archive/export reports the
   expected ODR tags and asset packs before upload.
4. After App Store Connect finishes processing, verify that the build reports
   hosted ODR asset packs and that the initial app download excludes their
   bytes. Install through TestFlight, load more than one model repeatedly, and
   exercise offline and low-space failure paths; failed requests must show
   `3D model unavailable` and must never display a raster or remote fallback.
