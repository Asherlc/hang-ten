# Migrating a hangboard from USDZ to native CAD

How to replace a board's compiled runtime model with a self-contained parametric
FreeCAD source, then rebuild the runtime asset from that source.

Written for an agent or engineer picking this up cold. Everything here was
executed on this repository; commands are real.

## End state for a migrated board

```
Hangboards/<package>/<package>.FCStd      the canonical geometry source
Hangboards/<package>/board.json           logical/product metadata (unchanged)
Hangboards/<package>/assets/primary.model.json   descriptor, hash-bound
Hangboards/<package>/assets/primary.usdz  runtime asset (build output)
```

One shared command reads the FCStd plus `board.json` and writes the USDZ and the
descriptor. There must be no board-specific Python program in the build path, no
Blender/GLB/STEP/OBJ/STL step, and no hidden second geometry source. A temporary
script may *create* the document; the saved document must then stand alone.

The FCStd name must equal its package directory name. The package validator
rejects any other name, and rejects unknown entries in a package directory.

## Toolchain (pinned)

| Component | Version | Where |
| --- | --- | --- |
| FreeCAD | 1.1.3 | `/Applications/FreeCAD.app` (macOS dmg, sha256 `f5c0ece7cd7c932466d6effadc0fc6e179b0538a9d9a6a77a6769eae3af2667c`) |
| OCCT | 7.8.1 | bundled with FreeCAD |
| Python | 3.11.14 | `FreeCAD.app/Contents/Resources/bin/freecadcmd` |
| OpenUSD | 26.08 | `pip install --target <dir> usd-core==26.8` (that `<dir>` is `PXRPATH` below) |

The host-side Python tools need `pytest`, `usd-core`, `numpy`, and `pillow`:

```bash
python3 -m venv .env && .env/bin/pip install pytest usd-core==26.8 numpy pillow
```

Nothing in the build path imports FreeCAD from the host interpreter: FreeCAD work
always goes through `freecadcmd`, and `Tools/HangboardCAD/usdz_writer.py` never
imports FreeCAD at all, which is what lets the exporter be tested without it.

Two launcher quirks cost real time. Both are worked around in the existing
scripts, so reuse them rather than re-deriving:

1. **`freecadcmd` does not inherit `PYTHONPATH`.** Supply extras through
   `HANGTEN_CAD_PYTHONPATH` and have the script inject them into `sys.path`
   itself, as `compile_board.py` and the tests do.
2. **`freecadcmd` consumes unrecognised command-line options** before your script
   sees them, so `--package` never arrives. Embed the arguments in a generated
   wrapper script instead; see `Tools/HangboardCAD/tests/test_pilot_native.py`.

## The two contracts the source must satisfy

### Coordinate frame

Native is millimetres, +X right, +Z up, front -Y. Runtime is metres, +X right,
+Y up, front +Z. The conversion is applied exactly once:

```
(x, y, z) -> (x/1000, z/1000, -y/1000)
```

Normals get the same rotation **without** the 1/1000 factor. Applying the point
conversion to a normal emits unit-less vectors of magnitude 1e-3, which most
renderers hide by renormalising, so it will not show up visually.

### Bindings

Document properties (`App::PropertyString` / `Integer` / `Float`):

`HangTenBoardID`, `HangTenPresentationID`, `HangTenSchemaVersion` (1 or 2),
`HangTenSourceKind` (`native-parametric-measured-profile` or `faceted-import`),
`HangTenCoordinateFrame` (`freecad-mm-z-up-front-negative-y`),
`HangTenTessellationDeflection` (linear deflection in mm).

Each object you want exported carries `NodeID` (becomes the USD mesh prim name —
this is what the app binds against), `NodeRole` (`body`/`contact`/`attachment`),
`ContactID` (v1) or `ContactSlotID` (v2), `MaterialName`, `BaseColor`,
`Roughness`, `Metallic`, and optionally an embedded `TextureFile`. Objects
without `NodeID` — sketches, datums, construction features — are never exported.
`contract.inspect_archive` enforces a builtin-type allowlist and rejects Python
objects, external `XLink` references, and missing embedded files, so a document
that opens locally can still fail the contract.

## Procedure

### 0. Census before you choose

Do not trust a historical model count; enumerate at execution time.

```bash
ls Hangboards/*/assets/*.usdz | wc -l            # model-media boards
ls Hangboards/*/*.FCStd                          # already migrated
git log --all --diff-filter=A --name-only -- '*.glb'   # which boards have a GLB source
```

