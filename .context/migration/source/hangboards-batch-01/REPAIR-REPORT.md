# Batch 1 revision 3 — all six exports present

**Six usable GLBs. Six PARTIAL entries. Zero EVIDENCE-BLOCKED entries.**

Evolv Long now has an actual model constructed from the four newly supplied front/rear/oblique/side views. The existing five production GLBs are unchanged byte-for-byte from revision 2. This revision does not retroactively certify their unresolved source details.

| Model | Status | Contacts | Triangles | Native .blend |
|---|---|---:|---:|---|
| deWoodstok Woodbord | PARTIAL | 17 | 42,000 | No |
| Escape Unlimited Board | PARTIAL | 7 | 36,000 | No |
| Evolv Basic Training Board (Long) | PARTIAL | 4 | 50,000 | No |
| Metolius Wood Grips II Deluxe | PARTIAL | 26 | 65,000 | No |
| Moon Armstrong | PARTIAL | 21 | 46,000 | No |
| target10a Linebreaker BASE | PARTIAL | 23 | 46,000 | No |

## New Evolv deliverables

The model has one independently selectable continuous jug, three independently selectable continuous rails, a separate nonselectable body, two actual recessed rear bays, a central spine, mounting bosses and eleven open mounting apertures. It contains no exterior screws, wall, cords, fake cavity caps or overlapping selector shells.

All four supplied source photographs are retained unchanged in its evidence directory. Eight actual GLB renders, an eight-view review sheet, a source-photo versus model comparison, four-contact evidence mapping, editable metre-scale PLY/NPZ geometry and executed numeric source are included. The 50,000-triangle export is 5.4 MB uncompressed.

Evolv source code was executed in a new directory containing only code and numeric configuration: no original GLB, mesh cache, or photos. It produced a byte-identical GLB. Ten model acceptance tests and the listed structural checks passed. The prior five source-rebuild receipts are preserved and hash-checked; they are not relabelled as new executions.

## What is not being claimed

The Evolv upper/middle/lower assignment of nominal 10/15/20 mm edges is photo-inferred, not a manufacturer-numbered map. Its exact rear wall thickness, local radii, mounting dimensions and casting surface are unmeasured display estimates. The manufacturer's metric and inch dimensions disagree; the model adopts the metric listing under an explicit ruling. These limits are why it remains PARTIAL rather than being sold as a fully source-verified dimensional replica.

The other five models retain their earlier source-coverage limitations. Native Blender remains unavailable: the installation attempt failed DNS resolution. No .blend or Outliner screenshot is claimed. The allowed genuine GLB + editable PLY/NPZ + executed-source fallback is delivered.

## Integrity and use

The exact six-entry manifest records every current path, contact count, triangle count and GLB SHA-256. Per-model and root checksum manifests cover the included files. The final archive is reopened and audited from clean extraction before delivery. The external verification receipt records the final ZIP's hash without circular hashing.

Open `index.html` to browse local previews and model links. `models/<slug>/<slug>.glb` is the integration asset. Source Z-up converts to glTF Y-up by `(x,y,z)->(x,z,-y)`; all assets are metre-scale. Reference photographs are research evidence, not commercially licensed application textures. These are display/interaction models, not manufacturing or load-bearing designs.

Recheck the extracted batch with:

```sh
python tools/audit_archive.py --tree . --report /tmp/batch01-check.json
```
