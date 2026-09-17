# Hangboard 3D batch 02 migration records

Retained evidence for migrating six raster-only hangboard packages to model-first
3D packages from `hangboards-batch-02.zip` (delivery revision
`foundry-verification-inset-selections-browser-tests-20260916`).

## Scope

| Zip slug | App package | Delivered regions | Action |
|---|---|---:|---|
| `escape-beta-board` | `escape-beta-22` | 18 | Re-authored to the manufacturer's 22 numbered positions. |
| `metolius-foundry` | `metolius-foundry` | 18 | Mapped 1:1 by manufacturer number. |
| `nature-climbing-stoak-board-iii` | `nature-stoak-board-iii` | 7 | Mapped by geometry. |
| `so-ill-iron-palm-2-0` | `soill-iron-palm-2` | 8 | Mapped; second rail corrected to the manufacturer's 35 mm. |
| `so-ill-split-palm` | `soill-split-palm` | 14 | Adopted the manufacturer's 7 regions per unit. |
| `mammut-diamond-finger` | `mammut-diamond-finger` | 16 | Adopted the model's stable regions (manufacturer publishes no numbered inventory; user-approved as best available). |

## Independent source verification

`evidence/FINDINGS.md` records an independent re-check of the delivered region
inventories against manufacturer sources (all re-fetched HTTP 200 and retained in
`evidence/` with hashes in `evidence/SHA256SUMS.txt`). Key verdicts:

- **Escape Beta**: the manufacturer's numbered diagram prints labels 1–11 on both
  left and right, i.e. 22 positions. The delivered GLB merges thin+wide pinch per
  side and the 50/31 mm sloper rails into single centre regions (18), so it was
  re-authored to 22.
- **Metolius Foundry**: numbered diagram = 7 bilateral pairs + 4 centre = 18;
  delivered GLB and app agree.
- **Iron Palm 2.0**: manufacturer specifies crimp rails 40 / **35** / 15 mm; the
  app's `flat-edge-25` label was corrected.
- **Split Palm**: manufacturer specifies 7 named regions per unit; the app
  over-split the smaller sloper and its connected pinch.
- **Stoak Board III**: manufacturer does not enumerate regions; delivered count
  (7) matches the app, mapped by geometry.
- **Mammut Diamond Finger**: no numbered manufacturer inventory exists; the
  delivered GLB is explicitly non-exhaustive.

## Source provenance

`source-delivery/*.glb` are the delivered GLBs, verified against
`batch-manifest.json` `glbSha256`. They were normalized in Blender for compiler
import (coordinate-wrapper empties baked into meshes; every material given a
solid-color image so the existing `contact_model_package.py` image-material
requirement is satisfied). The supplied `source/rebuild.py` could not reproduce
even the unmodified GLB on this host (float32 UV precision failure), so the
migration normalized the delivered bytes rather than regenerating geometry.
