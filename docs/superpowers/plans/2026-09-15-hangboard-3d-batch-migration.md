# Hangboard 3D Batch Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate 6 raster-only hangboard packages to model-only 3D packages using GLB sources, Blender round-trip, and the existing contact-model compiler.

**Architecture:** Each board's GLB is imported into Blender, meshes are tagged with body/contact roles via a contact-mapping manifest derived from the hold-map, then compiled through `contact_model_package.py` to produce USDZ + descriptor. The `board.json` is updated to replace the raster presentation with a model presentation. Suspension cord research is performed per-board.

**Tech Stack:** Python, Blender (headless), `contact_model_package.py`, `import_contact_model_source.py`, `hangboard-packages.sh`

---

## File Structure

| File | Purpose |
|---|---|
| `.context/migration/SLUG/glb-to-blend.py` | Blender script to import GLB and save as .blend |
| `.context/migration/SLUG/source-manifest.json` | Source evidence manifest for import pipeline |
| `.context/migration/SLUG/contact-mapping.json` | GLB object → contact ID mapping |
| `.context/migration/SLUG/migration-report.json` | Per-board migration result |
| `Hangboards/SLUG/board.json` | Updated: raster → model presentation |
| `Hangboards/SLUG/assets/primary.usdz` | Compiled 3D model |
| `Hangboards/SLUG/assets/primary.model.json` | Hash-bound contact descriptor |

---

## Task 1: Extract Zip and Set Up Staging

**Files:**
- Create: `.context/migration/` directory tree
- Create: `.context/migration/README.md`

- [ ] **Step 1: Create staging directory**

```bash
mkdir -p .context/migration
```

- [ ] **Step 2: Extract zip to staging**

```bash
unzip -o /Users/asherlc/.paseo/uploads/upload_4e5abf73-d47f-4b1b-bfbb-f6713de46967/hangboards-batch-01-no-screwholes.zip \
  -d .context/migration/source
```

Expected: 6 model directories extracted under `.context/migration/source/hangboards-batch-01/models/`

- [ ] **Step 3: Create per-board staging directories**

```bash
for slug in dewoodstok-woodbord escape-unlimited-board evolv-basic-training-board-long \
  metolius-wood-grips-ii-deluxe moon-armstrong-ash target10a-linebreaker-base; do
  mkdir -p ".context/migration/$slug"
done
```

- [ ] **Step 4: Copy GLB and hold-map to per-board staging**

```bash
SRC=".context/migration/source/hangboards-batch-01/models"
for model_dir in "$SRC"/*/; do
  slug=$(basename "$model_dir")
  cp "$model_dir"/*.glb ".context/migration/$slug/" 2>/dev/null
  cp "$model_dir"/hold-map.json ".context/migration/$slug/" 2>/dev/null
  cp "$model_dir"/evidence/* ".context/migration/$slug/" 2>/dev/null
done
```

- [ ] **Step 5: Verify extraction**

```bash
for slug in dewoodstok-woodbord escape-unlimited-board evolv-basic-training-board-long \
  metolius-wood-grips-ii-deluxe moon-armstrong-ash target10a-linebreaker-base; do
  echo "=== $slug ==="
  ls ".context/migration/$slug/"
done
```

Expected: Each directory contains a `.glb` file and `hold-map.json`.

- [ ] **Step 6: Commit**

```bash
git add .context/migration/
git commit -m "chore: extract hangboard batch 01 GLB sources to staging"
```

---

## Task 2: Build Contact Mapping for deWoodstok Woodbord (Pilot)

**Files:**
- Create: `.context/migration/dewoodstok-woodbord/contact-mapping.json`
- Read: `.context/migration/dewoodstok-woodbord/hold-map.json`
- Read: `Hangboards/dewoodstok-woodbord/board.json`

- [ ] **Step 1: Read the hold-map to identify GLB object names**

```bash
python3 -c "
import json
hm = json.load(open('.context/migration/dewoodstok-woodbord/hold-map.json'))
for h in hm['holds']:
    print(f\"{h['holdId']:30s} -> {h['objectName']}\")
"
```

