# Hangboard 3D Batch Migration — Design

## Scope

Migrate six hangboards from raster-only packages to model-only 3D packages
using GLB source models from `hangboards-batch-01-no-screwholes.zip`:

| Board | Slug | GLB Source | Current State |
|---|---|---|---|
| deWoodstok Woodbord | `dewoodstok-woodbord` | `dewoodstok-woodbord.glb` | PNG raster |
| Escape Unlimited | `escape-unlimited` | `escape-unlimited-board.glb` | PNG raster |
| Evolv Basic Training Long | `evolv-kilter-basic-long` | `evolv-basic-training-board-long.glb` | PNG raster |
| Metolius Wood Grips II Deluxe | `metolius-wood-grips-deluxe-ii` | `metolius-wood-grips-ii-deluxe.glb` | PNG raster |
| Moon Armstrong | `moon-armstrong` | `moon-armstrong-ash.glb` | PNG raster |
| target10a Linebreaker BASE | `target10a-linebreaker-base` | `target10a-linebreaker-base.glb` | PNG raster |

All GLBs are "no-screwholes" variants with mounting holes removed. Each includes
a `hold-map.json` mapping GLB object names to hold IDs, source geometry scripts,
renders, and validation data.

## Architecture

Each catalog package remains the authority for physical board identity and its
`contacts[]` inventory. The migration replaces the raster presentation with one
USDZ and a hash-bound descriptor generated from imported, importer-visible model
nodes. The descriptor is the only rendering, highlight, hit-testing, and
resolved-spatial-geometry source; raster assets and canonical paths are removed
from every migrated package.

The importer is supplied an explicit per-board source manifest and node-to-contact
mapping derived from the hold-map. It never infers bindings from mesh names or
source imagery. Non-contact geometry is tagged as `body`; absent, unsupported, or
ambiguous contacts fail the package rather than producing a fallback surface.

## Pilot Strategy

Start with two simpler boards to validate the pipeline:
1. **deWoodstok Woodbord** — long, simple board with continuous rim and discrete pockets
2. **Moon Armstrong** — classic fingerboard with well-documented hold types

After pilot validation, batch the remaining 4 boards.

## Per-Board Workflow

### Step 1: Extract and Prepare

Extract GLB, hold-map, source geometry, and evidence from the zip into
`.context/migration/SLUG/`. Read the existing `board.json` contacts inventory.
Cross-reference hold-map object names with contact IDs.

### Step 2: Build Contact Mapping Manifest

Create a JSON manifest mapping GLB object names → contact IDs and roles:

```json
{
  "packageID": "dewoodstok.woodbord",
  "sourceAsset": "dewoodstok-woodbord.glb",
  "sourceSHA256": "...",
  "mappings": [
    {
      "objectName": "hold-top-rim",
      "contactID": "top-rim",
      "role": "contact"
    },
    {
      "objectName": "body-mesh",
      "contactID": null,
      "role": "body"
    }
  ]
}
```

Use the hold-map's `holds[].objectName` and `holds[].holdId` as the primary
mapping source. Validate that every `contacts[].id` in `board.json` has a
corresponding GLB object.

### Step 3: Blender Import and Tag

Import the GLB into Blender using `import_contact_model_source.py` with the
contact mapping. Verify mesh tags are correctly applied (body, contact per
contact ID). Verify material assignments are preserved from the GLB.

### Step 4: Compile USDZ + Descriptor

Run `contact_model_package.py` to produce `primary.usdz` and `primary.model.json`.
Verify SHA-256 hash binding between descriptor and USDZ. Verify all contact nodes
are bound and bounds are correct.

### Step 5: Update board.json

Replace `media.type: "raster"` with `media.type: "model"`. Add `assetPath`,
`descriptorPath`, `display.camera`, and `suspension` (if applicable). Remove
`contactGeometry` (raster paths). Keep `contacts[]` factual inventory unchanged.

### Step 6: Suspension Cord Research

Check manufacturer evidence for cord/suspension documentation. Most hangboards
are wall-mounted without suspension cords. For boards without documented cords,
create a `noDocumentedSuspension` record in the cord audit with retained evidence
(product pages, photos) showing wall-mount-only use.

### Step 7: Validate

- `hangboard-packages.sh validate --root Hangboards --final-inventory`
- Model-tool pytest collection
- Package audit

## Evidence and Facts

Before import, retain and audit at least two materially distinct visual sources
per exact revision. Prefer the board's existing manufacturer source audit;
supplement with the downloaded model package's evidence only where its publisher,
URL, hash, review date, and supported facts are recorded.

Mounting screws and hardware are omitted from display models. Existing unsupported
model details are neither promoted into board facts nor made selectable.

## Package Contract

Each migrated package has exactly one default `media.type: "model"` presentation
with:
- `assetPath`: `assets/primary.usdz`
- `descriptorPath`: `assets/primary.model.json`
- `display.camera`: orthographic with board-appropriate view direction
- `suspension`: only if source evidence documents a cord

The descriptor binds importer-visible nodes to physical contact IDs. Model
packages contain no raster fallback.

## Completion Criteria

1. All 6 boards have model-only packages with valid USDZ + descriptor
2. Package validation passes: `hangboard-packages.sh validate --root Hangboards --final-inventory`
3. Contact bindings are correct: every `contacts[].id` maps to a USDZ node
4. Hash integrity is verified: descriptor SHA-256 matches USDZ bytes
5. Suspension decisions are documented: each board has a cord audit record
6. No raster fallback remains: no `primary.png` in any migrated package
7. Model-tool tests pass: pytest collection for model descriptor/package
8. Native tests/build pass: Swift tests and Xcode build succeed
9. Source evidence is retained: evidence files in `docs/source-audits/`
10. Workspace cleanup is verified: no orphaned staging artifacts
