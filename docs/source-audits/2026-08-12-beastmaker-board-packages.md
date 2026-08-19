# Beastmaker board-package source audit

Checked 2026-08-12. This is a historical evidence audit, not current package
or runtime state. Its old readiness conclusions are superseded by the current
flat-package schema and `docs/ADDING_A_BOARD.md`; unsupported optional metadata
is omitted, while visible paths are directly authored from primary evidence.

## Candidates

| slug | catalog id | official product URL | official front image URL |
| --- | --- | --- | --- |
| `beastmaker-1000` | `beastmaker.1000` | https://www.beastmaker.co.uk/products/beastmaker-1000-series | https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068 |
| `beastmaker-2000` | `beastmaker.2000` | https://www.beastmaker.co.uk/products/beastmaker-2000-series | https://cdn.shopify.com/s/files/1/0107/6442/files/2000_Small_Tulip.jpg?v=1756734230 |

The official product pages establish each board's identity, published overall
dimensions, a grouped inventory of hold types, and the associated official
front image. The audit found no Beastmaker-published numbered hold guide,
depth diagram, manual, or measurement source for either board. No official
oblique image or per-hold measurement source was found that could distinguish
the individual physical boundaries, depths, and capacities needed by the
package schema.

## Evidence coverage

| board fact, hold field, semantic target, or asset | official source URL | package evidence key | representation method |
| --- | --- | --- | --- |
| Beastmaker 1000 identity, dimensions, grouped hold inventory, and silhouette | https://www.beastmaker.co.uk/products/beastmaker-1000-series | not authored: readiness gate not met | product-page review only |
| Beastmaker 1000 front presentation image | https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068 | not authored: readiness gate not met | official front-image review only |
| Beastmaker 2000 identity, dimensions, grouped hold inventory, and silhouette | https://www.beastmaker.co.uk/products/beastmaker-2000-series | not authored: readiness gate not met | product-page review only |
| Beastmaker 2000 front presentation image | https://cdn.shopify.com/s/files/1/0107/6442/files/2000_Small_Tulip.jpg?v=1756734230 | not authored: readiness gate not met | official front-image review only |

## Evidence blockers

### `beastmaker-1000`

Missing official evidence: no manufacturer hold guide or measurement supports
`fingerCapacity`, `gripType`, and each physical hold boundary. The product page
and front image establish identity and silhouette only. No `board.json`,
`semantics.json`, `evidence.json`, or catalog entry was added.

The product page does name a grouped inventory (including pocket capacities and
one 10 mm category), but it does not associate those facts with every visible
physical hold or publish the full depth/size measurements and boundaries that
the package needs. The completed package was later authored and reviewed
independently of the removed draft art.

### `beastmaker-2000`

Missing official evidence: no manufacturer hold guide or measurement supports
`fingerCapacity`, `gripType`, and each physical hold boundary. The product page
and front image establish identity and silhouette only. No `board.json`,
`semantics.json`, `evidence.json`, or catalog entry was added.

The product page has a grouped descriptive list (including the 22 mm middle
edge), rather than a one-to-one map of physical holds with their depth, finger
capacity, grip classification, and boundary. The completed package was later
authored and reviewed independently of the removed draft art.