Expected: List of holdId → objectName mappings.

- [ ] **Step 2: Read existing board.json contacts**

```bash
python3 -c "
import json
bj = json.load(open('Hangboards/dewoodstok-woodbord/board.json'))
for c in bj['contacts']:
    print(c['id'])
"
```

Expected: List of contact IDs.

- [ ] **Step 3: Create contact mapping manifest**

Write `.context/migration/dewoodstok-woodbord/contact-mapping.json`:

```json
{
  "schemaVersion": 1,
  "packageID": "dewoodstok-woodbord",
  "logicalContactIDs": [
    "<from board.json contacts[].id, in order>"
  ],
  "objects": [
    {
      "sourceNodeID": "<GLB mesh object name for body>",
      "role": "body"
    },
    {
      "sourceNodeID": "<GLB mesh object name for hold>",
      "role": "contact",
      "contactID": "<matching contact ID>"
    }
  ]
}
```

Use the hold-map's `objectName` values as `sourceNodeID`. The body mesh is typically named `body` or similar in the GLB. Map every `contacts[].id` from `board.json` to a contact role object.

- [ ] **Step 4: Validate mapping covers all contacts**

```bash
python3 -c "
import json
mapping = json.load(open('.context/migration/dewoodstok-woodbord/contact-mapping.json'))
board = json.load(open('Hangboards/dewoodstok-woodbord/board.json'))
board_ids = {c['id'] for c in board['contacts']}
mapped_ids = {o['contactID'] for o in mapping['objects'] if o['role'] == 'contact'}
missing = board_ids - mapped_ids
extra = mapped_ids - board_ids
if missing: print(f'MISSING: {missing}')
if extra: print(f'EXTRA: {extra}')
if not missing and not extra: print('All contacts mapped')
"
```

Expected: `All contacts mapped`

- [ ] **Step 5: Commit**

```bash
git add .context/migration/dewoodstok-woodbord/contact-mapping.json
git commit -m "chore: add dewoodstok-woodbord contact mapping manifest"
```

---

## Task 3: Build Contact Mapping for Moon Armstrong (Pilot)

**Files:**
- Create: `.context/migration/moon-armstrong-ash/contact-mapping.json`
- Read: `.context/migration/moon-armstrong-ash/hold-map.json`
- Read: `Hangboards/moon-armstrong/board.json`

- [ ] **Step 1: Read the hold-map**

```bash
python3 -c "
import json
hm = json.load(open('.context/migration/moon-armstrong-ash/hold-map.json'))
for h in hm['holds']:
    print(f\"{h['holdId']:30s} -> {h['objectName']}\")
"
```

- [ ] **Step 2: Read existing board.json contacts**

```bash
python3 -c "
import json
bj = json.load(open('Hangboards/moon-armstrong/board.json'))
for c in bj['contacts']:
    print(c['id'])
"
```

- [ ] **Step 3: Create contact mapping manifest**

Write `.context/migration/moon-armstrong-ash/contact-mapping.json` with the same schema as Task 2. Map every contact ID from `board.json` to a GLB object name from the hold-map.

- [ ] **Step 4: Validate mapping covers all contacts**

```bash
python3 -c "
import json
mapping = json.load(open('.context/migration/moon-armstrong-ash/contact-mapping.json'))
board = json.load(open('Hangboards/moon-armstrong/board.json'))
board_ids = {c['id'] for c in board['contacts']}
mapped_ids = {o['contactID'] for o in mapping['objects'] if o['role'] == 'contact'}
missing = board_ids - mapped_ids
extra = mapped_ids - board_ids
if missing: print(f'MISSING: {missing}')
if extra: print(f'EXTRA: {extra}')
if not missing and not extra: print('All contacts mapped')
"
```

- [ ] **Step 5: Commit**

```bash
git add .context/migration/moon-armstrong-ash/contact-mapping.json
git commit -m "chore: add moon-armstrong-ash contact mapping manifest"
```

---

## Task 4: Write GLB-to-Blend Converter Script

**Files:**
- Create: `.context/migration/glb-to-blend.py`

