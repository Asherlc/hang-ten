# Hangboard 3D Batch 02 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate six raster-only hangboard packages to model-first 3D packages from `hangboards-batch-02.zip`, re-authoring Escape Beta to its manufacturer-documented 22 selections and correcting source-confirmed contact inventories.

**Architecture:** Each delivered GLB is normalized in Blender (coordinate-wrapper empties baked into meshes; every material given a solid-color image so the existing compiler accepts it), then compiled by `Tools/HangboardModels/import_contact_model_source.py` into `assets/primary.usdz` + hash-bound `assets/primary.model.json`. Escape Beta is additionally bisected to split its two merged pinch wings and two continuous centre sloper rails into the manufacturer's left/right positions. `board.json` then switches `media.type` raster→model, adjusting `contacts[]` only where the manufacturer evidence requires it.

**Tech Stack:** Blender 5.2 headless, `contact_model_package.py`, `import_contact_model_source.py`, `scripts/hangboard-packages.sh`, UV/Python 3.13.5 venv.

---

## Decisions locked by prior research

Source evidence is retained in `.context/migration-batch-02/research/` (`FINDINGS.md`, `evidence/`, `SHA256SUMS.txt`). Manufacturer sources were re-fetched and independently inspected.

| App package | Model GLB | Action |
|---|---|---|
| `metolius-foundry` | 18 regions | Keep app's 18 contact IDs; map by manufacturer number. |
| `escape-beta-22` | **re-authored 18→22** | Keep app's 22 IDs; split pinches and centre sloper rails to manufacturer positions 1–11. |
| `soill-iron-palm-2` | 8 regions | Keep app's 8 IDs; correct `flat-edge-25` depth to 35 mm (manufacturer: 40/35/15). |
| `soill-split-palm` | 14 regions | Adopt model's 7-per-unit inventory (manufacturer lists 7/unit); merge `small-sloper-*` + `lower-pinch-*` into `*-small-sloper-pinch`. |
| `nature-stoak-board-iii` | 7 regions | Keep app's 7 IDs; map by geometry to model regions. |
| `mammut-diamond-finger` | 16 regions | Adopt model's 16 stable IDs; the manufacturer publishes no numbered inventory and the model is the best available (user decision). |

