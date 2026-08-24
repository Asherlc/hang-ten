# Hangboard Workbench

Hangboard Workbench edits direct board packages. The packaged macOS app is the
only local-checkout editor; browser-hosted deployments use GitHub-backed storage.
It discovers completed boards, opens the primary image and hold geometry together,
edits hold contours, validates the package, and saves the result atomically.

## Run as a hosted editor

From the repository root:

```sh
cd Tools/HangboardWorkbench && npm ci && npm run check:bundle
cd ../..
rtk python3 Tools/HangboardWorkbench/server.py \
  --allow-remote \
  --github-client-id <id> \
  --github-client-secret <secret> \
  --session-secret <secret>
```

The local server and package operations require the generated UI bundle. Run
`npm ci && npm run check:bundle` in `Tools/HangboardWorkbench` before those
operations.

For a different deployment checkout, provide its root explicitly:

```sh
rtk python3 Tools/HangboardWorkbench/server.py \
  --repository-root /absolute/path/to/hang-ten \
  --host 0.0.0.0 \
  --port 4173 \
  --allow-remote \
  --github-client-id <id> \
  --github-client-secret <secret> \
  --session-secret <secret>
```

Host this process with HTTPS in front (for example via a reverse proxy or your
provider’s platform TLS), then point browsers to your public URL.
`--allow-remote` is required for the browser server. It uses GitHub OAuth and
GitHub-backed board storage, so each **Save** creates a GitHub commit on the
selected branch. See "Repository workflow actions from the editor UI" below
for how to set up the OAuth App.

### Repository workflow actions from the editor UI

From the hosted editor toolbar you can:

- Switch branches.
- Create a branch from the current branch.
- Save directly to the selected GitHub branch.
- Open a pull request using the authenticated GitHub session.

The packaged macOS app is the only supported local-checkout workflow. Its
**Save** action writes to the chosen checkout; commit and push remain explicit
Git review steps.

Hosted deployments (`--allow-remote`) instead require a GitHub OAuth App:
start the server with `--github-client-id` and `--github-client-secret` to
enable browser-based login. Once a user logs in, `git push` and
`gh pr create` automatically use that user's GitHub token instead of any
server-side `gh` credentials, and expired or insufficient-permission tokens
surface as a 401 asking the user to log in again.

To set up a GitHub OAuth App:
1. On GitHub, go to **Settings > Developer settings > OAuth Apps** and register a new app.
2. Set its callback URL to `http://<your-host>/auth/callback`.
3. Start the server with `--allow-remote --github-client-id <id> --github-client-secret <secret>`.

Security note: hosted saves write to GitHub under the authenticated user's
session. Place the deployment behind appropriate access controls.

## Board packages

Every direct child of `Hangboards/` containing `board.json` is a completed
package. Its exact inventory is `board.json` plus `assets/primary.png`; there
is no root registry or package sidecar. A direct child containing only
`assets/primary.png` is a migration draft and is excluded from the editor.

Each physical hold has one identifier and one or more geometry pieces embedded
in `board.json`; each piece has one closed, contiguous contour. The editor
exposes each piece under a stable `<hold-id>-piece-<index>` key, and runtime
bounds are the union of all pieces belonging to the physical hold.
`aspectRatio` is the primary PNG's pixel width divided by height and must match
the decoded image within 0.1% relative error.

Save validates the complete package before replacing it. Invalid geometry,
invalid image data, or an interrupted write leave the saved package unchanged.

## Capture a visual catalog

The catalog capture command starts an isolated loopback Workbench server and a
headless Chrome DevTools session. It opens each completed board through the
editor, waits for its primary image and SVG regions, then captures the unchanged
`#editor-svg` surface at a fixed viewport.

```sh
rtk python3 Tools/HangboardWorkbench/capture_catalog.py \
  --repository-root /absolute/path/to/hang-ten \
  --output-root /absolute/path/to/catalog-captures \
  --chrome-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --port 4173
```

The output includes one labeled PNG per board, an API-order `manifest.json`,
and a labeled `contact-sheet.png`. It uses a dedicated capture-only loopback
launcher rather than the browser-hosted server, then terminates its Chrome and
server children before returning.

## Outline shape constraints

The **Outline shape** picker reflects the selected geometry piece and offers
**Custom**, **Oval**, **Circle**, **Pill**, **Rounded rectangle**, and
**Rectangle**. Choosing a preset replaces that piece's outline with the exact
primitive and keeps the selection constrained as it is moved, rotated, and
resized. Constrained outlines use a shape-aligned box with eight handles: edge
handles resize one dimension and corner handles resize both. Circles retain a
1:1 aspect ratio during either kind of resize.

Choosing **Custom** removes the constraint without changing the current
outline, then restores point and Bezier-control editing. Saving persists the
selected constraint and orientation in `board.json`, so the same picker state
and constrained handles return when the package is reopened.

A geometry piece may include this optional object alongside its existing
`frame` and `shape`:

```json
"shapeConstraint": {
  "shape": "oval",
  "rotationDegrees": 15
}
```

`shape` must be exactly one of `oval`, `circle`, `pill`, `roundedRectangle`, or
`rectangle`. `rotationDegrees` must be a finite number normalized to the
half-open range `[-180, 180)`. Omitting `shapeConstraint` means the piece is
Custom/freeform. The existing `frame` and `shape` remain the authoritative
rendering geometry, including position and size; `shapeConstraint` records only
the geometric invariant and its orientation.

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

On first launch the native window asks you to **Choose Local Repository…**.
The app remembers the last valid checkout and uses the selected checkout on
later launches; choose **Choose Another Local Repository…** from the app menu to
switch. All edits remain ordinary local Git changes for normal Git review.

Local editor users can continue to use the packaged app; hosted deployment uses
an opt-in server mode (`--allow-remote`) of the same Workbench codebase.

## Verification

```sh
(
  cd Tools/HangboardWorkbench
  npm ci
  npm run check:bundle
  npm run typecheck
  npm test
)
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
swift test --package-path Tools/HangboardWorkbench/macos
```