- [ ] **Step 1: Write the Blender GLB import script**

Create `.context/migration/glb-to-blend.py`:

```python
#!/usr/bin/env python3
"""Import a GLB file into Blender and save as .blend."""
import sys
import bpy

def convert(glb_path: str, blend_path: str) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)

if __name__ == "__main__":
    convert(sys.argv[-2], sys.argv[-1])
```

- [ ] **Step 2: Verify script is valid Python**

```bash
python3 -c "import ast; ast.parse(open('.context/migration/glb-to-blend.py').read()); print('Valid')"
```

Expected: `Valid`

- [ ] **Step 3: Commit**

```bash
git add .context/migration/glb-to-blend.py
git commit -m "chore: add GLB-to-Blender converter script"
```

---

## Task 5: Convert Pilot GLBs to Blender Files

**Files:**
- Create: `.context/migration/dewoodstok-woodbord/source.blend`
- Create: `.context/migration/moon-armstrong-ash/source.blend`

- [ ] **Step 1: Convert deWoodstok GLB to Blender**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/dewoodstok-woodbord/dewoodstok-woodbord.glb \
  .context/migration/dewoodstok-woodbord/source.blend
```

Expected: `.context/migration/dewoodstok-woodbord/source.blend` created.

- [ ] **Step 2: Verify deWoodstok blend has expected objects**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python -c "
import bpy
bpy.ops.wm.open_mainfile(filepath='.context/migration/dewoodstok-woodbord/source.blend')
for obj in bpy.context.scene.objects:
    print(f'{obj.name:40s} type={obj.type}')
"
```

Expected: List of mesh objects matching GLB structure.

- [ ] **Step 3: Convert Moon Armstrong GLB to Blender**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/moon-armstrong-ash/moon-armstrong-ash.glb \
  .context/migration/moon-armstrong-ash/source.blend
```

Expected: `.context/migration/moon-armstrong-ash/source.blend` created.

- [ ] **Step 4: Verify Moon Armstrong blend**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python -c "
import bpy
bpy.ops.wm.open_mainfile(filepath='.context/migration/moon-armstrong-ash/source.blend')
for obj in bpy.context.scene.objects:
    print(f'{obj.name:40s} type={obj.type}')
"
```

- [ ] **Step 5: Commit**

```bash
git add .context/migration/dewoodstok-woodbord/source.blend \
  .context/migration/moon-armstrong-ash/source.blend
git commit -m "chore: convert pilot GLBs to Blender source files"
```

---

## Task 6: Write Source Manifests for Pilot Boards

**Files:**
- Create: `.context/migration/dewoodstok-woodbord/source-manifest.json`
- Create: `.context/migration/moon-armstrong-ash/source-manifest.json`

- [ ] **Step 1: Write deWoodstok source manifest**

Create `.context/migration/dewoodstok-woodbord/source-manifest.json`:

```json
{
  "schemaVersion": 1,
  "packageID": "dewoodstok-woodbord",
  "manufacturerPhysicalAuthority": {
    "publisher": "deWoodstok",
    "evidencePacket": "https://www.dewoodstok.nl/product/hangboard-woodbord/"
  },
  "historicalSource": {
    "status": "missing"
  },
  "auditedModelSource": {
    "provenanceType": "user-provided",
    "authorization": "GLB exported from verified manufacturer geometry; no-screwholes variant",
    "retainedPath": ".context/migration/dewoodstok-woodbord/dewoodstok-woodbord.glb",
    "sha256": "<sha256 of GLB file>"
  },
  "supersessionRuling": "Replaces raster presentation with model-first 3D package"
}
```

Compute the SHA-256:

```bash
shasum -a 256 .context/migration/dewoodstok-woodbord/dewoodstok-woodbord.glb | awk '{print $1}'
```

- [ ] **Step 2: Write Moon Armstrong source manifest**

Create `.context/migration/moon-armstrong-ash/source-manifest.json` with the same schema, using the Moon Armstrong GLB hash and product URL `https://moonclimbing.com/moon-armstrong-fingerboard-beech.html`.

