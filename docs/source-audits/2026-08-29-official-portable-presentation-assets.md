# Official portable presentation assets — source audit

Reviewed 2026-08-29. This audit covers only the five presentation assets
integrated for the Frictitious Port-A-Board and the large and small Lattice
MXEdge Lift packages.

## Ingest contract

Each candidate was downloaded unchanged from the exact first-party asset URL
recorded by
`.context/pretty-impala-official-asset-sources/official-asset-source-manifest.json`.
ImageMagick 7.1.2-21 decoded each JPEG and encoded its pixels as a stripped
24-bit sRGB PNG with this command shape:

```sh
rtk magick <official-source.jpg> -strip PNG24:<tracked-presentation.png>
```

No crop, resize, compositing, masking, generation, registration, source
alignment, vectorization, detection, or automatic path authoring was used.
For every row, `magick compare -metric AE <input.jpg> <output.png> null:`
reported `0 (0)`, establishing that the decoded input and output pixels are
identical. Every full image is square, so the board and presentation aspect
ratios are `1.0`.

## Per-view provenance

| Package / view | Product page | Exact first-party asset | Input JPEG | Output PNG | Evidence role | Non-evidence role |
| --- | --- | --- | --- | --- | --- | --- |
| `frictitious-port-a-board` / `primary` | [The Port-A-Board](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard) | [PAB-Front.jpg](https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840) | SHA-256 `1509f81ed1dcf960a8ee1e91424e538de5aa890698b351a12fe2f1c36e4859e1`; 1440 × 1440 | `Hangboards/frictitious-port-a-board/assets/primary.png`; SHA-256 `13bef16f346030dbe383d320beedc4034ae2da6c82b122ed8b349590132c0a17`; 1440 × 1440 | Exact current-revision frontal manufacturer packshot and direct visual evidence for the front contact layout. | It is not generated geometry, a training prescription, or evidence for facts absent from the product page. |
| `frictitious-port-a-board` / `back` | [The Port-A-Board](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard) | [PAB-Back.jpg](https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840) | SHA-256 `38522abf6ccfa4a0f18dac57e5bbbf9a6290de4cd6a030756248f1a0314f70f4`; 1440 × 1440 | `Hangboards/frictitious-port-a-board/assets/back.png`; SHA-256 `5c4e9f36a31311ea2d88cd58a2acc441898fef28182dc5ed74e0b1ae48bc0092`; 1440 × 1440 | Exact current-revision reverse manufacturer packshot and direct visual evidence for the four stepped reverse contacts. | It is not generated geometry, a training prescription, or evidence for facts absent from the product page. |
| `frictitious-port-a-board` / `side` | [The Port-A-Board](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard) | [PAB-Side.jpg](https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840) | SHA-256 `61221d7cb34edf3c5fd13e2300045050a0d7149424be9c5bcf8ded6c021df8e7`; 1440 × 1440 | `Hangboards/frictitious-port-a-board/assets/side.png`; SHA-256 `ff23a2bbeb4b7d08ae530775a7ec7c328474b9e5b19db99fc4f9b126aeb45866`; 1440 × 1440 | Exact current-revision end-on manufacturer packshot and direct visual evidence for the body-pinch silhouette. | The printed side logo is not a separate hold, and the image is not evidence for unsourced coaching semantics. |
| `lattice-mxedge-lift-large` / `primary` | [MXEdge Lift](https://latticetraining.com/product/mxedge-lift/) | [MXL-Front.jpg](https://latticetraining.com/app/uploads/2024/04/MXL-Front.jpg) | SHA-256 `0811e08f36674e305d7c31c56a78bc3c77225b28ac41fa999170f9e55ec9aee8`; 1000 × 1000 | `Hangboards/lattice-mxedge-lift-large/assets/primary.png`; SHA-256 `091078ab355d81fbc109fe04065b39b2ccc5f4eb79093c5de215347d2789b8a3`; 1000 × 1000 | Exact large-SKU frontal manufacturer packshot and direct visual evidence for three edge regions plus the mono. | The printed `12`, `16`, `22`, `28`, and `MXL` markings are labels, not selectable holds; the image does not add unsupported training semantics. |
| `lattice-mxedge-lift-small` / `primary` | [MXEdge Lift](https://latticetraining.com/product/mxedge-lift/) | [MXS-Front.jpg](https://latticetraining.com/app/uploads/2024/04/MXS-Front.jpg) | SHA-256 `d71bb25739c647a8f686671c55623358f5381efbf06145d98d7fe4468fc1c1cb`; 1000 × 1000 | `Hangboards/lattice-mxedge-lift-small/assets/primary.png`; SHA-256 `6a0d7b0167a53d54b2849773000512d12c1343107fe01d16af4d81a7559cd822`; 1000 × 1000 | Exact small-SKU frontal manufacturer packshot and direct visual evidence for three edge regions plus the mono. | The printed `8`, `14`, `18`, `25`, and `MXS` markings are labels, not selectable holds; the image does not add unsupported training semantics. |

## Manual canonical-geometry review

Every presentation-scoped geometry piece was deliberately reviewed and
re-framed by an operator against the exact full packshot above. No coordinates,
contours, masks, or hold proposals were extracted from image pixels. Stable
hold IDs and the frozen physical inventories were preserved.

- Port-A-Board front: `edge-20`, `edge-25`, and `edge-30` remain distinct
  routed contact regions; `pocket-30-two-finger-mono` remains the separately
  marked lower two-finger/mono contact; and `jug-outer-rim` follows the top
  rounded rail. The two 30 mm records do not collapse into one overlay.
- Port-A-Board back: the paths follow the printed depths from top to bottom:
  `edge-15` occupies the upper recessed floor below the rounded outer rail,
  `edge-12` occupies the broad middle floor above the lower routed opening,
  and `edge-8` and `edge-10` occupy the opening's upper and lower stepped
  floors. The rope and grommets do not define contacts; where the rope visibly
  crosses the upper continuous floors, it is only packshot occlusion over the
  underlying wood contact.
- Port-A-Board side: `pinch-body` follows the narrow rounded wooden side face,
  excluding the rope. Its existing rounded-rectangle constraint was
  deliberately retained for that genuinely regular silhouette.
- MXEdge Lift large: `edge-12` and `edge-16` are separate upper edge bands;
  `edge-22` follows the lower edge region without absorbing `mono-28`; and the
  mono is a deliberately selected circle. The printed size and `MXL` labels
  remain outside the paths.
- MXEdge Lift small: `edge-8` and `edge-14` are separate upper edge bands;
  `edge-18` follows the lower edge region without absorbing `mono-25`; and the
  mono is a deliberately selected circle. The printed size and `MXS` labels
  remain outside the paths.

The constrained pill paths used for regular edge bands remain the saved
canonical rendering, highlighting, and hit-testing source of truth. Constraint
metadata records the operator-selected editing behavior only. The review used
the Trango Rock Prodigy Pivot package as the precedent for economical smooth
closed paths and did not copy any Trango product geometry.
