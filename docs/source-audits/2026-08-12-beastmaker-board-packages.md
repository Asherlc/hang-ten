# Beastmaker board-package source audit

Checked 2026-08-12. This is a historical evidence audit, not current package
or runtime state. Its old readiness conclusions are superseded by the current
flat-package schema and `docs/ADDING_A_BOARD.md`; unsupported optional metadata
is omitted, while visible paths are directly authored from primary evidence.

## Candidates

| slug | board id | official product URL | official front image URL |
| --- | --- | --- | --- |
| `beastmaker-1000` | `beastmaker.1000` | https://www.beastmaker.co.uk/products/beastmaker-1000-series | https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068 |
| `beastmaker-2000` | `beastmaker.2000` | https://www.beastmaker.co.uk/products/beastmaker-2000-series | https://cdn.shopify.com/s/files/1/0107/6442/files/2000_Small_Tulip.jpg?v=1756734230 |

The official product pages establish each board's identity, published overall
dimensions, a grouped inventory of hold types, and the associated official
front image. The audit found no Beastmaker-published numbered hold guide,
depth diagram, manual, or measurement source for either board. No official
oblique image or per-hold measurement source was found that could assign every
individual depth or capacity.

## Current authoring interpretation

- For `beastmaker-1000`, the grouped inventory supports the visible pocket
  capacities and one 10 mm category, but not a depth for every individual
  contact. Unsupported measurements remain omitted.
- For `beastmaker-2000`, the grouped description supports the clearly central
  22 mm edge, but not a complete depth assignment. Unsupported values remain
  omitted.
- Visible contact boundaries may be directly authored from the official front
  imagery and reviewed by a person. They are not measurements.

Both completed packages were later authored and visually reviewed independently
of the removed draft art.