- [ ] **Step 3: Commit**

```bash
git add .context/migration/*/source-manifest.json
git commit -m "chore: add source manifests for pilot boards"
```

---

## Task 7: Run Import Pipeline for deWoodstok (Pilot)

**Files:**
- Create: `.context/migration/dewoodstok-woodbord/compiled/` (output)
- Modify: `Hangboards/dewoodstok-woodbord/board.json`

- [ ] **Step 1: Run import_contact_model_source.py**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/dewoodstok-woodbord/source-manifest.json \
  --mapping .context/migration/dewoodstok-woodbord/contact-mapping.json \
  --package dewoodstok-woodbord \
  --board-json Hangboards/dewoodstok-woodbord/board.json \
  --output-directory .context/migration/dewoodstok-woodbord/compiled \
  --report .context/migration/dewoodstok-woodbord/migration-report.json
```

Expected: Exit code 0. Output directory contains `assets/primary.usdz` and `assets/primary.model.json`.

- [ ] **Step 2: Verify output files exist**

```bash
ls -la .context/migration/dewoodstok-woodbord/compiled/assets/
```

Expected: `primary.usdz` and `primary.model.json` present.

- [ ] **Step 3: Verify descriptor hash matches USDZ**

```bash
python3 -c "
import json, hashlib
desc = json.load(open('.context/migration/dewoodstok-woodbord/compiled/assets/primary.model.json'))
usdz_hash = hashlib.sha256(open('.context/migration/dewoodstok-woodbord/compiled/assets/primary.usdz', 'rb').read()).hexdigest()
print(f'Descriptor SHA256: {desc[\"modelSHA256\"]}')
print(f'Actual SHA256:     {usdz_hash}')
print(f'Match: {desc[\"modelSHA256\"] == usdz_hash}')
"
```

Expected: `Match: True`

- [ ] **Step 4: Verify contact node count**

```bash
python3 -c "
import json
desc = json.load(open('.context/migration/dewoodstok-woodbord/compiled/assets/primary.model.json'))
contacts = [n for n in desc['nodes'] if n['role'] == 'contact']
print(f'Contact nodes: {len(contacts)}')
for n in contacts:
    print(f'  {n[\"nodeID\"]} -> {n[\"contactID\"]}')
"
```

Expected: All contacts from board.json are bound.

- [ ] **Step 5: Copy compiled assets to package**

```bash
cp .context/migration/dewoodstok-woodbord/compiled/assets/primary.usdz \
  Hangboards/dewoodstok-woodbord/assets/
cp .context/migration/dewoodstok-woodbord/compiled/assets/primary.model.json \
  Hangboards/dewoodstok-woodbord/assets/
```

- [ ] **Step 6: Update board.json to model presentation**

Read the current `board.json`, replace the raster `media` block with:

```json
"media": {
  "type": "model",
  "assetPath": "assets/primary.usdz",
  "descriptorPath": "assets/primary.model.json",
  "display": {
    "camera": {
      "type": "orthographic",
      "viewDirection": [0, 0, -1],
      "up": [0, 1, 0],
      "fitPadding": 0.08
    }
  }
}
```

Remove `contactGeometry` from the media object. Keep `contacts[]` unchanged.

- [ ] **Step 7: Remove old raster asset**

```bash
rm Hangboards/dewoodstok-woodbord/assets/primary.png
```

- [ ] **Step 8: Validate package**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory 2>&1 | grep -A5 dewoodstok
```

Expected: No validation errors for dewoodstok-woodbord.

- [ ] **Step 9: Commit**

```bash
git add Hangboards/dewoodstok-woodbord/
git commit -m "feat: migrate dewoodstok-woodbord to 3D model package"
```

---

## Task 8: Run Import Pipeline for Moon Armstrong (Pilot)

**Files:**
- Create: `.context/migration/moon-armstrong-ash/compiled/` (output)
- Modify: `Hangboards/moon-armstrong/board.json`

