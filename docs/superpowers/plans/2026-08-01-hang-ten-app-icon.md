# Hang Ten App Store Icon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register the approved close-cropped hand-on-highlighted-hold artwork as Hang Ten's 1024x1024 App Store icon and verify that Xcode compiles it into the app.

**Architecture:** Add one universal iOS marketing image to a new `AppIcon.appiconset`, then explicitly point the Debug and Release targets at that asset catalog. No SwiftUI, runtime, board model, or existing image assets change.

**Tech Stack:** Xcode asset catalogs, PNG, `sips`, `xcodebuild`, Xcode project build settings.

## Global Constraints

- Use the approved final preview as the source: `/Users/asherlc/.codex/generated_images/019fc0a6-4db9-7c73-8e16-09dd5c3da72a/exec-44531cb7-b2ce-45b8-ab00-9daf80209e8c.png`.
- The committed icon must be exactly 1024x1024 pixels and named `AppIcon-1024.png`.
- Preserve the deep evergreen field, faithful Compact II silhouette, localized warm-cream hand, and exactly one red-orange lower-center hold.
- Do not add a wristband, forearm, extra orange object, text, watermark, scenery, or extra app-icon variants.
- Do not modify the existing board imagery, runtime UI, color definitions, bundle identifier, or deployment target.
- Configure the Xcode asset for the App Store marketing slot; a signed App Store Connect upload remains dependent on the project's Apple credentials and is not performed by this local asset change.

## File Map

- Create: `HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png` — canonical App Store artwork.
- Create: `HangTen/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json` — Xcode asset metadata for the 1024px marketing icon.
- Modify: `HangTen.xcodeproj/project.pbxproj` — set `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon` in Debug and Release target settings.
- Test: the Xcode build and asset-dimension checks below; no Swift test file is needed for a static asset registration.

---

### Task 1: Stage the approved 1024px artwork

**Files:**
- Create: `HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png`

**Interfaces:**
- Consumes: the approved generated PNG at the source path in Global Constraints.
- Produces: a square 1024x1024 PNG ready for Xcode's `ios-marketing` slot.

- [ ] **Step 1: Confirm the approved source dimensions and format**

Run:

```bash
sips -g pixelWidth -g pixelHeight -g format \
  /Users/asherlc/.codex/generated_images/019fc0a6-4db9-7c73-8e16-09dd5c3da72a/exec-44531cb7-b2ce-45b8-ab00-9daf80209e8c.png
```

Expected: a square PNG source whose artwork matches the approved close crop.

- [ ] **Step 2: Copy and normalize the source into the asset catalog**

Run:

```bash
cp /Users/asherlc/.codex/generated_images/019fc0a6-4db9-7c73-8e16-09dd5c3da72a/exec-44531cb7-b2ce-45b8-ab00-9daf80209e8c.png \
  HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
sips -z 1024 1024 \
  HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
```

Expected: the target file exists as a 1024x1024 PNG without changing any
other asset.

- [ ] **Step 3: Re-check the committed image dimensions**

Run:

```bash
sips -g pixelWidth -g pixelHeight -g format \
  HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
```

Expected: `pixelWidth: 1024`, `pixelHeight: 1024`, and `format: png`.

- [ ] **Step 4: Commit the binary asset**

Run:

```bash
git add HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
git commit -m "Add Hang Ten App Store icon artwork"
```

---

### Task 2: Register the App Store icon asset

**Files:**
- Create: `HangTen/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json`

**Interfaces:**
- Consumes: `AppIcon-1024.png` from Task 1.
- Produces: an Xcode asset catalog named `AppIcon` with an `ios-marketing`
  1024x1024 image entry.

- [ ] **Step 1: Add the standard iOS marketing-icon metadata**

Create `Contents.json` with:

```json
{
  "images" : [
    {
      "filename" : "AppIcon-1024.png",
      "idiom" : "ios-marketing",
      "scale" : "1x",
      "size" : "1024x1024"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
```

- [ ] **Step 2: Validate the JSON and asset-catalog filename**

Run:

```bash
plutil -lint HangTen/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json
test -f HangTen/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
```

Expected: `OK` from `plutil` and a successful file existence check.

- [ ] **Step 3: Commit the asset metadata**

Run:

```bash
git add HangTen/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json
git commit -m "Register Hang Ten App Store icon asset"
```

---

### Task 3: Point both build configurations at `AppIcon`

**Files:**
- Modify: `HangTen.xcodeproj/project.pbxproj` in the HangTen target's Debug
  and Release `buildSettings` blocks.

**Interfaces:**
- Consumes: the asset catalog set named `AppIcon` from Task 2.
- Produces: Debug and Release builds that pass `AppIcon` to the asset catalog
  compiler.

- [ ] **Step 1: Add the app-icon build setting to Debug**

In the Debug target `buildSettings` block, alongside the existing generated
Info.plist and deployment settings, add:

```text
ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
```

- [ ] **Step 2: Add the same setting to Release**

In the Release target `buildSettings` block, add the identical line:

```text
ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
```

- [ ] **Step 3: Confirm both configurations resolve the same icon name**

Run:

```bash
xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug -showBuildSettings \
  | rg 'ASSETCATALOG_COMPILER_APPICON_NAME|CONFIGURATION'
xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Release -showBuildSettings \
  | rg 'ASSETCATALOG_COMPILER_APPICON_NAME|CONFIGURATION'
```

Expected: the Debug command and the Release command each report
`ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon`.

- [ ] **Step 4: Commit the target configuration**

Run:

```bash
git add HangTen.xcodeproj/project.pbxproj
git commit -m "Use Hang Ten AppIcon in all configurations"
```

---

### Task 4: Build-verify the App Store icon integration

**Files:**
- Test: `HangTen/Resources/Assets.xcassets/AppIcon.appiconset/` and the
  `HangTen` scheme build output.

**Interfaces:**
- Consumes: the complete `AppIcon` asset and build setting from Tasks 1–3.
- Produces: a successful simulator build with the icon compiled into the
  asset catalog.

- [ ] **Step 1: Run repository whitespace and status checks**

Run:

```bash
git diff --check origin/main...HEAD
git status --short
```

Expected: no whitespace errors; after the implementation commits,
`git status --short` is clean.

- [ ] **Step 2: Build the Debug simulator target**

Run:

```bash
xcodebuild -project HangTen.xcodeproj \
  -scheme HangTen \
  -sdk iphonesimulator \
  -configuration Debug \
  -derivedDataPath /tmp/hang-ten-app-icon-derived-data \
  build
```

Expected: `** BUILD SUCCEEDED **` and no asset-catalog error or missing
`AppIcon` warning.

- [ ] **Step 3: Inspect the final icon at thumbnail scale**

Use the repository image viewer on the committed PNG and confirm the board,
single highlighted pocket, and localized hand remain distinct when viewed
small. If the generated PNG is not square or the hand/hold has drifted,
stop before claiming completion and correct the asset rather than changing
runtime code.

- [ ] **Step 4: Report the App Store handoff boundary**

Report the committed asset path and build result. State that the Xcode project
is prepared for the App Store icon; do not claim an App Store Connect upload
unless an authenticated archive/upload actually succeeds.
