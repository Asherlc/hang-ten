# Beastmaker 1000 canonical-render validation

Validated on 2026-08-04 against the authoritative Beastmaker product
photograph. The copyrighted source photo and generated review artifacts remain
untracked under `work/real-beastmaker/`; they are not distributed in the
package.

## Shipped rendering contract

The Beastmaker 1000 template has one reviewed visible product layer:
`src/hangboard_vectorizer/products/beastmaker-1000-render.png`. It is a
transparent RGBA canonical render, cleaned deterministically from the
authoritative real product photograph, then packaged with the template. Its
exact bytes are embedded as the only visible product layer in the SVG.

The source photo is used to identify the selected product and check alignment.
It is not traced, restyled, or otherwise used to create a run-specific visible
render. B/reference imagery and AI-generated imagery are not runtime inputs.
The 22 transparent vector paths above the raster remain the selectable and
highlightable grip regions.

## Source and tested revision

- Official product page: <https://www.beastmaker.co.uk/products/beastmaker-1000-series>
- Local validation input: `work/real-beastmaker/source.jpg`
- Source dimensions: 1080 x 318 pixels
- Source SHA-256: `17e9f743f6cbacf27092a5e5073b88633be4e282cc05a656151a4bde8203328f`
- Packaged visible asset: `beastmaker-1000-render.png`
- Packaged asset SHA-256: `4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627`
- Canonical asset dimensions/mode: 1000 x 259, RGBA
- Tested implementation revision: `e8fcdb6` (`test: guard against legacy split-center ids`)
- Initial documentation revision: `5dd7052` (`docs: validate deterministic beastmaker render`)
- Full verification: `234 passed`

This validation record's reviewed documentation lineage begins at `5dd7052`.
Its direct corrective follow-up only clarifies exporter behavior, proof-canvas
dimensions, and the recorded verification result; the follow-up cannot embed
its own commit hash without changing that hash.

## Conversion command and final artifacts

Run from the package root:

```bash
rtk env PYTHONPATH=src hangboard-to-svg ../../work/real-beastmaker/source.jpg \
  --product beastmaker-1000 \
  --output ../../work/real-beastmaker/product-render-proof-task4.svg \
  --manifest ../../work/real-beastmaker/product-render-proof-task4.json
```

The accepted, untracked review artifacts are:

- `work/real-beastmaker/product-render-proof-task4-normal.png`
- `work/real-beastmaker/product-render-proof-task4-center.png`
- `work/real-beastmaker/product-render-proof-task4.svg`
- `work/real-beastmaker/product-render-proof-task4.json`

The second PNG was captured after adding `active` to the one
`sloper-center` SVG path. It covers the entire continuous center top surface
and no other grip.

## Machine-checked result

- Product ID/template schema: `beastmaker-1000` / 1
- Embedded product renders: 1
- Manifest regions / SVG `.grip-region` paths: 22 / 22
- Region split: 17 `pocket`, 3 `sloper`, 2 `jug`
- `sloper-center` count: 1 in the template, SVG, and manifest
- Legacy split-center IDs: absent
- Manifest openings / SVG `.opening` paths: 0 / 0
- Ordered SVG/manifest ID parity: pass
- Render asset precedes all overlay paths in SVG order: pass
- Region sources: 22 `template`; all template `openingId` values are `null`
- Alignment method: `minimum-area-frame`
- Alignment aspect-ratio error: `0.01873207547169806` (1.8732%)
- Alignment confidence: `high`
- Alignment warning: `minimum-area rectangle fallback`

The minimum-area fallback is expected for the rounded outer silhouette in the
official front photograph. Its error is within the high-confidence band.

## Visual acceptance

The normal and active-state proof PNGs were reviewed on their 2800 x 1000
browser-capture canvases. The embedded asset and SVG viewBox remain the
canonical 1000 x 259. Acceptance confirms all 17 pockets, both extreme-corner
jugs, and the three top sloper sections. The center is one uninterrupted
double-width surface with no physical, visual, or semantic divider. The outer
slopers begin at the top contour and lower slightly farther than the center;
all pocket rows remain level. Subtle wood grain and cavity depth are present
in the packaged render without adding logos, screw detail, false openings, or
selectable background/perimeter features.

Visual acceptance: **pass**.

## V14 selectable-region promotion

The final selectable-region contract is recorded in
`docs/validation/beastmaker-staged-replay.md`. It promotes the accepted mixed
corner geometry for regions 01–05 and the accepted controlled pocket geometry
for regions 06–22, while retaining one center sloper and the reviewed packaged
raster. The production replay pins the V14 path-contract and generated-SVG
hashes, checks board containment for the outer jugs/slopers, and rebuilds all
standard highlight variants from the packaged paths.

## Repeatable onboarding

Another commercial model requires an authoritative product photo, a reviewed
template for its exact revision, complete selectable display paths and
metadata, and one reviewed transparent canonical render at the template's
canonical dimensions. Package the asset beside the template, declare it as
`renderAsset`, verify PNG/RGBA/dimension validation, then verify exact
SVG/manifest ID parity and active-state coverage. A product profile can be
exercised explicitly through the standalone deterministic height-field
renderer during development, but SVG conversion does not select it as a
fallback. Unreviewed photographic cleanup is never inferred at conversion
time.