`contacts[]` is the app authority; the importer requires `logicalContactIDs` to equal the board contact order and every source mesh to be mapped exactly once. Non-contact extra meshes (Mammut's four `unresolved-*`) are mapped as `body`.

---

## Task 1: Retain batch-02 sources and verification evidence

**Files:**
- Keep: `.context/migration-batch-02/source/**` (extracted delivery)
- Create: `docs/source-audits/2026-09-16-hangboard-3d-batch-migration/source-delivery/*.glb`
- Create: `docs/source-audits/2026-09-16-hangboard-3d-batch-migration/evidence/**`
- Create: `docs/source-audits/2026-09-16-hangboard-3d-batch-migration/README.md`

- [ ] **Step 1: Copy the six delivered GLBs to retained source-delivery**

```bash
D=docs/source-audits/2026-09-16-hangboard-3d-batch-migration
mkdir -p "$D/source-delivery" "$D/evidence"
for g in escape-beta-board mammut-diamond-finger metolius-foundry \
  nature-climbing-stoak-board-iii so-ill-iron-palm-2-0 so-ill-split-palm; do
  cp ".context/migration-batch-02/source/$g/$g.glb" "$D/source-delivery/$g.glb"
done
```

- [ ] **Step 2: Copy independent manufacturer evidence**

```bash
cp .context/migration-batch-02/research/evidence/* "$D/evidence/"
cp .context/migration-batch-02/research/FINDINGS.md "$D/evidence/FINDINGS.md"
cp .context/migration-batch-02/research/SHA256SUMS.txt "$D/evidence/SHA256SUMS.txt"
```

- [ ] **Step 3: Write README describing scope and provenance**

Write `$D/README.md` stating: batch-02 delivery revision `foundry-verification-inset-selections-browser-tests-20260916`; six GLBs retained with hashes; independent Findings verdicts (Escape model under-split, Mammut non-exhaustive, Foundry/Iron Palm/Split Palm source-confirmed, Stoak count-only); the user decision to re-author Escape and migrate Mammut as-is.

- [ ] **Step 4: Verify hashes match the batch manifest**

```bash
python3 - <<'PY'
import json,hashlib
m=json.load(open('.context/migration-batch-02/source/batch-manifest.json'))
for x in m['models']:
    p=f"docs/source-audits/2026-09-16-hangboard-3d-batch-migration/source-delivery/{x['slug']}.glb"
    h=hashlib.sha256(open(p,'rb').read()).hexdigest()
    assert h==x['glbSha256'], (x['slug'],h,x['glbSha256'])
print('all source hashes match batch manifest')
PY
```

- [ ] **Step 5: Commit**

```bash
git add docs/source-audits/2026-09-16-hangboard-3d-batch-migration
git commit -m "docs: retain batch-02 GLB sources and source verification evidence"
```

---

## Task 2: Build the model-normalization tool and prove it on Foundry

**Files:**
- Create: `.context/migration-batch-02/tools/normalize_glb.py` (already written and proven)

- [ ] **Step 1: Confirm the normalizer content**

`.context/migration-batch-02/tools/normalize_glb.py` must: import GLB; `parent_clear(CLEAR_KEEP_TRANSFORM)` + `transform_apply` on all meshes; delete all empties; for each material add a 1×1 sRGB solid-color image from the Principled Base Color, linked to Base Color; export GLB.

- [ ] **Step 2: Establish the Python model venv (recorded versions)**

```bash
uv python install 3.13.5
uv venv --python 3.13.5 .context/migration-batch-02/.venv-model
uv pip install --python .context/migration-batch-02/.venv-model/bin/python \
  -r .context/migration-batch-02/source/escape-beta-board/source/requirements.txt
.context/migration-batch-02/.venv-model/bin/python -c "import numpy,scipy,trimesh,vtk,skimage,shapely,PIL;print('deps ok')"
```

Note: the supplied `source/rebuild.py` UV stage fails on this host (float32 precision) even for the unmodified model; the migration therefore normalizes the delivered GLB directly rather than regenerating it. Record this as an environmental limitation.

- [ ] **Step 3: Normalize Foundry and verify only body+contact meshes remain**

```bash
P=.context/migration-batch-02/prototype
blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration-batch-02/tools/normalize_glb.py -- \
  .context/migration-batch-02/source/metolius-foundry/metolius-foundry.glb \
  $P/metolius-foundry-normalized.glb
```

Expected: exit 0. Re-importing shows 19 mesh objects (1 body + 18 contacts), no EMPTY.

- [ ] **Step 4: Commit the normalizer**

```bash
git add .context/migration-batch-02/tools/normalize_glb.py
git commit -m "chore: add GLB normalizer for batch-02 compiler import"
```

---

## Task 3: Re-author Escape Beta to 22 selections

**Files:**
- Create: `.context/migration-batch-02/tools/reauthor_escape.py`
- Create: `.context/migration-batch-02/escape/escape-beta-board-22.glb`
- Create: `.context/migration-batch-02/escape/hold-map.json`
- Create: `.context/migration-batch-02/escape/reauthor-report.json`

- [ ] **Step 1: Write the bisect/re-author script**

The script imports the delivered `escape-beta-board.glb`, then:

1. `left-pinch` → bisect plane `co=(0,0,b_pinch)`, `no=(0,0,1)`; upper part renamed `left-thin-pinch`, lower `left-wide-pinch`. Same for `right-pinch`.
2. `centre-sloper-50` → bisect at `x=0`; renamed `left-sloper-50` / `right-sloper-50`.
3. `centre-sloper-31` → bisect at `x=0`; renamed `left-sloper-31` / `right-sloper-31`.
4. Bake empties + add solid-color material images as in the normalizer.
5. Export `.context/migration-batch-02/escape/escape-beta-board-22.glb`.

`b_pinch` defaults to source `z = 0` mm. Bisect uses `use_fill=False` (open surface patch). After each bisect, assert both halves have ≥1 face, else abort.

- [ ] **Step 2: Run and verify 22 contact meshes**

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration-batch-02/tools/reauthor_escape.py -- \
  .context/migration-batch-02/source/escape-beta-board/escape-beta-board.glb \
  .context/migration-batch-02/escape/escape-beta-board-22.glb \
  .context/migration-batch-02/escape/reauthor-report.json
```

Expected: report lists 22 contact objects + `body-board`.

- [ ] **Step 3: Write the 22-entry hold-map**

Generate `hold-map.json` with `contacts[].holdId/nodeName` = the 22 names and metadata (`name`, `publishedDepthMm`) from the delivered hold-map (thin/wide pinch inherit the pinch entry; sloper halves inherit 50/31 mm). Keep `sourceCoordinates`/`integrationCoordinates` from the delivered hold-map.

- [ ] **Step 4: Render the 4 new boundaries for operator review**

Render the re-authored model (front + oblique) and each split contact close-up to `.context/migration-batch-02/escape/review/`. Show the user the thin/wide pinch boundary and the sloper left/right splits. **Do not proceed** until the boundary placement is approved; adjust `b_pinch` and re-run if requested.

- [ ] **Step 5: Commit**

```bash
git add .context/migration-batch-02/tools/reauthor_escape.py .context/migration-batch-02/escape
git commit -m "feat: re-author escape-beta-board to the manufacturer 22-selection inventory"
```

---

## Task 4: Write source manifests and contact mappings

**Files (per board under `.context/migration-batch-02/<slug>/`):**
- Create: `source-manifest.json`, `contact-mapping.json`

The mapping schema is `{"schemaVersion":1,"packageID":...,"logicalContactIDs":[...],"objects":[{"sourceNodeID","role",...}]}`. `logicalContactIDs` MUST equal the current `Hangboards/<dir>/board.json` `contacts[].id` order (after any Task 6 contact edits). Every mesh object must be mapped: contacts → `role:"contact"`, all bodies/extra meshes → `role:"body"`.

- [ ] **Step 1–6: Write each board's files using the tables below.**

Source manifest template (substitute publisher/evidence URL, delivered GLB SHA, normalized GLB SHA, packageID):

```json
{
  "schemaVersion": 1,
  "packageID": "<packageID>",
  "manufacturerPhysicalAuthority": {"publisher": "<publisher>", "evidencePacket": "<product URL>"},
  "historicalSource": {"status": "missing"},
  "auditedModelSource": {
    "provenanceType": "user-provided",
    "authorization": "Batch-02 delivered GLB <delivered sha256>; coordinate-wrapper empties baked and removed and neutral solid-color material images added for compiler import (<normalized sha256>)",
    "retainedPath": ".context/migration-batch-02/<slug>/<file>.normalized.glb",
    "sha256": "<normalized sha256>"
  },
  "supersessionRuling": "<one sentence>"
}
```

Mapping tables (app contact ID → model node name):

**metolius-foundry** (`body-board`→body): `pinch-1-left`→`left-pinch`, `jug-2-left`→`left-jug`, `pocket-3-left`→`left-pocket-32`, `pocket-4-left`→`left-pocket-22`, `pocket-5-left`→`left-pocket-30`, `pocket-6-left`→`left-pocket-15`, `pocket-7-left`→`left-pocket-21`, `sloper-8-center`→`centre-sloper-53`, `edge-9-center`→`centre-edge-16`, `edge-10-center`→`centre-edge-30`, `edge-11-center`→`centre-edge-23`, `pocket-7-right`→`right-pocket-21`, `pocket-6-right`→`right-pocket-15`, `pocket-5-right`→`right-pocket-30`, `pocket-4-right`→`right-pocket-22`, `pocket-3-right`→`right-pocket-32`, `jug-2-right`→`right-jug`, `pinch-1-right`→`right-pinch`.

**escape-beta-22** (`body-board`→body): `hold-01-left`→`left-thin-pinch`, `hold-02-left`→`left-wide-pinch`, `hold-03-left`→`left-jug-38`, `hold-04-left`→`left-incut-29`, `hold-05-left`→`left-incut-12`, `hold-06-left`→`left-flat-38`, `hold-07-left`→`left-flat-29`, `hold-08-left`→`left-flat-12`, `hold-09-left`→`left-sloper-50`, `hold-10-left`→`left-sloper-31`, `hold-11-left`→`left-sloper-12`, mirrored for right.

**soill-iron-palm-2** (`body-board`→body): `sloper-left`→`left-large-sloper`, `sloper-right`→`right-large-sloper`, `pinch-left`→`left-pinch`, `top-incut-jug`→`top-jug`, `rounded-edge-40`→`rail-40`, `flat-edge-25`→`rail-35`, `flat-edge-15`→`rail-15`, `pinch-right`→`right-pinch`.

**nature-stoak-board-iii** (`body-board`→body): map by geometry using the delivered `selection-review/*.png` and per-mesh bounds. Expected: `top-jug`→`top-jug`, `edge-22-center`→`centre-granite-edge`, `gradient-edge-left`→`left-tapered-wood-edge`, `gradient-edge-right`→`right-tapered-wood-edge`, `lower-composite-left`→`left-granite-edge`, `lower-composite-right`→`right-granite-edge`, `lower-composite-center`→`upper-centre-wood-edge`. Record the evidence (bounds + render) in a `mapping-evidence.json`.

**mammut-diamond-finger** (16 regions; `body-board`+4 `unresolved-*`→body): `mam-jug-L`, `mam-jug-R`, `mam-sloper-C`, `mam-mid-edge-C`, `mam-mono-L`, `mam-mono-R`, `mam-upper-pocket-L`, `mam-upper-pocket-R`, `mam-lateral-ledge-L`, `mam-lateral-ledge-R`, `mam-upper-pocket-C`, `mam-lower-edge-C`, `mam-upper-open-bay-L`, `mam-upper-open-bay-R`, `mam-upper-inset-L`, `mam-upper-inset-R`.

**soill-split-palm** (14 regions; `body-left`+`body-right`→body): `left-top-jug`, `left-large-sloper`, `left-small-sloper-pinch`, `left-outer-crimp`, `left-sloping-rail`, `left-flat-rail`, `left-bottom-crimp`, and right mirrors.

- [ ] **Step 7: Validate every mapping covers every board contact**

```bash
for pair in metolius-foundry:metolius-foundry escape-beta-22:escape-beta-22 \
  soill-iron-palm-2:soill-iron-palm-2 nature-stoak-board-iii:nature-stoak-board-iii \
  mammut-diamond-finger:mammut-diamond-finger soill-split-palm:soill-split-palm; do :; done
python3 .context/migration-batch-02/tools/check_mappings.py  # asserts logical==board order and coverage
```

- [ ] **Step 8: Commit**

```bash
git add .context/migration-batch-02
git commit -m "chore: add batch-02 source manifests and contact mappings"
```

---

## Task 5: Update contact inventories for the boards whose regions change

**Files:**
- Modify: `Hangboards/mammut-diamond-finger/board.json` (21→16 contacts)
- Modify: `Hangboards/soill-split-palm/board.json` (16→14 contacts: merge small sloper + pinch)
- Modify: `Hangboards/soill-iron-palm-2/board.json` (fix `flat-edge-25` depth → 35 mm)

- [ ] **Step 1: Rewrite Mammut contacts to the 16 model regions**, deriving `kind` from the region name (jug/sloper/edge/pocket/mono→pocket/ledge→edge/inset→pocket/bay→edge) and leaving `depth` null unless the delivered `contact-metadata.json` or manufacturer establishes it. Keep `equipmentObjectID:"primary"`, `revisionID:"2026-09-contact-first"`.

- [ ] **Step 2: Rewrite Split Palm contacts to 14 regions** (7 per unit), replacing `small-sloper-*`+`lower-pinch-*` with `small-sloper-pinch-*`. Keep the three manufacturer rail depths (38.1/25.4/12.7).

- [ ] **Step 3: Correct Iron Palm's second rail** to `id":"flat-edge-35"` with `depth 35`, preserving order.

- [ ] **Step 4: Validate JSON parsing**

```bash
for d in mammut-diamond-finger soill-split-palm soill-iron-palm-2; do
  python3 -c "import json;json.load(open('Hangboards/$d/board.json'));print('$d ok')"
done
```

- [ ] **Step 5: Commit**

```bash
git add Hangboards/mammut-diamond-finger/board.json Hangboards/soill-split-palm/board.json Hangboards/soill-iron-palm-2/board.json
git commit -m "data: reconcile batch-02 board contact inventories with manufacturer evidence"
```

---

## Task 6: Compile all six model packages

**Files (per board):**
- Create: `.context/migration-batch-02/<slug>/<slug>.normalized.glb`
- Create: `.context/migration-batch-02/<slug>/compiled/assets/{primary.usdz,primary.model.json}`
- Create: `.context/migration-batch-02/<slug>/migration-report.json`

- [ ] **Step 1: Normalize each delivered GLB** (Escape uses the Task 3 re-authored GLB as its delivered input; do not re-run the normalizer over it).

```bash
for g in mammut-diamond-finger metolius-foundry nature-climbing-stoak-board-iii \
  so-ill-iron-palm-2-0 so-ill-split-palm; do
  blender --background --factory-startup --python-exit-code 1 \
    --python .context/migration-batch-02/tools/normalize_glb.py -- \
    ".context/migration-batch-02/source/$g/$g.glb" \
    ".context/migration-batch-02/$g/$g.normalized.glb"
done
```

- [ ] **Step 2: Compile each board**

```bash
# repeat per board with its packageID, normalized GLB, mapping, board.json
blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration-batch-02/<slug>/source-manifest.json \
  --mapping  .context/migration-batch-02/<slug>/contact-mapping.json \
  --package  <packageID> \
  --board-json Hangboards/<dir>/board.json \
  --output-directory .context/migration-batch-02/<slug>/compiled \
  --report .context/migration-batch-02/<slug>/migration-report.json
```

- [ ] **Step 3: Verify status, contact counts, and descriptor hash binding**

```bash
python3 .context/migration-batch-02/tools/verify_compiled.py  # each report status=converted, sha match, bounds finite
```

- [ ] **Step 4: Commit**

```bash
git add .context/migration-batch-02
git commit -m "feat: compile batch-02 USDZ and descriptors"
```

---

## Task 7: Install assets and switch presentations to model

**Files (per board):**
- Create: `Hangboards/<dir>/assets/primary.usdz`, `primary.model.json`
- Modify: `Hangboards/<dir>/board.json` (media raster→model)
- Delete: `Hangboards/<dir>/assets/primary.png`

- [ ] **Step 1: Copy compiled assets**

```bash
for pair in metolius-foundry:metolius-foundry escape-beta-22:escape-beta-22 \
  soill-iron-palm-2:soill-iron-palm-2 nature-stoak-board-iii:nature-stoak-board-iii \
  mammut-diamond-finger:mammut-diamond-finger soill-split-palm:soill-split-palm; do
  s=${pair%%:*}; d=${pair##*:}
  cp ".context/migration-batch-02/$s/compiled/assets/primary.usdz" "Hangboards/$d/assets/"
  cp ".context/migration-batch-02/$s/compiled/assets/primary.model.json" "Hangboards/$d/assets/"
done
```

- [ ] **Step 2: Replace each presentation media block** with:

```json
"media": {
  "type": "model",
  "assetPath": "assets/primary.usdz",
  "descriptorPath": "assets/primary.model.json",
  "display": { "camera": { "type": "orthographic", "viewDirection": [0,0,-1], "up": [0,1,0], "fitPadding": 0.08 } }
}
```

Remove any `contactGeometry`. Compute each presentation `aspectRatio` from the descriptor bounds (`width / height` in the board frame) and set it.

- [ ] **Step 3: Remove raster assets**

```bash
for d in metolius-foundry escape-beta-22 soill-iron-palm-2 nature-stoak-board-iii mammut-diamond-finger soill-split-palm; do
  rm -f "Hangboards/$d/assets/primary.png"
done
```

- [ ] **Step 4: Validate packages and confirm model-only**

```bash
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
for d in metolius-foundry escape-beta-22 soill-iron-palm-2 nature-stoak-board-iii mammut-diamond-finger soill-split-palm; do
  ls "Hangboards/$d/assets/"*.png 2>/dev/null && echo "FAIL $d has PNG" || echo "OK $d model-only"
done
```

- [ ] **Step 5: Commit**

```bash
git add Hangboards
git commit -m "feat: migrate six batch-02 hangboards to model-first 3D packages"
```

---

## Task 8: Add cord-audit records and retained evidence

**Files:**
- Modify: `docs/source-audits/2026-09-13-model-hangboard-cord-audit.json` (+6 records)
- Create: `docs/source-audits/2026-09-13-model-cord-snapshots/<slug>-manufacturer-product-2026-09-16.html`

- [ ] **Step 1: Retain a manufacturer product snapshot per board**

For each board, save the manufacturer product page HTML (already downloaded under `.context/migration-batch-02/research/raw/`) as `<slug>-manufacturer-product-2026-09-16.html` and compute SHA-256.

- [ ] **Step 2: Append one `excluded`/`noDocumentedSuspension` record per board** with `view`, `url`, `exactRevisionID`, `sourceTier:"manufacturer"`, `snapshotSHA256`, `snapshotPath`, nonempty `ruling`, and `humanApproval` (reviewer `hang-ten-cord-audit`, date `2026-09-16`).

- [ ] **Step 3: Validate exact coverage**

```bash
scripts/hangboard-packages.sh audit-cords --root Hangboards \
  --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
```

Expected: exit 0; `modelPackageIDs` includes all six new IDs.

- [ ] **Step 4: Commit**

```bash
git add docs/source-audits
git commit -m "docs: add batch-02 cord-audit records and retained manufacturer evidence"
```

---

## Task 9: Full validation lanes

- [ ] **Step 1: Package + cord validation**

```bash
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
```

- [ ] **Step 2: Python test lanes**

```bash
.context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests -q
PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardModels/test_contact_model_descriptor.py \
  Tools/HangboardModels/test_contact_model_package.py \
  Tools/HangboardModels/test_import_contact_model_source.py -q
```

- [ ] **Step 3: Clearance regression and compileall**

```bash
rtk proxy ruby Tools/HangboardModels/check_production_cord_clearance.rb
python3 -m compileall -q Tools/HangboardPackages/src
git diff --check
```

- [ ] **Step 4: Focused XCTest selectors** for `SuspendedBoardPresentationTests`, `BoardModelTests`, `BoardPackageStoreTests` on a workspace-owned simulator.

- [ ] **Step 5: Report any blocked lane precisely** (missing runtime, deadlock) rather than claiming success.

---

## Task 10: Current-source native iOS review

- [ ] **Step 1** Follow `validate-hang-ten-ios` + `docs/IOS_SIMULATOR_VALIDATION.md` + `docs/IOS_RUNTIME_SERVICES.md`; create the exact isolated simulator `Hang Ten Paseo legit-puma Review`, register its UUID in the pending/owned manifests, build into `.context/DerivedData`.
- [ ] **Step 2** Capture, for each of the six app IDs, portrait + landscape active, plus at least one selected-contact capture; inspect model load, framing, highlight clear/restore, orbit/reset, and picking.
- [ ] **Step 3** Record evidence under `.context/legit-puma-batch-02-acceptance/` and add a report to `docs/source-audits/2026-09-16-hangboard-3d-batch-migration/ios-native-acceptance.md`.
- [ ] **Step 4** Clean up the owned simulator UUID and DerivedData; verify absence.

---

## Task 11: Cleanup and completion

- [ ] **Step 1** Remove the extraction, venvs, prototype, and normalized intermediates that are not retained evidence; keep manifests, mappings, reports, findings, and retained source GLBs.
- [ ] **Step 2** Verify no workspace-owned external resource remains (simulator, DerivedData, tunnels).
- [ ] **Step 3** Confirm completion criteria: all six model-only with valid USDZ+descriptor; closed cord audit covers every model package; manufacturer-traceable inventories; focused/full lanes pass or blocked lanes stated; native captures cover every board; cleanup verified.

---

## Self-review notes

- **Spec coverage:** source evidence (Task 1/8), re-authoring (3), inventory corrections (5), compile+install (6/7), cord audit (8), validation (9), native (10), cleanup (11).
- **Type consistency:** `logicalContactIDs` order must be re-checked after Task 5 edits; Tasks 4 and 6 depend on Task 5 ordering.
- **Known risk:** the supplied `source/rebuild.py` cannot reproduce even the unmodified GLB on this host; the plan normalizes delivered GLBs instead and records that limitation.