Most boards have **no** GLB or STEP source: their only geometry evidence is the
shipped USDZ. That is the common case, not the exception, so pick a pilot that
represents it.

### 1. Pick a board that can actually be rebuilt natively

Prefer one whose real geometry is expressible with native features. A
constant-cross-section part is ideal: one Sketcher profile plus a pad. Check the
approved asset before committing to a board:

```bash
# cross-section constancy: does the surface vary along the extrusion axis?
```

A board whose profile is genuinely organic can still be measured (below), but a
board that is a swept profile reproduces exactly.

### 2. Read the reference from Git — never from the live path

The compiler **overwrites** `Hangboards/<package>/assets/primary.usdz`. If your
migration script reads that path, it will silently compare the board against its
own output. Resolve the pre-migration bytes from the recorded commit instead:

```python
from reference import load_reference
path, digest = load_reference("lattice-triple-rung", "primary.usdz", scratch)
```

`reference.py` does `git show <commit>:<path>` and pipes it through
`git lfs smudge`, checking the resolved bytes against the object id the LFS
pointer declares. Record that commit and digest.

### 3. Measure, then author deliberately

Extract the profile as an ordered boundary loop of the reference's cross-section
and convert to native coordinates. Reduce it to the vertices you will author,
with a **stated tolerance and a measured achieved deviation**. On the pilot: 267
measured points reduced to 170 authored vertices, maximum deviation 0.1899 mm.

Keep published facts separate from measurements:

- overall dimensions and grip depths come from `board.json` (published);
- the outline is measured from the approved display mesh;
- every display choice (UV projection, material) is stated as a choice.

The result is a measured approximation of a display mesh. It is **not** recovered
manufacturing geometry, and nothing here supports a product-accuracy or
load-bearing claim. Say so in the doc comment.

Author native features: a fully constrained Sketcher profile and a pad. Bind each
contact region to **runs of the profile's own sketch edges**, extruded with a
length expression on the pad. Do not bind to the pad's faces — see traps.

### 4. Write the native checks before trusting anything

`Tools/HangboardCAD/tests/native_source_checks.py` is the pattern. It reopens the
saved document in a fresh process and asserts:

- the sketch is fully constrained and the pad recomputes a solid;
- the body occupies the expected native frame;
- each contact region's depth matches the grip depth `board.json` publishes;
- each contact region lies exactly on the board surface (measured, not assumed);
- a pad-length edit reaches the body **and every contact**;
- a profile dimension edit moves the intended region and leaves the others alone;
- the source bytes are unchanged by reopening and editing.

That last group is the part that matters. A binding that silently re-resolves to
a different surface passes every structural check and fails only a test like this.

### 5. Compile and compare against the reference

```bash
python3 Tools/HangboardCAD/run_freecad.py --extra-python-path "$PXRPATH" \
  Tools/HangboardCAD/compile_board.py --package <slug> --check --report /tmp/report.json

PYTHONPATH= python3 Tools/HangboardCAD/tests/compare_exports.py \
  <reference.usdz> Hangboards/<slug>/assets/primary.usdz --limit-mm 0.5
```

`PXRPATH` is the directory holding `pxr` (see Prerequisites). `run_freecad.py`
runs a script under `freecadcmd` with your arguments forwarded in order — use it
rather than calling `freecadcmd` directly, for the two launcher reasons above.

`compare_exports.py` samples both surfaces and measures point-to-triangle
distance in **both** directions, so a one-sided comparison cannot hide a missing
feature. It reports a sampled bound, not an exact Hausdorff distance.

Also compare the descriptors region by region. Two-way region agreement of
0.0000 mm with identical triangle counts is the target; a `facePlaneAABB` that
matches the reference numerically is the strongest cheap signal that the contact
identity survived.

### 6. Refresh the delivery lock

`docs/source-audits/2026-09-22-model-delivery-lock.json` pins the committed
bytes. Refresh it **only after** verifying the changed bytes, and keep the
previous value in `supersededSha256Manifest`:

```bash
python3 -m pytest Tools/HangboardModels/tests/test_model_delivery_alignment.py -q
```

A source-backed board is locked as descriptor + `board.json` + source, not as a
compiled asset; `verify-model-delivery.py` reports which boards those are.

### 7. Verify in the app, with the hold selected

Build and install, then drive the board-detail review route:

