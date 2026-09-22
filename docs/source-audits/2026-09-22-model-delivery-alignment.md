# Exact model delivery alignment — 2026-09-22

## Authoritative files

The committed assets in PR #457 are the single source of truth. This aligns the
new download **to the branch**, not the branch to the earlier local export.
Asset commit: `54436b7fa4d3556a1627c628d3b236ee9afb1636`.
The alignment commit changes no USDZ, descriptor, board metadata, or repair code.

The earlier `hang-ten-all-models-no-screw-holes.zip`, SHA-256
`34772bb44c9b977652e399e5ffbd75838ac890ba8537851e62ca04fba5e2fc38`,
and its previews are superseded. They contain a different local repair variant.
The replacement is `hang-ten-pr-457-aligned.zip`, assembled by copying the
committed files; no model export is part of delivery packaging.

## Identity verification

All 40 complete model packages (40 USDZs, 40 descriptors, 40 board JSON files)
were compared with the Git objects of the asset commit. Each actual USDZ was
hashed to reconstruct its exact Git LFS pointer, including byte size. The
package trees reconstructed from these local files were then compared through
the GitHub Git-tree API. Replacing all 40 subtrees with the computed trees
returned the unchanged repository tree
`dbad9135f541443470b95c5a58ab84c9320234dc`.

The SHA-256 lock is `2026-09-22-model-delivery-lock.json` in this directory.
It pins the digest of the complete, path-sorted SHA256SUMS text for all 120
files. Both the repository and extracted download must pass the same check:

```sh
python scripts/verify-model-delivery.py --root .
```

The model pytest suite includes the lock check. It also checks that differing
bytes, missing files, extra models, unsafe/duplicate package names, and symlinks
are rejected. An intentional future model change must update the delivery lock
and publish a new matching download; do not silently refresh a stale lock.

## Preview and validation scope

Replacement previews are rendered from these exact committed USDZ files, not
from the superseded download. The download includes per-preview model and image
hashes. They are neutral, double-sided CPU mesh previews, not native application
screenshots or physical-material simulations. Runtime suspension cords and
instance duplication are not synthesized in these previews.

Alignment establishes file identity. It does not certify shape fidelity,
global watertightness, shading quality, native picking, or app readiness. The
previously noted visual concerns still need native review; this remains a draft
PR. No merge or auto-merge is authorized by this alignment.