- [ ] **Step 1: Run import_contact_model_source.py**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/moon-armstrong-ash/source-manifest.json \
  --mapping .context/migration/moon-armstrong-ash/contact-mapping.json \
  --package moon-armstrong-ash \
  --board-json Hangboards/moon-armstrong/board.json \
  --output-directory .context/migration/moon-armstrong-ash/compiled \
  --report .context/migration/moon-armstrong-ash/migration-report.json
```

- [ ] **Step 2: Verify output files**

```bash
ls -la .context/migration/moon-armstrong-ash/compiled/assets/
```

- [ ] **Step 3: Verify descriptor hash matches USDZ**

```bash
python3 -c "
import json, hashlib
desc = json.load(open('.context/migration/moon-armstrong-ash/compiled/assets/primary.model.json'))
usdz_hash = hashlib.sha256(open('.context/migration/moon-armstrong-ash/compiled/assets/primary.usdz', 'rb').read()).hexdigest()
print(f'Match: {desc[\"modelSHA256\"] == usdz_hash}')
"
```

- [ ] **Step 4: Copy compiled assets to package**

```bash
cp .context/migration/moon-armstrong-ash/compiled/assets/primary.usdz \
  Hangboards/moon-armstrong/assets/
cp .context/migration/moon-armstrong-ash/compiled/assets/primary.model.json \
  Hangboards/moon-armstrong/assets/
```

- [ ] **Step 5: Update board.json to model presentation**

Same pattern as Task 7 Step 6. Replace raster media with model media. Remove `contactGeometry`.

- [ ] **Step 6: Remove old raster asset**

```bash
rm Hangboards/moon-armstrong/assets/primary.png
```

- [ ] **Step 7: Validate package**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory 2>&1 | grep -A5 moon-armstrong
```

- [ ] **Step 8: Commit**

```bash
git add Hangboards/moon-armstrong/
git commit -m "feat: migrate moon-armstrong to 3D model package"
```

---

## Task 9: Validate Pilot End-to-End

**Files:** None (validation only)

- [ ] **Step 1: Run full package validation**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: No errors for dewoodstok-woodbord or moon-armstrong.

- [ ] **Step 2: Run model-tool pytest**

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardModels/tests -q 2>&1 | tail -20
```

Expected: Tests pass (or only pre-existing failures unrelated to pilot boards).

- [ ] **Step 3: Run package validation tests**

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests -q 2>&1 | tail -20
```

Expected: Tests pass.

- [ ] **Step 4: Run git diff check**

```bash
git diff --check
```

Expected: No issues (or only expected changes).

- [ ] **Step 5: Visual review of migration report**

```bash
cat .context/migration/dewoodstok-woodbord/migration-report.json | python3 -m json.tool
cat .context/migration/moon-armstrong-ash/migration-report.json | python3 -m json.tool
```

Expected: Both reports show `status: "converted"` with correct hashes and contact counts.

- [ ] **Step 6: Mark pilot complete**

The pilot has validated the pipeline. Proceed to batch the remaining 4 boards.

---

## Task 10: Batch Contact Mappings for Remaining 4 Boards

**Files:**
- Create: `.context/migration/escape-unlimited-board/contact-mapping.json`
- Create: `.context/migration/evolv-basic-training-board-long/contact-mapping.json`
- Create: `.context/migration/metolius-wood-grips-ii-deluxe/contact-mapping.json`
- Create: `.context/migration/target10a-linebreaker-base/contact-mapping.json`

- [ ] **Step 1: Create contact mapping for Escape Unlimited**

Read `Hangboards/escape-unlimited/board.json` contacts and `.context/migration/escape-unlimited-board/hold-map.json`. Create `.context/migration/escape-unlimited-board/contact-mapping.json` with the same schema as pilot boards.

- [ ] **Step 2: Create contact mapping for Evolv Basic Training Long**

Read `Hangboards/evolv-kilter-basic-long/board.json` contacts and `.context/migration/evolv-basic-training-board-long/hold-map.json`. Create `.context/migration/evolv-basic-training-board-long/contact-mapping.json`.

- [ ] **Step 3: Create contact mapping for Metolius Wood Grips II Deluxe**