```bash
DERIVED=<derived data path, e.g. .context/<workspace>/derived>

xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath "$DERIVED" \
  CODE_SIGNING_ALLOWED=NO build

UDID=<simulator udid>
xcrun simctl install $UDID "$DERIVED/Build/Products/Debug-iphonesimulator/HangTen.app"
SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_DETAIL=1 \
SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID=<board id> \
  xcrun simctl launch $UDID com.hangten.training

# select a hold — deep link, not an environment variable
xcrun simctl openurl $UDID "hangten://board/<board id>/hold/<contactID>"
axe tap --label "Open" --udid $UDID            # iOS confirms custom schemes
axe describe-ui --udid $UDID | grep selectedHold
xcrun simctl io $UDID screenshot /tmp/<name>.png
```

Deep links are handled by `HangTen/Models/DeepLinkManager.swift`:

```
hangten://board/<boardID>                      open a board
hangten://board/<boardID>/hold/<contactID>     open a board with a hold selected
hangten://plan/<planID>/workout                open a plan workout
```

`hangten:///board/<id>` (empty host) also works. iOS shows an "Open in Hang Ten?"
confirmation for a custom scheme — accept it, then wait for
`boardDetail.selectedHold.<contactID>` before capturing.

Confirm the highlight lands on the right region and that the "Selected hold"
panel shows the expected depth. That exercises the descriptor's node binding,
which is the part a CPU render cannot check.

### 8. What you must not claim

- A mesh imported as B-rep is `faceted-import`. The build refuses to publish it
  without `--allow-faceted-import`, precisely so it cannot ship as if it carried
  native history. Smooth B-rep without feature history is an intermediate, not a
  parametric migration.
- Do not present a reconstructed display asset as recovered factory geometry or
  as manufacturing-ready.
- CPU previews are not native SceneKit screenshots and do not establish
  materials, picking, accessibility, suspension, or performance.

## Traps that cost real time

1. **FreeCAD reports a failed recompute through object state, not an exception.**
   A feature tree that errors leaves the object `Invalid`/`Touched` and keeps its
   previously saved shape, so a naive build publishes a stale body stitched to
   freshly computed regions. Assert that every object is `Up-to-date` after
   reopening, and fail naming the offenders.

2. **Sketcher `DistanceX`/`DistanceY` against an axis are unsigned** on the
   pinned build: they solve to the negated value regardless of the constraint
   value and the initial geometry. A profile containing negative coordinates
   therefore cannot be pinned with driving dimensions alone. The pilot stores
   negated local coordinates with positive driving dimensions and negates them
   back through an explicit sketch placement, then asserts the pad's world
   bounding box so a change in that behaviour fails the build instead of
   silently mirroring the board.

3. **Face-index bindings are fragile.** Binding contact regions to the pad's
   faces was tried and rejected: after a profile edit FreeCAD lost the face
   element map and *unrelated* contact regions silently moved to different faces.
   Bind to the sketch's own edges, which keep their identity. Add the published
   grip depth check anyway — it is what catches this class of defect.

4. **Coincident surfaces z-fight.** The approved runtime contract partitions the
   board surface: the body node carries the surface *minus* the contact regions.
   Emitting the body whole and laying contact patches on top duplicates coplanar
   geometry and flickers. Assign every body triangle to exactly one node, refuse
   a triangle claimed by two regions, and refuse an exported area that does not
   match the body surface.

5. **Normals are directions, not positions.** See the frame section.

6. **USDZ packaging stamps the current time into every archive member**, so two
   identical builds differ. Normalise the timestamps in place — the DOS date/time
   fields are fixed width, so 64-byte alignment survives. Note the central
   directory header stores its name/extra lengths at different offsets than a
   local file header; reading local offsets for both silently mis-scans, and for
   a member over 64 KiB it can wander into unrelated bytes.

7. **The package contract is exact.** The loader requires every declared
   presentation asset and rejects unknown entries in the package directory. A
   source-backed package may omit its compiled asset, but only that exact path
   and only when the package carries its own `<package>.FCStd`.

8. **App staging copies the whole package directory** and routes model assets to
   ODR. Exclude `*.FCStd` from both — the CAD source is neither a runtime
   resource nor an on-demand runtime asset.

9. **CI does not run every suite.** The pytest job's
   `defaults.run.working-directory` is `Tools/HangboardPackages`, so
   `pytest tests` never reaches `Tools/HangboardModels/tests`. That is how the
   delivery lock sat stale while six boards were added. Check which suite a test
   actually belongs to before assuming CI protects it.

