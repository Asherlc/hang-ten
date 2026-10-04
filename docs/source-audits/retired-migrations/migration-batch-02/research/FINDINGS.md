# Batch 02 — independent contact-inventory verification

Independent manufacturer-source check of the six batch-02 GLB region inventories
(`hold-map.json`) against the app's current `board.json` inventories. All source
artifacts were re-fetched (HTTP 200) and retained under `evidence/` with hashes in
`SHA256SUMS.txt`. This check does not rely on the batch-02 package's own claims.

| App package | Manufacturer evidence | Manufacturer region count | Zip model | App inventory | Verdict |
|---|---|---:|---:|---:|---|
| `escape-beta-22` | Escape numbered breakdown, labels 1–11, every number printed on both left and right | 22 (11×2) | 18 | 22 | **Zip denied.** GLB merges thin+wide pinch per side (1+2) and 50/31 mm sloper rails (9,10) into single centre regions. Manufacturer numbering supports the app's 22. |
| `metolius-foundry` | Metolius numbered diagram: 1–7 bilateral pairs, 8–11 centre | 18 | 18 | 18 | **Both confirmed.** Zip and app agree with the diagram; IDs differ but map by number. |
| `nature-stoak-board-iii` | Page names top jug, centre 22 mm edge, magnetic 5 mm inserts; no numbered inventory | not enumerated | 7 | 7 | **Inconclusive.** Counts agree; partitions differ. Neither is manufacturer-enumerated; decide by geometry/visual review. |
| `soill-iron-palm-2` | soill.ca spec: 2 big slopers, pinches, top jug rail, crimp rails 40 / 35 / 15 mm | 8 | 8 | 8 | **Zip confirmed.** App's second rail label (`flat-edge-25`, 25 mm) is **denied**; manufacturer says 35 mm. |
| `soill-split-palm` | soill.ca spec: 7 named regions per unit; rails 38.1 / 25.4 / 12.7 mm | 14 (7×2) | 14 | 16 | **Zip confirmed.** App over-splits the "Middle Smaller Sloper" and its connected pinch into two contacts. |
| `mammut-diamond-finger` | Manual + catalog photo: no numbered inventory; zip itself marks its 16 as non-exhaustive | not published | 16 | 21 | **Unresolved.** No independent authority. Zip is explicitly partial; app is an authored 21. |

## Consequences for migration

The repo importer requires an exact bijection between `board.json` contacts and
GLB contact nodes, so a board can only be migrated with a model whose region
inventory is at least as fine as the app's.

- **`escape-beta-22`** — the supplied GLB cannot represent the manufacturer's 22
  positions. Migrating would reduce a source-confirmed inventory to 18.
- **`mammut-diamond-finger`** — the supplied GLB has 16 regions and is
  self-declared incomplete; the app has 21. Migrating would drop regions with no
  source basis for doing so.
- **`metolius-foundry`, `soill-iron-palm-2`, `soill-split-palm`,
  `nature-stoak-board-iii`** — model inventory is source-consistent (Stoak by
  count, pending geometric mapping). These can migrate, correcting the Iron Palm
  rail label to 35 mm and Split Palm's over-split to the manufacturer's 7/unit.