Read `Hangboards/metolius-wood-grips-deluxe-ii/board.json` contacts and `.context/migration/metolius-wood-grips-ii-deluxe/hold-map.json`. Create `.context/migration/metolius-wood-grips-ii-deluxe/contact-mapping.json`.

- [ ] **Step 4: Create contact mapping for target10a Linebreaker BASE**

Read `Hangboards/target10a-linebreaker-base/board.json` contacts and `.context/migration/target10a-linebreaker-base/hold-map.json`. Create `.context/migration/target10a-linebreaker-base/contact-mapping.json`.

- [ ] **Step 5: Validate all mappings cover all contacts**

```bash
for slug in escape-unlimited-board evolv-basic-training-board-long \
  metolius-wood-grips-ii-deluxe target10a-linebreaker-base; do
  echo "=== $slug ==="
  python3 -c "
import json
mapping = json.load(open('.context/migration/$slug/contact-mapping.json'))
# Map slug to board directory
dirs = {'escape-unlimited-board': 'escape-unlimited', 'evolv-basic-training-board-long': 'evolv-kilter-basic-long', 'metolius-wood-grips-ii-deluxe': 'metolius-wood-grips-deluxe-ii', 'target10a-linebreaker-base': 'target10a-linebreaker-base'}
board = json.load(open(f'Hangboards/{dirs[\"$slug\"]}/board.json'))
board_ids = {c['id'] for c in board['contacts']}
mapped_ids = {o['contactID'] for o in mapping['objects'] if o['role'] == 'contact'}
missing = board_ids - mapped_ids
if missing: print(f'MISSING: {missing}')
else: print('OK')
"
done
```

- [ ] **Step 6: Commit**

```bash
git add .context/migration/*/contact-mapping.json
git commit -m "chore: add contact mappings for remaining 4 boards"
```

---

## Task 11: Convert Remaining GLBs to Blender

**Files:**
- Create: `.context/migration/escape-unlimited-board/source.blend`
- Create: `.context/migration/evolv-basic-training-board-long/source.blend`
- Create: `.context/migration/metolius-wood-grips-ii-deluxe/source.blend`
- Create: `.context/migration/target10a-linebreaker-base/source.blend`

- [ ] **Step 1: Convert Escape Unlimited GLB**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/escape-unlimited-board/escape-unlimited-board.glb \
  .context/migration/escape-unlimited-board/source.blend
```

- [ ] **Step 2: Convert Evolv Basic Training Long GLB**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/evolv-basic-training-board-long/evolv-basic-training-board-long.glb \
  .context/migration/evolv-basic-training-board-long/source.blend
```

- [ ] **Step 3: Convert Metolius Wood Grips II Deluxe GLB**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/metolius-wood-grips-ii-deluxe/metolius-wood-grips-ii-deluxe.glb \
  .context/migration/metolius-wood-grips-ii-deluxe/source.blend
```

- [ ] **Step 4: Convert target10a Linebreaker BASE GLB**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/migration/glb-to-blend.py -- \
  .context/migration/target10a-linebreaker-base/target10a-linebreaker-base.glb \
  .context/migration/target10a-linebreaker-base/source.blend
```

- [ ] **Step 5: Commit**

```bash
git add .context/migration/*/source.blend
git commit -m "chore: convert remaining GLBs to Blender source files"
```

---

## Task 12: Write Source Manifests for Remaining Boards

**Files:**
- Create: `.context/migration/escape-unlimited-board/source-manifest.json`
- Create: `.context/migration/evolv-basic-training-board-long/source-manifest.json`
- Create: `.context/migration/metolius-wood-grips-ii-deluxe/source-manifest.json`
- Create: `.context/migration/target10a-linebreaker-base/source-manifest.json`

- [ ] **Step 1: Create source manifests for all 4 boards**

Same schema as Task 6. Use each board's product URL and GLB SHA-256:

| Board | Product URL |
|---|---|
| Escape Unlimited | `https://escapeclimbing.com/products/ec72000` |
| Evolv Basic Training Long | `https://evolvclothing.com/products/basic-training-board` |
| Metolius Wood Grips II Deluxe | `https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards` |
| target10a Linebreaker BASE | `https://target10a.com/products/linebreaker-base` |

