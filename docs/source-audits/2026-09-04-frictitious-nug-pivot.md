# Frictitious NUG pivot presentation audit

Reviewed 2026-09-04 against the current [Frictitious NUG product page](https://frictitiousclimbing.com/products/the-nug) and its first-party product imagery. The manufacturer evidence establishes one portable board with two physical recessed faces: a 20/25 mm face and an 8/13 mm face. Each face is represented by one transparent canonical raster; the opposite usable edge is a metadata-only 180-degree rotation of that same raster.

The two canonical rasters were generated as head-on, cord-free catalog art with the exact corresponding manufacturer packshot and the locked first-party reference set supplied to the generator. Dynamic black cord is rendered separately from the face art. The board body and attachment points rotate together while the pull point remains world-up, keeping both strands tensioned under gravity.

## Face and position mapping

| Presentation | Canonical physical face | Clock-face rotation | Available holds |
| --- | --- | ---: | --- |
| `primary` | 20/25 mm face (`assets/primary.png`) | 0° | `edge-25`, `jug-40`, `pinch-60` |
| `primary-inverted` | source `primary` | 180° | `edge-20`, `jug-40`, `pinch-60` |
| `reverse` | 8/13 mm face (`assets/reverse.png`) | 0° | `edge-13` |
| `reverse-inverted` | source `reverse` | 180° | `edge-8` |

The primary asset is 1536 × 1024 RGBA with SHA-256 `f733a692c345d1e05e512f5301d91e606fc1a26388e31b4b8d62f76f5d4dfc48`. The reverse asset is 1722 × 913 RGBA with SHA-256 `8efe4199240dd8d151bf0fca2c63b3f34028e40a854da20b4fd1f183872c6171`. Both have fully transparent corners and clear padding around the subject.

## Approved standalone renders

| Position | Review asset | SHA-256 |
| --- | --- | --- |
| 25 mm | `review-assets/2026-09-04-nug-dynamic-cord-25mm-approved.png` | `efa1dfef3a44c565fb35de85b6d2a5e137f29d1a6876dbbf61a50ae16d776cd5` |
| 20 mm | `review-assets/2026-09-04-nug-dynamic-cord-20mm-approved.png` | `5402da2e9d397349beebc8db63324ee2c9a2439a62f117a024b7f56203ba911c` |
| 13 mm | `review-assets/2026-09-04-nug-dynamic-cord-13mm-approved.png` | `e2190b4f307e29ffdefbe665ce06ea856ba78439750c66a2b291327f8befae56` |
| 8 mm | `review-assets/2026-09-04-nug-dynamic-cord-8mm-approved.png` | `b945f8e08997b67171b6f243cf96494756eb49dca34b72981aacc876256e57f2` |

All four approved files are standalone 1200 × 1464 RGBA renders with transparent backgrounds, complete support loops, and transparent margins on every side. They are not app screenshots or contact sheets.

## Geometry boundary

This migration does not alter any canonical hold path. In particular, `jug-40` and `pinch-60` retain their previously manually authored geometry; their alignment remains a known follow-up caveat and was not inferred, regenerated, or re-authored from these images. The image approval covers the canonical face art, physical-face mapping, rotations, and tensioned-cord presentation only.
