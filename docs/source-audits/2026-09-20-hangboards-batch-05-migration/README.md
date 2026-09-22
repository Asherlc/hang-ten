# Batch 05 migration evidence packet

Current status: all six migrated models and their actual iOS portrait/landscape,
selection, orbit and reset captures have passed controller Astra visual review.
See [native iOS acceptance](native/ios/README.md) and its
[hash-bound manifest](native/ios/manifest.json) for final package identities,
validation, cleanup and the pre-existing Android gate limitation. The source
packet and original-delivery claims below remain historical evidence.

The bounded migration design was approved in chat. **The user approved the exact 24 captures, 12 PDF views and all six cord exclusions on 2026-09-20**; see [the approval record](human-approval.json). This authorizes migration, not model acceptance. Start at [REVIEW.md](REVIEW.md). The initial evidence commits retained sources only. Subsequent migration work is documented under [native](native/README.md).

## Retained delivery

[source-delivery](source-delivery/) is a byte-for-byte subset of the local `hangboards-batch-05` delivery, revision `repair-v2`, which declares `PARTIAL` and `productionReady: false`. Original relative paths are preserved, including all six GLBs, root manifests/checksums/readme, per-board licenses, hold maps, grip usage, mounting interfaces, optimization, source registers, feature mappings and validation reports. These documents preserve historical claims; they are not an endorsement or proof of native acceptance.

All 237 entries of the original root checksum file were checked against the full local delivery before retention. The [retained-delivery manifest](retained-delivery-manifest.json) hashes all 107 retained files and enumerates intentionally omitted paths. Original root/per-board checksum files and `requiredPaths` still reference the full delivery; do not expect a full-delivery checksum command to succeed against this subset. Omitted files include redundant OBJ/NPZ/editable-source bulk and generated model renders. The retained source licenses govern delivered authored assets; they do not grant a license to manufacturer imagery. Manufacturer captures retain their publishers' rights and are evidence, not shipped app media.

## Manufacturer captures

[evidence/manifest.json](evidence/manifest.json) records all 24 original HTTP response bodies, canonical and fetched URLs, UTC timestamps, publisher, source tier, exact revision, support, caveats, sizes and SHA-256 hashes. [SHA256SUMS.txt](evidence/SHA256SUMS.txt) validates them. Exact requested query strings and image sizes were preserved; no substitute revisions, crops or re-encoding were used. The five product pages are HTML snapshots, not full offline website archives. Fifteen image originals were visually inspected. Four untouched PDFs have 12 selected full-page review renders, separately hashed in [render provenance](evidence/review-renders/manifest.json), using PyMuPDF 1.28.2 at 120 DPI; all 12 renders were inspected.

The delivery says primary binary downloads were unavailable. Those historical source registers are unchanged; the newly captured evidence fills this gap for the exact set listed in REVIEW. Historical conflict rulings (especially Natural 7.5 mm and Forge single IMR) remain unaccepted. No retailer evidence is needed for this proposed visual set.

## Original GLB hashes

| Source board | Contacts | SHA-256 |
| --- | ---: | --- |
| [frictitious-doormount-pro-7](source-delivery/models/frictitious-doormount-pro-7/frictitious-doormount-pro-7.glb) | 13 | `8b639807ff660566dca2fd313f00abfadaae0bfbaf0c28ecbc82477f2732113f` |
| [frictitious-megalith](source-delivery/models/frictitious-megalith/frictitious-megalith.glb) | 20 | `d8a9fb8c1f308d0d11e90f760e30f1cfde3bf36cb19b212ef24a368835adceb1` |
| [trango-rock-prodigy-forge](source-delivery/models/trango-rock-prodigy-forge/trango-rock-prodigy-forge.glb) | 22 | `cb905fe6eaac9161b40e8e0f5d972343e424925316bf15d76e59e4e033adeaba` |
| [trango-rock-prodigy-natural](source-delivery/models/trango-rock-prodigy-natural/trango-rock-prodigy-natural.glb) | 16 | `a9a2087a263fc08ea489947ad5d41edad36c7af210b734de0873edf927586b90` |
| [zlagboard-evo](source-delivery/models/zlagboard-evo/zlagboard-evo.glb) | 21 | `bf3c44e8538a22ffc5c86ca6b7410ce58b265dd33f70328c205490c3069d2f8b` |
| [zlagboard-pro-2-0](source-delivery/models/zlagboard-pro-2-0/zlagboard-pro-2-0.glb) | 28 | `e71482d155485acd5ad710f7fb8cf2ac2a055ef14a634a6026733f2e970f3b56` |

## Original migration checklist (historical)

1. Exact-evidence and six cord-exclusion approval recorded: user, 2026-09-20. Native/model acceptance remains separate.
2. Reconcile app/source contact counts (13/13, 18/20, 20/22, 14/16, 21/21, 28/28), especially Forge IM Deep/Shallow/IMR and overlapping pinches. Preserve stable identities and unsupported-depth omissions; keep Zlag board dimensions estimates.
3. Review and correct source geometry/materials after the gate: Natural thumb-support channel fidelity, dark/jagged crimp artifacts, mounting holes/hardware omission, and any other evidenced discrepancy. The six delivered GLBs remain immutable originals here.
4. Import through retained native tooling with explicit contact bindings, compile model-only USDZ/descriptor packages, and update the closed cord audit after approval. No routine changes.
5. Perform appropriate package, model, staging and native iOS tests/builds, plus current-source front/oblique/active-contact and picking review. None is claimed by this evidence-retention task.

All generated work uses workspace-owned paths. No server, simulator or other external resource was created by the evidence task. Recovery bookkeeping and dependency environment are local under `.context/hangboards-batch-05-astra-migration/`.

## Evidence-task verification

Verified all 107 retained delivery files byte-for-byte against the source, all six manifest GLB hashes, all 120 selectable GLB `holdId` values against the delivered hold maps, all 24 capture hashes, all 12 render hashes/source bindings, the 5/15/4 capture counts, and all local links authored in README/REVIEW. These are provenance checks, not geometry or app tests. At least two materially distinct visual references per revision are presented for human judgment.

The full staged `git diff --check` reports existing whitespace inside the five untouched manufacturer HTML snapshots and the original F3 PDF (which Git treats as text). Those exact source bytes are intentionally preserved; the check passes for every authored document/manifest. No production test suite or native acceptance is claimed by this evidence task.
