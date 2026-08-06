# Hangboard Onboarding Tooling Design

Hang Ten will own the staged hangboard-onboarding pipeline as repository-local
developer tooling. The Swift app remains deterministic and vector-driven at
runtime; generated raster and SVG artifacts are calibration evidence used to
author and validate `BoardDesign` geometry, not runtime overlays.

The existing `hangboard-vectorizer` Python project will be vendored without
semantic changes under `Tools/HangboardOnboarding`. Its accepted Metolius Wood
Grips Compact II run will be stored under `reference/` so the token-efficient
semantic replay can prove the same 19-region inventory, Stage 3 geometry, and
Stage 4 highlight pixels with zero model calls. A repository script will create
an isolated virtual environment under `.context/` and dispatch any of the three
tool commands.

`docs/ADDING_A_BOARD.md` will describe the staged workflow and make its output
contract explicit: review each stage image, keep generated runs in `.context/`,
then translate accepted normalized paths into the Swift board design while
preserving stable hold IDs and the shared render/highlight/hit-test path.

Verification consists of the accepted Metolius cache-only parity benchmark,
the vendored Python test suite, and the existing iOS build. The integration does
not add Python to the shipped app target or alter Xcode project membership.