10. **The v2 path and the attachment role were not exercised by the pilot.**
    Two defects shipped because nothing tested them. First, `compile_board`
    partitioned only `contact` nodes, so a declared `attachment` node was
    validated and then silently dropped from the exported asset and descriptor.
    Contacts and attachments are both regions of the body surface; the
    partition must cover both. Second, `_validate_published_depths` read
    `ContactID`, which a v2 object does not have, so the published-depth guard
    passed vacuously. It must key on `ContactSlotID` and map the slot to the
    published depth through each instance's `contactIDsBySlotID`. Both are now
    covered by `Tools/HangboardCAD/tests/metolius_native.py`.

11. **A ruled loft twists when its two sections are independently ordered.**
    A pocket floor measured as its own loop does not share vertex order with the
    opening, so `Part::Loft` connects vertex *i* to vertex *i* and the pocket
    collapses into a wedge. Resample both sections by arc length from the same
    start vertex and the same direction. A uniform inward offset also fails when
    a corner radius is smaller than the inset; resampling the measured floor
    avoids both.

## Lessons for the next board

See [`freecad-authoring-lessons.md`](freecad-authoring-lessons.md) for the full
write-up. The durable points:

- **Decide goal and acceptance bar first.** A sculpted display shell cannot be
  matched by a solid native model; either accept a measured approximation up
  front or ship a faceted import. Do not chase an unreachable `compare_exports`
  limit.
- **A prismatic extrusion flattens any local silhouette extremum.** Where the
  outline has zero slope, its extruded side wall faces straight up for the whole
  depth and renders as one over-lit facet; fillets cannot fix it. Author a
  swept lip (congruent cross-sections lofted along the span) instead. Flat tops
  and rounded crests still show up-facing facets — compare `preview.py`'s metric
  to the reference, not against zero. (Board-specific: the lattice profile is
  fine.)
- **Holds are open surfaces, not solids.** `Part::Loft`/`Part::Extrusion` with
  `Solid = False` give cap-free shells; a solid leaks an opening cap that hides
  the cavity. Reverse a shell's orientation parametrically with
  `Part::Reverse` so the cavity-facing side is front-facing.
- **Region mesh vs body partition.** A region may export its own surface only if
  its boundary matches the body area the partition removed. A hold that is a
  sub-region of a large flat body face fails this; author it as a shallow recess
  (a pocket) instead, or the partition leaves a ragged hole.
- **Never overlay a coincident patch.** A flat patch a hair proud of the face
  z-fights under the app's depth buffer; make it a real recess.
- **Closed schema.** A new descriptor field needs the Python descriptor, the
  Swift decoder, and the package validator changed together.
- **Single writer per worktree; run the suites once at the end.**
- **MXEdge Large** confirmed the Small trough pattern and added measurement
  traps (descriptor bounds, depth-map sampling, per-trough published depth,
  mono circle fit, cord mouths, source-backed lock). See lessons §11.

## Fast loop and definition of done

**Decision tree.** Measure the reference before authoring anything:

- **Constant cross-section along the intended axis? → swept profile.** Clone the
  pilot (`lattice-triple-rung`): a fully constrained sketch, a pad, a fillet;
  holds are extruded runs of the profile. Reproduces closely.
