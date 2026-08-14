# Hangboard Workbench

Hangboard Workbench is the local authoring suite for direct board packages.
It lists registered boards, opens the primary image and hold geometry together,
edits hold contours, validates the package, and saves the result atomically.

## Run from a checkout

From the repository root:

```sh
rtk python3 Tools/HangboardWorkbench/server.py
```

Open `http://127.0.0.1:4173`. The **Boards** button lists the registered
packages in `Hangboards/`. Selecting a board loads its image and all of its
holds. **Save** writes directly to that board package; it does not commit or
push your Git changes.

For a different checkout, provide its root explicitly:

```sh
rtk python3 Tools/HangboardWorkbench/server.py \
  --repository-root /absolute/path/to/hang-ten
```

## Board packages

`Hangboards/catalog.json` registers each package. A registered package has
`board.json`, `artwork.json`, `evidence.json`, `semantics.json`, and
`assets/primary.png`.

Each physical hold has exactly one identifier and one closed, contiguous contour
in `artwork.json`. Decorative artwork is not hold geometry. The frame in
`board.json` is derived from that contour.

Save validates the complete package before replacing it. Invalid geometry,
missing evidence, invalid image data, or an interrupted write leave the saved
package and catalog unchanged.

## Run the Apple Silicon macOS release

Download the workbench ZIP and its checksum from a release, verify the
checksum, extract it, then open the app:

```sh
curl -LO https://github.com/Asherlc/hang-ten/releases/download/<release>/hangboard-workbench-macos-arm64.zip
curl -LO https://github.com/Asherlc/hang-ten/releases/download/<release>/hangboard-workbench-macos-arm64.sha256
shasum -a 256 -c hangboard-workbench-macos-arm64.sha256
unzip hangboard-workbench-macos-arm64.zip
open "Hangboard Workbench.app"
```

On first launch the native window asks you to **Choose Hang Ten Checkout…**.
The app remembers the last valid checkout and uses the selected checkout on
later launches; choose **Choose Another Checkout…** from the app menu to
switch. All edits remain ordinary local Git changes for normal Git review.
Remote hosting is not yet shipped.

## Verification

```sh
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
node --test Tools/HangboardWorkbench/tests/workbench*.test.js
swift test --package-path Tools/HangboardWorkbench/macos
```
