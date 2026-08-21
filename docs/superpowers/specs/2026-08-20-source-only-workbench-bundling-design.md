# Source-only Hangboard Workbench bundling

## Goal

The Workbench browser bundle (`Tools/HangboardWorkbench/app.js`) is generated
from TypeScript source and must not be committed. CI and release packaging must
prove that the bundle can be generated from the checked-out source, then use
that ephemeral artifact to test and package the Workbench.

## Current problem

`app.js` is checked in and `check:bundle` rebuilds it before failing whenever
the working tree differs. This makes a source-only change fail CI until a
generated file is committed. The release package does need `app.js`, because
the Python server and PyInstaller manifest serve/embed it, but it only needs
the file in the build workspace—not in Git.

## Design

### Bundle ownership

- Remove the tracked `Tools/HangboardWorkbench/app.js` file and add that exact
  path to `.gitignore`.
- Keep the current `npm run build` output path (`app.js`) so the server,
  `workbench_assets` manifest, and PyInstaller data manifest retain their
  existing runtime contract.
- Treat this file as a workspace-local build input. It is regenerated from
  `src/main.tsx` before any operation that serves, tests, or packages static
  Workbench assets.

### NPM scripts and developer workflow

- Change `check:bundle` from a Git-diff freshness assertion to a source build
  verification: it runs the production bundle build and succeeds only if
  esbuild succeeds.
- Preserve the existing test commands. Documentation will state that commands
  which exercise the Python static-file server or package the app require
  `npm ci && npm run check:bundle` first.
- Update the Workbench README verification sequence to build the bundle before
  running the Python suite or local server/package workflow. No runtime server
  will invoke npm automatically.

### CI and release packaging

- The existing JavaScript PR and release jobs continue to run `npm ci`, tests,
  and `check:bundle`; the latter now validates buildability without requiring a
  Git diff to be clean.
- Before each independent Python test job, install the pinned Node version,
  run `npm ci`, and run `npm run check:bundle`. This gives server and packaging
  tests the same generated asset that a real build uses.
- The shared macOS `build-hangboard-workbench` action installs Node dependencies
  and runs `npm run check:bundle` before invoking the Python PyInstaller build.
  PyInstaller then embeds the generated, untracked `app.js` under the existing
  `/app.js` runtime route.
- Generated bundle files remain in the runner/worktree only; neither CI nor
  release automation writes them back to Git.

## Error handling

- A failed esbuild invocation fails the job before Python tests or packaging,
  exposing the TypeScript/bundle error directly.
- The server and packaging validation keep treating a missing `app.js` as a
  required-runtime-input error. Locally, that clearly tells an operator to run
  the documented bundle command rather than silently serving stale source.

## Verification

- Add/adjust tests for the new bundle-check contract so it no longer asserts a
  clean Git diff.
- Run the JavaScript test suite, Python Workbench suite after bundle creation,
  and the relevant packaging/workflow tests.
- Validate that `git status` stays clean after each verification build because
  `app.js` is ignored.
- Confirm the CI workflow definitions build the bundle in every independent
  job that serves or packages static assets.

## Non-goals

- No dynamic runtime bundling in the Python server.
- No change to the `/app.js` public route or the packaged Workbench asset
  layout.
- No generated artifact commits.