- **Genuinely sculpted shell (rounded lip, scooped pockets)? → pick the bar up
  front.** Either a native *measured approximation* (declare the accepted
  deviation; `compare_exports` is evidence, not a gate) or a *faceted import*.
  Then author each hold as a cap-free surface: a band is an extruded run; a
  recess is a pocket (`Part::Loft Solid=False` + floor face, reversed with
  `Part::Reverse`); a hold that is a sub-region of a flat body face is a
  **shallow recess** — never a coincident patch (z-fights) and never a proud
  patch (also z-fights under the app's depth buffer). For MXEdge-style
  partitioned troughs, measure topology first (AABBs + front depth map) —
  see `docs/freecad-authoring-lessons.md` §10 before inventing separate pockets.

**Inner loop (fast, host-side).** After every authoring edit:

```bash
# Host venv needs numpy, pillow, usd-core (see Toolchain). Workspace example:
#   .context/<workspace>/venv/bin/python
# PXRPATH is the directory that *contains* the `pxr` package (same value
# `run_freecad.py --extra-python-path` takes).
python3 Tools/HangboardCAD/run_freecad.py --extra-python-path "$PXRPATH" \
  Tools/HangboardCAD/compile_board.py --package <slug>

# Resolve the pre-migration USDZ from Git (never from the live package path —
# compile overwrites it). `reference.load_reference` writes
# `<scratch>/<slug>-primary.usdz`.
.context/<workspace>/venv/bin/python -c "
import sys
from pathlib import Path
sys.path.insert(0, 'Tools/HangboardCAD')
from reference import load_reference
print(load_reference('<slug>', 'primary.usdz', Path('.context/<workspace>/ref'))[0])
"
.context/<workspace>/venv/bin/python Tools/HangboardCAD/preview.py --package <slug> \
  --reference .context/<workspace>/ref/<slug>-primary.usdz
```

`preview.py` is a diagnostic only (never a build input). It renders front/side/top
with normal shading (and the reference side by side), prints the node inventory
and bounds, and reports the largest up-facing top facet under the same metric on
both assets. Flat tops and rounded crests both produce up-facing facets — compare
to the reference and the front render, not against zero. Read the front render;
then build the app and screenshot a deep-linked hold. Only run the suites and
refresh the lock once the shape is right.

**Definition of done.**

- the node inventory and `modelBounds` match the published facts;
- every hold renders as one cohesive region in the app (deep link + screenshot);
- `Tools/HangboardCAD/tests/native_source_checks.py` (or the board's variant)
  passes: reopen, published depths, region-on-surface, edit propagation, and the
  slot/instance relationship;
- both pytest suites pass and the delivery lock is refreshed.

## Reproducibility and the USDZ as a build output

`Tools/HangboardCAD/verify_reproducible.py` recompiles each source-backed board
in a fresh process and requires the bytes to match the committed USDZ and the
derived descriptor to equal the committed one. `prepare_assets.py` compiles into
a directory with the same check, for builds that consume a compiled asset.

This matters because the app enforces it at runtime: `BoardPackageStore` rejects
a package whose delivered bytes do not hash to the descriptor's `modelSHA256`. A
platform that cannot reproduce the committed bytes must not compile the asset for
delivery. Prove reproducibility on the target platform *before* removing a
committed asset.

## Model and cost policy

**Claude/Opus models are too expensive for this work.** One Opus review pass cost
**$6.37** against a $10 weekly OpenRouter limit — 64% of the budget for a single
review. It was genuinely valuable (it found a publish-from-failed-recompute
blocker with a concrete reproduction, plus several smaller defects), but that
rate is not sustainable here and the user has ruled it out.

Practical routing:

- Use cheap OpenRouter models (`deepseek/deepseek-v4.1-flash`, `qwen/qwen3.7-flash`)
  for bounded, precisely specified work. A DeepSeek agent fixed the archive
  preflight and caught an error in the brief it was given for a few cents. The
  same model produced nothing in 33 minutes when given an open-ended brief, so
  the brief matters more than the model tier.
- Give a worker exclusive file ownership and the exact commands to run. Another
  agent may be editing the same worktree.
- Prefer tests over prose review. Every defect found in the pilot review is now
  covered by a test that fails without the fix; those cost nothing to re-run.
- Reserve any remaining review budget for one bounded, specific question with a
  small evidence package — not a whole-branch read.

## Command cheat sheet

```bash
PXRPATH=<dir holding pxr>

# compile (check mode: validates and stages, publishes nothing)
python3 Tools/HangboardCAD/run_freecad.py --extra-python-path "$PXRPATH" \
  Tools/HangboardCAD/compile_board.py --package <slug> --check

# compile and publish into the package
python3 Tools/HangboardCAD/run_freecad.py --extra-python-path "$PXRPATH" \
  Tools/HangboardCAD/compile_board.py --package <slug>

# native source checks (reopen, recompute, edit propagation, guards)
python3 Tools/HangboardCAD/run_freecad.py --extra-python-path "$PXRPATH" \
  Tools/HangboardCAD/tests/native_source_checks.py Hangboards/<slug>/<slug>.FCStd
python3 Tools/HangboardCAD/run_freecad.py --extra-python-path "$PXRPATH" \
  Tools/HangboardCAD/tests/native_broken_source_check.py

# CAD contract, exporter, and native integration suites
python3 -m pytest Tools/HangboardCAD/tests -q

# model, package, and delivery-lock suites
python3 -m pytest Tools/HangboardModels Tools/HangboardPackages -q

# package validation across the catalogue
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory

# reproducibility of committed assets against their sources
python3 Tools/HangboardCAD/verify_reproducible.py --extra-python-path "$PXRPATH"

# compile into a directory instead of the packages
python3 Tools/HangboardCAD/prepare_assets.py --out <dir> --extra-python-path "$PXRPATH"

