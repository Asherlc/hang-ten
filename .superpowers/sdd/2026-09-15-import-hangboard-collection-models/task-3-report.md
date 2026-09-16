# Task 3 — Metolius Simulator 3-D model migration

Status: implementation and package checks complete; reviewer gate requested
from the controller before integration.

## Delivered package

- Migrated `metolius.simulator-3d` to sole model presentation assets
  `assets/primary.usdz` and `assets/primary.model.json`.
- Removed declared raster `assets/primary.png` and all presentation contact
  geometry; retained the exact preexisting 29 catalog contact IDs and facts.
- Descriptor hash: `783e0a0e808a31d8f4d11c69c15477e6ef70c93eed2da9c195639ef014b302ee`.
- Shipped USDZ hash: `3372f4d2b42a967d3ca65c2d1a0f56bd7762b32f9c1a80f79897841b020fbc94`.

## Mapping and source correction

The explicit audited mapping has one `board_body`, two model body nodes after
the correction, and 31 selectable source mesh pieces. Every existing contact
is bound. The only intentional many-piece mappings are `hold_02_left` plus
`hold_03_left` to `round-sloper-3-left`, and their right counterparts to
`round-sloper-3-right`; they preserve the manufacturer’s uninterrupted #2/#3
sloper contacts. The supplied GLB SHA-256 is
`1f71e8673d0682f27398d260a8320ae054b75a3d023436aa896549eeed22297a`.

The source review found eight visible mounting-hardware openings. The owned
native correction adds eight nonselectable display-only body caps; it does not
modify any contact mesh or catalog fact. Native source hashes before/after are
`732be4c9ce2c58162ad40484268217db61ce97db2959256395119565ab982a49` and
`ab2d71965fc851bca6c1678dbac7d02d4bda73eba482690eae6e75ced6247b45`.

## Evidence and verification

The audit retains two official visual sources (product photo and numbered hold
diagram) with URLs, purpose limits, and hashes. It also records the exact
shipped-asset empty-scene Blender verification: 33 importer-visible nodes,
two body nodes, 31 contact mesh nodes, all image-material/triangle checks, and
the exact 29-contact descriptor keyset.

`scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
and `status --root Hangboards` passed. The retained model tooling suite could
not start because neither available Python environment has `pytest`; this is
reported rather than masked. Its `unittest`-compatible test modules remain to
be run by the controller or a provisioned test environment.
