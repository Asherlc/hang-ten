# Zlagboard native migration, 2026-09-20

The user approved the exact evidence set and all six cord exclusions on
2026-09-20; [human-approval.json](../human-approval.json) binds those original
bytes and PDF views. This record covers the first two package migrations only.
Neither that approval nor these native transport checks constitutes app/model
acceptance. No routines changed.

## Physical facts and explicit mapping

E1 is the current shared manufacturer product page; E2/E3 establish the two-row
Evo and P2/P3 establish the three-row Pro 2.0 (not Pro 1). See the original URLs,
SHA-256 values and caveats in [the evidence manifest](../evidence/manifest.json).
The source diagrams and front photos were directly inspected before mapping.

Both mappings preserve every existing contact object, its fields, and its order
byte-for-byte at the JSON value level against base `8248d8d4`. The Pro top-band
app order differs from delivery order; mapping is explicit by physical semantics.
The package identities stay `zlagboard.evo` and `zlagboard.pro`; Pro remains named
`Zlagboard.Pro 2.0`. The following positions are read left to right:

| Diagram region | Source semantics | Stable app contact IDs |
| --- | --- | --- |
| Top, both boards | Jug, 32°, 20°, sloper jug, 20°, 32°, jug | top-jug-left; top-sloper-32-left; top-sloper-20-left; top-sloper-jug-center; top-sloper-20-right; top-sloper-32-right; top-jug-right |
| Row 1, both | 30 mm edge; sloper 30; sloper 25; 35 mm edge; sloper 25; sloper 30; 30 mm edge | edge-30-left; sloper-edge-30-left; sloper-edge-25-left; edge-35-center; sloper-edge-25-right; sloper-edge-30-right; edge-30-right |
| Row 2, both | 20 mm edge; sloper 25; 30 mm edge; sloper 30; 30 mm edge; sloper 25; 20 mm edge | edge-20-left; sloper-edge-25-lower-left; edge-30-inner-left; sloper-edge-30-center; edge-30-inner-right; sloper-edge-25-lower-right; edge-20-right |
| Row 3, Pro only | incut 15; 15 mm edge; incut 30; incut 10; incut 30; 15 mm edge; incut 15 | edge-incut-15-left; edge-15-left; edge-incut-30-left; edge-incut-10-center; edge-incut-30-right; edge-15-right; edge-incut-15-right |

The numerical board-only dimensions formerly displayed by the app lacked support
in this approved exact-revision set and were removed. Model envelopes remain
**display estimates**: Evo 700 × 120 × 42 mm; Pro 705 × 152 × 42 mm. They are not
manufacturer dimensions. Cavity widths, offsets, radii, floors/sections and
front/rear thickness are estimated authored geometry, even where diagram nominal
hold depths are factual. No finger capacities or training prescriptions were added.

## Preparation and omissions

[prepare_zlagboards.py](prepare_zlagboards.py) verifies the two immutable original
GLB hashes before importing. GLB's root maps its authored Z-up/front−Y coordinates
to glTF Y-up/front+Z in metres. Blender's native GLB import converts back to its
Z-up basis. The explicit preparation bakes each evaluated world matrix into its
mesh once, removes only the two transform-only empties, and checks zero world
vertex displacement. There is **no extra axis rotation or scale conversion**.
The unchanged compiler later converts Blender coordinates to the descriptor's
Y-up/front+Z basis and checks the actual exported/reimported bounds.

Both Zlagboard sources already omit the metal mounting frame, phone holder,
phone-retention bands, screws and mounting holes, as confirmed in their retained
mounting interfaces and source builder. No mounting topology was deleted, filled,
or inferred. These display omissions do not assert the physical products lack
mounting components. No cords are baked into the model or declared in metadata.
The approved E1/E3 and E1/P3 exclusions were registered in the closed live cord
audit. Exact evidence bytes were copied into its required snapshot directory;
source URLs, hashes and independent noDocumentedSuspension facts are retained.

Source PBR material is a constant linear RGBA with roughness 0.78 and metallic 0.
An explicit constant image adaptation makes it compatible with the native
compiler's image-material requirement; there is no generated wood grain, UV
inference or manufacturer-photo texture. The final image is PNG RGBA8 sRGB `[223, 203, 177, 255]`; the
maximum linear-channel quantization error is 0.003267 (tolerance 0.004).
Preparation records bind its exact bytes. PNG matches the established catalog
transport convention; the earlier EXR trial was not claimed invalid. The geometry is unchanged by this step or the importer. Shape work
has not been hidden inside either production transporter.

## Reproduce and inspect

Run from the repository root with Blender 5.2.0 LTS. Set Blender config/cache/tmp
under `.context/hangboards-batch-05-astra-migration/blender/` as in the original
execution. The preparation script writes generated blends to the owner-specific
`.context/.../prepared/` directory and updates the hash-bound derivative manifests.
Prepared blends are generated output, not original user-delivery assets.

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python docs/source-audits/2026-09-20-hangboards-batch-05-migration/native/prepare_zlagboards.py \
  -- zlagboard-evo zlagboard-pro-2-0
```

For each board invoke the **unchanged**
`Tools/HangboardModels/import_contact_model_source.py` in Blender with:

| Argument | Evo | Pro 2.0 |
| --- | --- | --- |
| `--manifest` | native/zlagboard-evo/source-manifest.json | native/zlagboard-pro-2-0/source-manifest.json |
| `--mapping` | native/zlagboard-evo/contact-mapping.json | native/zlagboard-pro-2-0/contact-mapping.json |
| `--package` | zlagboard.evo | zlagboard.pro |
| `--board-json` | Hangboards/zlagboard-evo/board.json | Hangboards/zlagboard-pro/board.json |

Manifest/mapping paths above are relative to this audit directory; other paths
are relative to the repository root. Provide a fresh workspace-owned
`--output-directory` and `--report`. Copy only the two compiled assets into the
corresponding package. Import calls `contact_model_package.py`, which exports the
USDZ, imports that exact asset into an empty scene, checks image materials,
triangles, source-node correspondence, unchanged logical bindings and bounds,
and generates the canonical hash-bound descriptor from importer-visible triangles.
The per-board import and verification reports bind the shipped bytes to that run.
Blend file hashes are per-run provenance; Blender save metadata can vary between
runs, so rerunning preparation refreshes its derivative manifest.

## Review boundary

Controller Astra reviewed all four clean-reimport USDZ renders in workspace
`.context/hangboards-batch-05-astra-migration/renders/` against E3/P3 and the
approved diagrams: row inventories, top surfaces, handedness and overall forms
read coherently; no jagged crimp-style artifacts were visible. Bright studio
renders do not establish final SceneKit appearance. Their local provenance binds
them to the exported USDZ SHA-256 values. Final current-source iOS visuals,
materials, nearest-contact picking, highlights and reset interactions remain a
separate batch acceptance task. No native app acceptance is claimed here.
