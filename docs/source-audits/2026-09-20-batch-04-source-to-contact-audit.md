# Batch 04 Source-to-Contact Audit

Status: approved source-audit handoff for Tasks 8–13. The machine-readable
source register is [`2026-09-20-batch-04-3d-source-register.json`](2026-09-20-batch-04-3d-source-register.json).
This audit maps primary evidence to canonical contacts; it does not authorize
pixel-derived geometry, hidden topology, hardware, or training instructions.

## Retained source delivery

The six delivered GLBs and their exact batch checksums are retained below
`2026-09-20-hangboards-batch-04-model-imports/source-delivery/`. They are
source material, not promoted model packages. In particular, the Pivot GLB is
retained as `trango-rock-prodigy-pivot-rejected.glb`: it has isolated-proud
collars/rails, a narrow fin in place of the broad integrated wing, local
wing-root normal defects, and six unwanted fastener holes. It must not become
production geometry.

All twelve delivered source-register/media-manifest JSON files are copied
byte-for-byte to that evidence tree. Penta's two locally supplied full-image
originals have exact hashes, but their original binary URLs were not recovered:
their `binaryURL` remains `null` and their status is `unhashed` rather than an
invented URL.

## Contact normalization

### Crimptonite Helium Mobile

| Source feature | Canonical contact | Ruling |
| --- | --- | --- |
| Front 14 lip / reverse 14 lip | `edge-14` | Both visible lips are one physical contact. |
| Front 22 lip / reverse 22 lip | `edge-22` | Both visible lips are one physical contact. |
| Centre 10 / centre 18 | `center-edge-10` / `center-edge-18` | Preserve distinct maker nominal depths. |
| Top jug / rear jug-sloper | `top-jug` / `back-jug-sloper` | One continuous smooth rear contact, not an invented groove. |

The two visible end openings support only a transient `pairedLeadCord`; no
interior passage or `twoBranchCord` is claimed.

### Metolius Light Rail 2.0

| Approved manufacturer feature | Canonical contact |
| --- | --- |
| 40/20 upright side | `jug-40-20mm-side` |
| 20 edge | `edge-20` |
| 40/15 inverted side | `jug-40-15mm-side` |
| 15 edge | `edge-15` |

Use current manufacturer 40/20/40/15 labels rather than the conflicting
retailer 40/26/19/15 listing. The visible upper entry regions support exterior
paired leads only. There is no evidence for an underside mouth or hidden
vertical bore; old face screws are omitted as mounting hardware.

### Metolius Rock Rings 3D

| Unit-local slot | Left canonical contact | Right canonical contact |
| --- | --- | --- |
| `jug` | `jug-left` | `jug-right` |
| `pocket-40` | `pocket-40-four-left` | `pocket-40-four-right` |
| `pocket-32` | `pocket-32-three-left` | `pocket-32-three-right` |
| `pocket-25` | `pocket-25-two-left` | `pocket-25-two-right` |

Each physical ring owns its own `pairedLeadCord` and invisible anchor. Retain
the observed roof exits and lateral windows, but do not join units, infer an
interior route, or restore the disproved central through-bore.

### Owl Climb Poker

| Approved photo | Canonical face prefix |
| --- | --- |
| `owlclimb_poker19_0.jpg` | `face-a` |
| `owlclimb_poker19_1.jpg` | `face-b` |
| `owlclimb_poker19_2.jpg` | `face-c` |
| `owlclimb_poker19_3.jpg` | `face-d` |

Each direct batch patch retains its same-face canonical prefix. The approved
batch correction restores exactly `face-d-left-deep-rounded-recess` and
`face-d-right-deep-rounded-recess`; no other contact restoration is authorized.
Poker has `noDocumentedSuspension` and is excluded from cord presentation.

### YY Vertical Penta Evo

| Unit-local slot | Left canonical contact | Right canonical contact |
| --- | --- | --- |
| `edge-25` | `edge-25-left` | `edge-25-right` |
| `edge-20` | `edge-20-left` | `edge-20-right` |
| `edge-15` | `edge-15-left` | `edge-15-right` |
| `edge-10` | `edge-10-left` | `edge-10-right` |
| `mono` | `mono-left` | `mono-right` |
| `duo` | `duo-left` | `duo-right` |
| `tray` | `tray-left` | `tray-right` |

The manufacturer installation source establishes two independent exterior
loops around the upper band through the existing central ring. Do not invent a
channel or knot. The restored full originals disprove the old lower-band small
passage interpretation, so retired small passage holes remain absent.

### Trango Rock Prodigy Pivot

The normalized half inventory is nine physical contacts. Each source patch
maps identically to the left and reflected right canonical contact, yielding
18 physical contacts. The retired raster presentation compatibility inventory
contains exactly 72 IDs: nine physical-contact IDs × two sides × four historic
orientation presentations.

| Pivot source patch | Slot | Left contact | Right contact |
| --- | --- | --- | --- |
| wing crest | `outer-wedge-pinch` | `outer-wedge-pinch-left` | `outer-wedge-pinch-right` |
| wing inner | `outer-wedge-pinch` | `outer-wedge-pinch-left` | `outer-wedge-pinch-right` |
| rail lower | `variable-edge` | `variable-edge-left` | `variable-edge-right` |
| rail upper | `variable-edge` | `variable-edge-left` | `variable-edge-right` |
| rail-end outer | `variable-edge` | `variable-edge-left` | `variable-edge-right` |
| rail-end inner | `variable-edge` | `variable-edge-left` | `variable-edge-right` |
| supported lower | `medium-crimp` | `medium-crimp-left` | `medium-crimp-right` |
| supported upper | `large-crimp` | `large-crimp-left` | `large-crimp-right` |
| two-finger top | `two-finger-pocket` | `two-finger-pocket-left` | `two-finger-pocket-right` |
| two-finger side | `two-finger-pocket` | `two-finger-pocket-left` | `two-finger-pocket-right` |
| three-finger top | `three-finger-pocket` | `three-finger-pocket-left` | `three-finger-pocket-right` |
| top sloped | `upper-sloped-crimp` | `upper-sloped-crimp-left` | `upper-sloped-crimp-right` |
| side sloped | `outer-sloped-crimp` | `outer-sloped-crimp-left` | `outer-sloped-crimp-right` |
| lower-wave sloper | `lower-sloper` | `lower-sloper-left` | `lower-sloper-right` |

The source register independently maps every normalized patch to both exact
delivered `pv-L-*` and `pv-R-*` identifiers. It also explicitly maps all 72
retired presentation IDs to their 18 normalized contacts. Only `p1`, `p2`,
`p3`, and `p5` are selectable. `p4` is Orientation 3 Switch transition-only
evidence and is deliberately not selectable. Pivot has `noDocumentedSuspension`:
pulley-kit ropes are not suspension evidence.

## Exact-byte exception: Treeline Light Rail photo

The current Squarespace binary URL returned HTTP 200 with changed bytes
(`7d06ec5f74917b909b031ac72067944f8cf72b14481aa0e31eafc272600c0aea`,
702,408 bytes). Those bytes were not retained or accepted. The retained
`metolius-light-rail-1.jpg` is the exact approved 848,076-byte file
(`93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a`),
replayed at `2026-01-29T01:24:02Z` from
<https://web.archive.org/web/20260129012402id_/https://images.squarespace-cdn.com/content/v1/5b4544e485ede17941bc95fc/452f6e96-37f1-454d-a405-e801658501a5/metolius-light-rail-1.jpg>.
