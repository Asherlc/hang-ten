# Hangboard Workbench

Hangboard Workbench is the local authoring suite for direct board packages.
It discovers completed boards, opens the primary image and hold geometry together,
edits hold contours, validates the package, and saves the result atomically.

## Run from a checkout

From the repository root:

```sh
rtk python3 Tools/HangboardWorkbench/server.py
```

Open `http://127.0.0.1:4173`. The **Boards** button lists the completed
packages in `Hangboards/`. Selecting a board loads its image and all of its
holds. **Save** writes directly to that board package; it does not commit or
push your Git changes.

For a different checkout, provide its root explicitly:

```sh
rtk python3 Tools/HangboardWorkbench/server.py \
  --repository-root /absolute/path/to/hang-ten
```

### Hosted server mode (same editor, remote access)

If you want to use Workbench through a hosted server without downloading
the app, run:

```sh
rtk python3 Tools/HangboardWorkbench/server.py \
  --repository-root /absolute/path/to/hang-ten \
  --host 0.0.0.0 \
  --port 4173 \
  --allow-remote
```

Host this process with HTTPS in front (for example via a reverse proxy or your
provider’s platform TLS), then point browsers to your public URL.
`--allow-remote` is intentionally opt-in, because it allows non-loopback clients.

### Repository workflow actions from the editor UI

From the hosted editor toolbar you can:

- Switch branches.
- Commit current repository changes with a message.
- Push the current branch to a remote (`origin` by default).
- Open a pull request from the current branch using the authenticated `gh` CLI.

The PR action expects `gh` to be available in the server environment and logged
into GitHub with permission to create pull requests. If `gh` is not available,
the `/api/git/open-pr` endpoint returns an explanatory 4xx error.

Security note: this still writes directly to the repository checkout. For
production use, place it behind authentication/authorization and only expose
trusted users.

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

Local editor users can continue to use the packaged app; hosted deployment uses
an opt-in server mode (`--allow-remote`) of the same Workbench codebase.

## Verification

```sh
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
node --test Tools/HangboardWorkbench/tests/workbench*.test.js
swift test --package-path Tools/HangboardWorkbench/macos
```