- [ ] **Step 2: Commit**

```bash
git add .context/migration/*/source-manifest.json
git commit -m "chore: add source manifests for remaining boards"
```

---

## Task 13: Run Import Pipeline for Remaining 4 Boards

**Files:**
- Create: `.context/migration/escape-unlimited-board/compiled/`
- Create: `.context/migration/evolv-basic-training-board-long/compiled/`
- Create: `.context/migration/metolius-wood-grips-ii-deluxe/compiled/`
- Create: `.context/migration/target10a-linebreaker-base/compiled/`
- Modify: `Hangboards/escape-unlimited/board.json`
- Modify: `Hangboards/evolv-kilter-basic-long/board.json`
- Modify: `Hangboards/metolius-wood-grips-deluxe-ii/board.json`
- Modify: `Hangboards/target10a-linebreaker-base/board.json`

- [ ] **Step 1: Import and compile Escape Unlimited**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/escape-unlimited-board/source-manifest.json \
  --mapping .context/migration/escape-unlimited-board/contact-mapping.json \
  --package escape-unlimited-board \
  --board-json Hangboards/escape-unlimited/board.json \
  --output-directory .context/migration/escape-unlimited-board/compiled \
  --report .context/migration/escape-unlimited-board/migration-report.json
```

- [ ] **Step 2: Import and compile Evolv Basic Training Long**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/evolv-basic-training-board-long/source-manifest.json \
  --mapping .context/migration/evolv-basic-training-board-long/contact-mapping.json \
  --package evolv-basic-training-board-long \
  --board-json Hangboards/evolv-kilter-basic-long/board.json \
  --output-directory .context/migration/evolv-basic-training-board-long/compiled \
  --report .context/migration/evolv-basic-training-board-long/migration-report.json
```

- [ ] **Step 3: Import and compile Metolius Wood Grips II Deluxe**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/metolius-wood-grips-ii-deluxe/source-manifest.json \
  --mapping .context/migration/metolius-wood-grips-ii-deluxe/contact-mapping.json \
  --package metolius-wood-grips-ii-deluxe \
  --board-json Hangboards/metolius-wood-grips-deluxe-ii/board.json \
  --output-directory .context/migration/metolius-wood-grips-ii-deluxe/compiled \
  --report .context/migration/metolius-wood-grips-ii-deluxe/migration-report.json
```

- [ ] **Step 4: Import and compile target10a Linebreaker BASE**

```bash
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/import_contact_model_source.py -- \
  --manifest .context/migration/target10a-linebreaker-base/source-manifest.json \
  --mapping .context/migration/target10a-linebreaker-base/contact-mapping.json \
  --package target10a-linebreaker-base \
  --board-json Hangboards/target10a-linebreaker-base/board.json \
  --output-directory .context/migration/target10a-linebreaker-base/compiled \
  --report .context/migration/target10a-linebreaker-base/migration-report.json
```

- [ ] **Step 5: Verify all compiled outputs**

```bash
for slug in escape-unlimited-board evolv-basic-training-board-long \
  metolius-wood-grips-ii-deluxe target10a-linebreaker-base; do
  echo "=== $slug ==="
  ls ".context/migration/$slug/compiled/assets/"
done
```

Expected: Each has `primary.usdz` and `primary.model.json`.

- [ ] **Step 6: Verify all descriptor hashes**

```bash
for slug in escape-unlimited-board evolv-basic-training-board-long \
  metolius-wood-grips-ii-deluxe target10a-linebreaker-base; do
  python3 -c "
