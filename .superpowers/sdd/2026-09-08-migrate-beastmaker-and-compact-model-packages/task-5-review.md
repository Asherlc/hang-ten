# Task 5 — native SceneKit package semantics review

Date: 2026-09-09

## Reviewed range

`cc03eea8..2e9b67b2`

## Result

**SPEC PASS** — the Task 5 implementation and its retained host-native
evidence satisfy the actual-package semantic contract. **QUALITY PASS** — the
production change is the minimum generic importer-ID binding correction, and
the focused tests exercise the failure modes it must protect. Focused simulator
XCTest remains a documented external execution gate; it has not run and is not
claimed by this review.

## Correction to the initial review

The initial rejection in this review artifact is withdrawn. Its asserted
body-occlusion result came from an error in the review-only diagnostic, not
from the Task 5 XCTest, package, USDZ, descriptor, or app code.

That diagnostic used:

```swift
let spans = zip(minimum, maximum).map(-)
let extensionDistance = spans.max()! * 2
```

`map(-)` evaluates `minimum - maximum`. For Beastmaker, that made the largest
span `-0.058` and the extension `-0.116`, so the ray ran from approximately
`z = -0.058` to `z = 0.116`: back-to-front. The body at approximately zero was
therefore correctly its first intersection.

Task 5's `BoardModelTests.headOnRay` instead uses
`zip(bounds.minimum, bounds.maximum).map { $1 - $0 }`. Its positive extension
starts in front of the board and runs front-to-back, which is the required
direction. Keeping every other review-diagnostic variable unchanged and
correcting only that span expression returned `BeastmakerBody_024` for
`jug-left` at `z = 0.05642698332667351`, matching the retained Astra result.
The exact reconciliation, including endpoints and source code, is retained in
`.context/shaky-rat-task5-diagnostic-reconciliation.md`.

## Fresh host-native verification

The review reran Astra's retained
`.context/shaky-rat-native-occlusion/check.swift` against the committed
package-owned USDZ and descriptor files. The script uses `.convertToYUp`,
clones the imported root into a fresh `SCNScene`, flushes the transaction,
denormalizes each descriptor face-plane center in the declared X/Y board axes,
and performs closest front-to-back segment hits.

| Board | Descriptor-center rays | First hits match expected holds | Body probe |
| --- | ---: | --- | --- |
| Beastmaker 1000 | 22 | 22 / 22 | body / unbound |
| Metolius Wood Grips Compact II | 19 | 19 / 19 | body / unbound |

The rechecked promoted bytes match the Task 3/4 retained hashes exactly:

| Board | USDZ SHA-256 | Descriptor SHA-256 |
| --- | --- | --- |
| Beastmaker 1000 | `e15bae1d9664b834ee68853cecba47076617bdd382458b26700d18e321e146e3` | `2c392869087b6729870010d7606dd3a500eb659d48f80fe851115ff62b71984b` |
| Metolius Wood Grips Compact II | `220c68ea5519b0bed80cd2aac08b35f5f2c2a7d2200596f62c3a84996efb94a3` | `300a26886362dd0c510c729e1a9fd4e6a35f47497aed5e7f12d33a2fdb7068fe` |

This agrees with Task 5's retained host-native evidence: exact 23-node
Beastmaker and 20-node Compact descriptor inventories, nonempty imported
materials and diffuse contents, all 41 descriptor-center nearest hits, and an
unselectable body hit.

## Implementation and test assessment

The actual-package XCTest loads both target models only through
`BoardCatalog.packageStore` and `BoardModelLoader`; it does not use standalone
resources, fake node mappings, raster fallback, or a per-board renderer path.
It asserts literal 22/19 logical inventories, 23/20 imported mesh counts,
bound hold inventory, diffuse material presence, all 41 nearest hits, and a
body hit with no logical hold ID. The existing generic cloned-material check
now covers active and preview/rest restoration without duplicating that work
per imported mesh.

The missing/corrupt fixture mutations use unique valid board IDs, preventing
the asynchronous source-scene cache from satisfying one case with another
case's model. They therefore test failure closed rather than cache reuse.

`BoardModelScene` handles the importer Xforms with a constrained generic rule:
a descriptor whose IDs are uniformly bare binds exact unique geometry-node
names, while a descriptor containing a path retains exact hierarchy-path
matching. The existing full-path test and mixed/path mismatch rejection remain
in place. The verified imports expose bare geometry names beneath exporter
Xforms, so this is the minimum correction required for both promoted packages.

The reviewed range changes no Hangboard package, model resource, raster
fallback, geometry, or Xcode project staging. The Task 5 report records a
successful unsigned `build-for-testing`; that compile evidence is consistent
with the inspected test source but is not treated as XCTest execution.

## Pending simulator XCTest gate

The Task 5 report records one read-only `xcrun simctl list devices` preflight
failure caused by an unavailable CoreSimulator service. Per
`validate-hang-ten-ios`, no simulator was created or retried, no UUID was
recorded, and cleanup left no owned simulator record. That is correct
simulator-lifecycle behavior and an external infrastructure gate, rather than
an implementation defect.

The focused `BoardModelTests` and `BoardPackageStoreTests` XCTest run on the
prescribed owned simulator remains pending until CoreSimulator is healthy. It
must be performed before this migration can claim native simulator execution;
this review does not claim that result.
