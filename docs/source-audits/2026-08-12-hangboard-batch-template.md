# Hangboard batch source-audit template

Use this document for a single source-backed authoring batch. It is
documentation only: it is not runtime content, a package sidecar, or a
lifecycle, confidence, approximation, or review-state record.

Set `checkedAt` in each completed package's `evidence.json` to the ISO calendar
date on which its listed source URLs were checked. Capture the direct HTTPS URL
for every official manufacturer source used, including the product page, front
image, oblique image where needed, and hold guide, depth diagram, manual, or
measurement source. Do not prescribe or copy a board value unless the cited
official source supports it.

## Candidates

| slug | catalog id | official product URL | official front image URL |
| --- | --- | --- | --- |

## Evidence coverage

| hold field or artwork element | official source URL | package evidence key | representation method |
| --- | --- | --- | --- |

The completed package must use exact evidence maps: `fieldEvidence` covers
every factual field in `board.json`; `holdEvidence` covers every
`<hold-id>.<field>`; `semanticEvidence` covers every semantic ID;
`artworkEvidence` covers the silhouette, every layer, and every hold piece;
and `assetEvidence` covers `assets/primary.png` plus an optional unchanged
source photo. The registered package has exactly `board.json`, `evidence.json`,
`semantics.json`, and `artwork.json`, with `assets/primary.png` as its only
generated raster.

## Evidence blockers

For every candidate that cannot be fully authored, use this exact record and
leave its existing directory unregistered with only `assets/primary.png`:

### `manufacturer-model`

Missing official evidence: no manufacturer hold guide or measurement supports
`fingerCapacity`, `gripType`, and each physical hold boundary. The product page
and front image establish identity and silhouette only. No `board.json`,
`semantics.json`, `artwork.json`, `evidence.json`, or catalog entry was added.