import json, hashlib
desc = json.load(open('.context/migration/$slug/compiled/assets/primary.model.json'))
usdz = hashlib.sha256(open('.context/migration/$slug/compiled/assets/primary.usdz', 'rb').read()).hexdigest()
print(f'$slug: match={desc[\"modelSHA256\"] == usdz}')
"
done
```

- [ ] **Step 7: Copy compiled assets and update board.json for all 4 boards**

For each board, copy assets, replace raster media with model media in board.json, and remove old PNG. (Repeat the pattern from Tasks 7-8.)

- [ ] **Step 8: Commit**

```bash
git add Hangboards/escape-unlimited/ Hangboards/evolv-kilter-basic-long/ \
  Hangboards/metolius-wood-grips-deluxe-ii/ Hangboards/target10a-linebreaker-base/
git commit -m "feat: migrate remaining 4 hangboards to 3D model packages"
```

---

## Task 14: Full Validation

**Files:** None (validation only)

- [ ] **Step 1: Run full package validation**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: No errors for any of the 6 migrated boards.

- [ ] **Step 2: Run model-tool pytest**

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardModels/tests -q
```

- [ ] **Step 3: Run package validation tests**

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests -q
```

- [ ] **Step 4: Run Python compile check**

```bash
rtk python3 -m compileall -q Tools/HangboardPackages/src
```

- [ ] **Step 5: Run git diff check**

```bash
git diff --check
```

- [ ] **Step 6: Verify no raster assets remain in migrated packages**

```bash
for slug in dewoodstok-woodbord escape-unlimited evolv-kilter-basic-long \
  metolius-wood-grips-deluxe-ii moon-armstrong target10a-linebreaker-base; do
  if ls Hangboards/$slug/assets/*.png 2>/dev/null; then
    echo "FAIL: $slug still has PNG"
  else
    echo "OK: $slug is model-only"
  fi
done
```

Expected: All 6 boards show `OK: model-only`.

---

## Task 15: Suspension Cord Research

**Files:**
- Create: `docs/source-audits/2026-09-15-batch-01-cord-audit.json` (if needed)

- [ ] **Step 1: Research cord documentation for each board**

Check manufacturer product pages for each board. Most wall-mounted boards do not have suspension cords. Document the finding for each:

| Board | Likely Cord Status |
|---|---|
| deWoodstok Woodbord | Wall-mounted, no cord |
| Escape Unlimited | Wall-mounted, no cord |
| Evolv Basic Training Long | Wall-mounted, no cord |
| Metolius Wood Grips II Deluxe | Wall-mounted, no cord |
| Moon Armstrong | Wall-mounted, no cord |
| target10a Linebreaker BASE | Wall-mounted, no cord |

- [ ] **Step 2: Create cord audit records**

For each board without documented suspension, create a `noDocumentedSuspension` record in the cord audit format per `3D_SUSPENSION_AND_ODR.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/source-audits/
git commit -m "docs: add cord audit records for batch 01 boards"
```

---

## Task 16: Cleanup and Completion

**Files:** None (cleanup only)

- [ ] **Step 1: Remove staging GLBs and blends**

```bash
rm -rf .context/migration/source
rm -f .context/migration/*/source.blend
rm -f .context/migration/*/dewoodstok-woodbord.glb \
  .context/migration/*/escape-unlimited-board.glb \
  .context/migration/*/evolv-basic-training-board-long.glb \
  .context/migration/*/metolius-wood-grips-ii-deluxe.glb \
  .context/migration/*/moon-armstrong-ash.glb \
  .context/migration/*/target10a-linebreaker-base.glb
```

- [ ] **Step 2: Keep migration reports and manifests**

Retain `.context/migration/*/migration-report.json` and `.context/migration/*/contact-mapping.json` for audit trail.

- [ ] **Step 3: Final commit**

```bash
git add -A .context/migration/
git commit -m "chore: clean up migration staging artifacts"
```

- [ ] **Step 4: Verify completion criteria**

Run through the spec's completion checklist:
1. ✅ All 6 boards have model-only packages with valid USDZ + descriptor
2. ✅ Package validation passes
3. ✅ Contact bindings are correct
4. ✅ Hash integrity is verified
5. ✅ Suspension decisions are documented
6. ✅ No raster fallback remains
7. ✅ Model-tool tests pass
8. ✅ (Pending: native tests/build)
9. ✅ Source evidence is retained
10. ✅ Workspace cleanup is verified
