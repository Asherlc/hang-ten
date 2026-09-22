# FreeCAD authoring — unverified prototype

**Status: incomplete; not ready to merge.** This directory does not yet provide
CAD authoring, conversion, or a working model compiler. `contract.py` is an
unverified source-preflight prototype and is not wired into the application or
existing model pipeline. No shipping models or `board.json` files were changed.

## Requested target

One self-contained `ModelSources/<package-directory>.FCStd` document per board,
plus the existing `Hangboards/<package-directory>/board.json`. A single shared
command should read those inputs and build the existing USDZ and hash-bound model
descriptor. No required Blender, GLB, or STEP intermediate, and no board-specific
Python authoring program.

The user requested branching from PR #458's simplified models. This branch was
created from `optimize/model-simplification-pilot-20260922` at
`6b828e156d4e14ec4a8aa0e3b8f17212336be7bc`. The parent branch and main were not
modified. The snapshot contains 40 model-media packages; only three were part of
#458's simplification pilot:

- `metolius-simulator-3d`
- `metolius-wood-grips-deluxe-ii`
- `lattice-mxedge-lift-small`

## Important migration distinction

Wrapping existing triangles in FreeCAD Part faces does **not** recover sketches,
constraints, feature history, analytic surfaces, or original manufacturing data.
Such documents must be explicitly classified as imported faceted geometry, not
presented as reconstructed parametric CAD. Native Part/Part Design/Sketcher
features are the intended authoring format for newly constructed models.

Do not bulk-promote a mesh-to-BRep conversion merely because the resulting file
opens. Check editing performance, actual geometry, contact boundaries, normals,
materials, and the regenerated runtime output. Preserve existing shape fidelity
and label unknown product measurements as unknown.

## What exists

`contract.py` sketches read-only ZIP/XML checks, an explicit builtin object-type
allowlist, checks for some external/executable properties, and body/contact/slot
binding validation. These checks have not been exercised against actual complete
board documents. They are not a security sandbox or an approved production
contract. Review the allowlist and property handling against native saved files
before relying on them.

## Work still required

1. Restore a working local execution environment with FreeCAD, its matching
   Python/OCCT libraries, OpenUSD, NumPy, and pytest. Pin the validated toolchain.
2. Write and run source-contract tests, including genuine FCStd save/reopen
   fixtures. Verify builtin feature support, embedded dependencies, malformed
   archives, external links, duplicate IDs, and descriptor-v2 reusable slots.
3. Implement native document loading/recomputation and direct CAD tessellation
   to USDZ. Preserve stable semantic node IDs and contact regions. Derive the
   descriptor from the actual reopened output. Do not use old USDZ bytes as a
   normal build input or hide an embedded runtime asset inside the CAD document.
4. Establish the source metadata/document contract. Keep application facts in
   `board.json`; store shape and geometric bindings in FCStd. Use explicit units
   and one tested basis conversion: native millimetres, +X right, +Z up, front
   -Y; runtime metres, +X right, +Y up, front +Z.
5. Prove a representative simplified model end-to-end before expanding. Reopen
   and recompute its native source, build twice from a clean environment, and
   check shape, winding, normals, materials, contact IDs, and deterministic
   output. Do not claim recovered parametric history for a faceted import.
6. Add the public one-command build interface, source inventory, Git LFS rules,
   and appropriate read-only CI. Keep generated outputs separate from authoring
   files, and prevent failed builds from partially replacing existing packages.
7. Run the existing model/package tests, relevant full repository tests, and
   native app rendering/picking checks. Record every failure or unavailable
   verification lane before promoting any runtime asset.

## Execution status

Local terminal and Python tools began consistently returning
`TransportTimeoutError`; even a minimal terminal health check failed. The
implementation could not be executed or verified after that failure. No passing
CAD test suite, source conversion, rendering, or application build is claimed.

Two temporary isolated setup workflows ran before the interruption. A native
FreeCAD environment smoke test succeeded, but it did not validate this code or
convert a repository board. The temporary workflow and unfinished remote test
scaffold were removed. Setup artifacts were configured with seven-day retention.
Do not use hosted CI as a replacement development shell when local execution is
unavailable; continue the implementation in a working local execution session.
