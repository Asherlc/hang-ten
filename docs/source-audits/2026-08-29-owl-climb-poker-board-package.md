# Owl Climb Poker source audit

Reviewed 2026-08-29 for package `owl-climb-poker` and board ID
`owl-climb.poker`.

## Evidence and caveats

| Source | Package use | Caveat |
| --- | --- | --- |
| [Owl Climb Poker product page](https://owlclimb.com/index.php/en/prds-2/poker/) | Primary identity, canonical `productURL`, four-face construction, `660 × 100 × 100 mm` dimensions, central and outer contact inventory, published depth ranges, two 35° slopers, and two 100 mm half-circles. | The page describes the feature families and their range of dimensions but does not label an individual face or left/right contact with a particular depth. |
| [Owl Climb official image 0](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_0.jpg?resize=790%2C309&ssl=1), [1](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_1.jpg?resize=790%2C309&ssl=1), [2](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_2.jpg?resize=790%2C309&ssl=1), and [3](https://i0.wp.com/owlclimb.com/wp-content/uploads/2019/03/owlclimb_poker19_3.jpg?resize=790%2C309&ssl=1) | Primary visual evidence for the four face layouts, bilateral outer slots / single- and dual-finger holes, central pull-up hole, and distinguishable central-face profiles. | Product photos rather than a numbered hold guide; their image labels do not assign the published depth values to a particular face. The support, brackets, and Owl logo are not hand contacts and are omitted. |
| [BananaFingers Owl Climb Poker listing](https://bananafingers.com/us/owl-climb-poker-hangboard) | Secondary identity and retail-listing corroboration supplied with the request. | Third-party retailer. It was not used to determine dimensions, hold inventory, metadata, art, or geometry; its page also rejected automated retrieval during this review. |

## Frozen contact inventory and field mapping

The manufacturer explicitly establishes four selectable faces. Each face has a
left and right outer slot, a left and right single-finger hole, a left and
right dual-finger hole, and one central single-arm-pull-up hole. That is 24
contacts. The documented pair of big slopers and pair of 100 mm half-circles
add four central contacts, for 28 total direct-authored records.

| IDs | Retained source-backed fields | Deliberate omission |
| --- | --- | --- |
| `face-*-slot-left`, `face-*-slot-right` | `kind: edge`; the outer slots are a named manufacturer feature on all four faces. | The source lists 25/20/15/10 mm across the four faces but does not identify which pictured face owns which value, so no per-record size/depth is asserted. |
| `face-*-single-left`, `face-*-single-right` | `kind: pocket`, `fingerCapacity: 1`; the manufacturer calls these single-finger holes. | Its 40/30/25/20 mm depth list is not face-labelled, so no per-record size/depth is asserted. |
| `face-*-dual-left`, `face-*-dual-right` | `kind: pocket`, `fingerCapacity: 2`; the manufacturer calls these dual-finger holes. | No face-specific depth, grip posture, hand capacity, or treatment is supplied. |
| `face-*-center-hole` | `kind: pocket`; one central hole is visibly present on each face and the manufacturer says the central zone has four single-arm-pull-up holes. | The page says the four holes span 15–30 mm but does not map a value to a face, so no per-record size/depth, capacity, or posture is asserted. |
| `face-b-sloper-left`, `face-b-sloper-right` | `kind: sloper`; the manufacturer explicitly identifies two large 35° slopers. | No schema `sloper` subtype is supplied: the source does not say whether the app’s flat/round subtype applies. Their neutral Face B placement follows the distinct central profile in the official face series, not a manufacturer face label. |
| `face-c-half-circle-left`, `face-c-half-circle-right` | `sizeMillimeters: 100`; the manufacturer explicitly states two 100 mm-diameter half-circles. | `kind: sloper` is an explicitly documented schema adaptation: Hang Ten has no half-circle hold kind, and these are open rounded central contacts rather than holes. No posture, capacity, or depth is asserted. Their neutral Face C placement is a presentation choice, not a manufacturer depth/face mapping. |

`Face A` through `Face D` intentionally remain neutral identifiers. They map to
the four visual configurations in Owl Climb's official image series without
claiming a published face order or a per-face depth assignment. The direct
geometry is a conservative contact boundary for only the named, visible
contacts. Central sculpting that the sources do not identify as one of the two
slopers or two half-circles is art only, not extra hold metadata.

## Art and geometry review boundary

Each presentation asset is a new transparent 1980 × 300 straight-on schematic
render made from directly written SVG primitives and rasterized locally. It is
not a copied, cropped, traced, registered, vectorized, segmented, or otherwise
transformed manufacturer or retailer image. The official images were evidence
only. No image-generation model was used because the desired asset is a simple,
deterministic, code-native diagram rather than a photographic or illustrative
asset.

Every saved normalized path/frame was selected directly against that accepted
presentation art and then checked through the package validator. Regular slots,
holes, and central pull-up holes have operator-selected pill/oval constraints;
the two half-circles retain explicitly authored closed Bézier paths. The saved
paths remain the normal rendering, active rendering, and hit-test truth. No
source image drove geometry extraction or automatic refinement.

## iOS validation limitation

An owned iPhone 17 Pro / iOS 26.5 simulator was created and cleaned up twice
under the exact `Hang Ten Paseo infamous-parrot` ownership marker. The bounded
`launchctl print system` readiness probe passed. The focused
`OwlClimbPokerBoardMapInteractionUITests` build reached installation of its
runner but Xcode then launched the runner with an empty XCTest configuration
and `wait_for_debugger=1`; no test body or app process started. A separate
signed direct-app launch remained on the simulator's system splash screen, so
no valid Hang Ten normal, active/highlight, or hit-test screenshot was emitted.
The owned UUIDs and build artifacts were removed through
`scripts/paseo-resource-cleanup.sh archive`; both local manifests are empty.

Consequently, package-schema validation and the added focused UI test source
are present, but simulator visual validation remains an infrastructure follow-up
on a healthy Xcode/simulator runner. No splash-screen capture is retained or
claimed as product evidence.
