# Hangboard Workbench Binary Release Design

**Date:** 2026-08-08

## Goal

Distribute the repository-backed hangboard workbench as a self-contained Apple
Silicon macOS executable. A user with a Hang Ten checkout must be able to
download the release artifact, extract it, run it from the checkout, and use the
workbench without installing Python, Node, OpenCV, NumPy, Pillow, Requests, or
any other application dependency.

Every push to `main` must build, verify, and publish an immutable GitHub Release
for the exact source commit. A failed build or smoke test must not publish a
release.

## Scope

This change packages the existing workbench UI and server. It does not change
the visual pipeline, geometry algorithms, board schemas, publication contract,
or protected board artifacts. All processing remains programmatic,
product-neutral, and identical to the source-run workbench.

The first release target is Apple Silicon macOS (`arm64`). Intel macOS, Linux,
Windows, Apple Developer signing, and notarization are outside this version.

## User Contract

The release contains:

- `hangboard-workbench-macos-arm64.tar.gz`, containing one executable named
  `hangboard-workbench`;
- `hangboard-workbench-macos-arm64.sha256`, containing the archive checksum.

The executable is launched from inside a Hang Ten checkout:

```bash
./hangboard-workbench
```

It discovers the repository from the current directory, stores unfinished work
under `.context/hangboard-workbench/`, reads and writes canonical boards under
`Tools/HangboardOnboarding/boards/`, starts the server on
`127.0.0.1:4173`, and opens the workbench in the default browser after the
server is ready.

The packaged entrypoint supports the existing server overrides:

- `--repository-root`
- `--workspace-root`
- `--host`
- `--port`
- legacy `--run-dir` and `--catalog` inputs

It adds `--no-open` for automated and terminal-only use and `--version` to
print the source commit embedded at build time. Running the server directly
from source preserves its current browser-opening behavior; automatic browser
launch is a packaged-entrypoint responsibility.

The checkout remains required because the workbench deliberately edits the
same Git-versioned board repository. The runtime dependency installation does
not.

## Runtime Architecture

### Packaged entrypoint

A small Python entrypoint owns packaged startup. It:

1. parses only packaged-only flags before forwarding the existing server flags;
2. resolves frozen UI and package resources through one explicit resource-root
   abstraction;
3. creates the existing workbench HTTP server without duplicating routes or
   workflow logic;
4. starts the server, waits until it is listening, and opens the browser unless
   `--no-open` is present;
5. prints the URL when browser opening fails and continues serving;
6. shuts down cleanly on `SIGINT` or `SIGTERM`.

The source server and packaged entrypoint share the same server factory. The
entrypoint must not create an alternate API, persistence layer, or board path.

### Resource resolution

Static editor files and Python package data cannot rely on repository-relative
`__file__` paths inside a frozen executable. Resource lookup therefore accepts
an explicit editor root, using the checked-in editor directory for source runs
and the PyInstaller extraction root for frozen runs.

The frozen build explicitly includes:

- editor HTML, CSS, and JavaScript runtime files;
- the complete `hangboard_vectorizer` package needed by the workbench;
- package data declared by `hangboard_vectorizer.evidence` and
  `hangboard_vectorizer.products`.

Tests, evaluation fixtures, reference runs, committed board packages, `.git`,
and `.context` are not embedded. Published boards are always read from the
checkout selected at runtime.

### Python imports

The packaged application imports `hangboard_vectorizer` as an installed
package. Development mode may add the repository `src` directory to
`sys.path`, but that fallback must be isolated from the frozen path. Packaging
must not depend on a source tree existing beside the executable.

## Packaging

PyInstaller produces a one-file, arm64 Mach-O executable using a checked-in,
pinned build configuration. The build environment installs the onboarding
project and a pinned PyInstaller version into an isolated environment before
building.

The configuration declares all static resources and hidden imports rather than
depending on accidental module discovery. It also embeds a generated build
metadata module containing the exact Git commit. Build metadata is reproducible
for the same source commit and does not modify tracked source files.

The executable is archived with `tar.gz` so its executable mode survives
download. CI computes SHA-256 over the final archive, and the checksum filename
matches the release asset exactly.

PyInstaller one-file mode extracts native libraries to a temporary directory
at startup. This is an accepted tradeoff for providing one executable. All
temporary extraction is owned by PyInstaller and must not be confused with the
workbench's persistent `.context` workspace.

## Continuous Integration and Releases

A dedicated GitHub Actions workflow runs on every push to `main` and may also
be invoked manually for verification. It uses the standard native arm64
`macos-15` runner and grants `contents: write` only to the release job.

The workflow performs these ordered gates:

1. check out the exact commit;
2. install the pinned build environment;
3. run the focused Python and Node workbench test suites;
4. build the arm64 executable;
5. verify the Mach-O architecture is `arm64`;
6. run `--version` and require the exact checked-out commit;
7. launch the executable with `--no-open` on an isolated port against the CI
   checkout;
8. request both a static UI asset and `/api/library` successfully;
9. stop the process and verify the smoke-test log contains no startup failure;
10. create the archive and checksum;
11. publish the immutable GitHub Release.

The release tag is
`hangboard-workbench-main-<github-run-number>-<short-commit>`. The release title
includes the short commit and links back to the source SHA. The release is
marked as the latest release and contains only the archive and checksum.
Concurrency is serialized for the release workflow so two rapid `main` pushes
cannot race while assigning latest-release status. Earlier releases and tags
remain immutable.

Pull requests run the build and smoke-test gates without publishing a release.
This catches packaging regressions before merge while reserving release writes
for `main`.

## Failure Handling

- If repository discovery fails, startup exits nonzero with an actionable
  message explaining that the executable must be run inside a checkout or with
  `--repository-root`.
- If the port is occupied, startup exits nonzero and names the requested host
  and port without exposing unrelated filesystem paths.
- If the browser cannot open, the server remains active and prints the URL.
- If a required embedded asset is missing, startup fails before binding the
  server and names the logical asset, not a PyInstaller temporary path.
- If any CI test, architecture check, version check, or smoke test fails, the
  release step is skipped.
- The smoke-test process is stopped in an unconditional cleanup step so a
  failed request cannot leave a background process running on the runner.

## Testing

Focused unit tests cover:

- source and frozen resource-root selection;
- packaged-only argument parsing and forwarding;
- browser launch after server readiness;
- `--no-open` and browser failure behavior;
- embedded version reporting;
- missing-resource and missing-repository errors.

The existing Python and Node suites remain the regression boundary for
workflow, repository, and editor behavior. The CI smoke test exercises the
actual frozen executable, native OpenCV import, static assets, server routing,
repository discovery, and clean shutdown.

## Documentation

The workbench README gains a binary quick start, checksum verification command,
the requirement to run inside a checkout, the available flags, and a brief
Gatekeeper note for unsigned downloads. Source-development commands remain
documented separately.

## Acceptance Criteria

- A clean Apple Silicon Mac can run the released executable from a Hang Ten
  checkout without installing application dependencies.
- The browser UI can list the checkout's canonical boards and create/edit work
  using the same repository and workspace paths as the source server.
- The executable contains no committed board packages or product-specific
  packaging logic.
- `--version` identifies the exact release source commit.
- CI builds and smoke-tests the executable on pull requests.
- Every successful push to `main` publishes one immutable release with a
  checksum; failed pushes publish none.
- Existing workbench tests pass and protected board visual hashes remain
  unchanged.
