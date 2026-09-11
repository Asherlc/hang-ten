# Training Tiles • So iLL x Meagan Martin

Image-based display reconstruction of the manufacturer's mirrored urethane tiles. **Blender 4.2.0.** The user confirmed there are no cords; no cord geometry or cord markers are included. The fourth render is a hold close-up.

## Files

- `Training-Tiles.blend` — display model, 442,692 triangles for the pair; all geometry modifiers applied.
- `Training-Tiles-editable.blend` — dense editable mesh source, 2,012,240 triangles; same separate body/hold structure.
- `Training-Tiles.glb` — self-contained glTF export with the same object IDs and per-hold materials. Conversion to the app's preferred iOS format remains app-side.
- `hold-map.json` — object IDs, grip descriptions, published dimension targets and estimation status.
- `renders/` — front, back, oblique, hold detail, independent-highlight check and actual Blender outliner screenshot.
- `source/` — reconstruction scripts, traced reference photograph, geometry data and source record. `qa/validation.json` records asset checks.

## Coordinates and integration

Meters, Z up; X runs right and +Y points toward the mounting surface. The rear plane is Y=0 and the front projects into −Y. The origin is midway between the tiles at their bottom/back plane. All object transforms are identity. Each tile targets the manufacturer's approximate **0.3556 m width × 0.2032 m height**, with about **0.0762 m maximum projection**. The **0.026 m gap is a display arrangement**, not a specified installation spacing.

Nonselectable objects are `body-L` and `body-R`, inside collections `Tile L` and `Tile R`. Every listed hold is an independent mesh and has its own material. Highlight by object/node ID; do not join meshes or deduplicate materials during conversion. glTF applies its normal Z-up → Y-up coordinate conversion on export.

Hold meshes contain actual contact-surface triangles, including rounded lips where appropriate. Their boundaries are open individually but meet the body exactly; the assembled tiles are closed surfaces. They are not overlapping highlight shells. Body meshes retain the connecting ribs, returns, mounting bores, rear faces and lettering.

## Hold mapping

“Outer” is away from the center gap; “inner” is toward it. Left/right refers to the front view. The inventory follows the manufacturer's pocket, two slopers, two middle edges and three bottom edges per tile.

| Grip | Left object and mesh ID | Right object and mesh ID |
|---|---|---|
| Open pocket | `hold-L-pocket` | `hold-R-pocket` |
| Upper outer sloper | `hold-L-sloper-outer` | `hold-R-sloper-outer` |
| Upper inner sloper | `hold-L-sloper-inner` | `hold-R-sloper-inner` |
| Middle outer positive edge | `hold-L-edge-middle-outer` | `hold-R-edge-middle-outer` |
| Middle inner positive edge | `hold-L-edge-middle-inner` | `hold-R-edge-middle-inner` |
| Bottom outer flat edge | `hold-L-edge-bottom-outer` | `hold-R-edge-bottom-outer` |
| Bottom center flat edge | `hold-L-edge-bottom-center` | `hold-R-edge-bottom-center` |
| Bottom inner flat edge | `hold-L-edge-bottom-inner` | `hold-R-edge-bottom-inner` |

## Sources and uncertainty

Primary evidence: [manufacturer product page and specifications](https://soillholds.com/products/training-tiles-so-ill-x-meagan-martin), its front/oblique/detail photos, and [manufacturer-hosted rotation sequence](https://embed.imajize.com/1171473). Accessed 2026-09-11. The storefront does not provide a revision code. Detailed URLs and conflicts are in `source/references.md`.

**This is a fitted visual reconstruction, not factory CAD.** The grip inventory and available dimension values are sourced; exact contours, fillets, tapered pocket sections, hole diameters/countersinks, wordmark outlines and unseen rear details remain estimates. The holes follow ten visible screw positions per tile; no hardware is included. The material is a plain rough PBR approximation of Emerald urethane, without scanned microtexture.

The manufacturer's inch/mm values differ slightly; listed millimeters take priority. The sources do not explicitly map every numerical depth to a pictured position. Per-position assignments in JSON are therefore marked inferred from oblique views, and dimensions are excluded from the stable IDs. Positive-edge rake is fitted with a small 1.5 mm rise, not asserted as a published angle. Curved contact geometry should not be treated as a measured training-device calibration.

## Materials, licenses and verification

No external image textures, linked assets, live modifiers, geometry nodes, cameras, lights, mounting hardware or environment geometry are saved in either `.blend`. No `textures/` directory is necessary. Render cameras/lights were temporary and were created after saving the clean files.

Reference photography is copyright So iLL and is supplied in `source/` for traceability, not as a licensed application texture. Brand/design rights remain with their owners. The geometric wordmark approximation uses DejaVu Sans outlines under the Bitstream Vera/DejaVu font license; no font file is embedded. The models have no font dependency.

Validation checks named meshes, independent materials, meter scale, applied transforms, nominal bounds, joined-boundary continuity, absence of duplicate faces and preservation of IDs in the GLB. No on-device iOS performance test was run.
