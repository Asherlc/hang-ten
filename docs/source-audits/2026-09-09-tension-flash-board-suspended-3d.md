# Tension Flash Board suspended 3D evidence audit

Task 1 retains the exact-revision visual candidates under the workspace-owned
packet `.context/pretty-crocodile-tension-flash-board`. The manufacturer
product source is first tier; `commerce-hanging.jpg` and
`commerce-labelled-faces.jpg` are commerce-gap snapshots with retailer identity
and exact snapshot hashes. See `evidence-packet.json` and
`evidence-approval.md` for the complete source ledger and approval.

## Retained-source ledger

| Retained snapshot | Publisher / URL | Tier | View label | Supports | Limitations |
| --- | --- | --- | --- | --- | --- |
| `sources/manufacturer-front.png` (`82915e017550c544354c50086aa1b18b7091b0a6b766629ac196b95237f1d146`) | Tension Climbing, [Flash Board product page](https://tensionclimbing.com/products/flash-board-2) | manufacturer | oblique/two-well face | Exact product identity, compact cylindrical board, portable cord suspension, and the depicted two-well face | Does not map global edge sizes to individual contacts; does not establish attachment coordinates, cord dimensions, knot detail, or canonical poses |
| `sources/commerce-hanging.jpg` (`4a9f8e5639c60631dba9d2149a1cd6cfe2a1426012ef5ac42f442d2f743f1751`) | Backcountry, [Flash Board commerce page](https://www.backcountry.com/tension-flash-board) | commerce gap | hanging / attachment region | Hanging configuration and paired end cord passages; attachment-region context | Retailer evidence, not manufacturer authority; no exact cord dimensions, material, knot geometry, attachment coordinates, or pose values |
| `sources/commerce-labelled-faces.jpg` (`b601ac96f555f7ef10ebbdd955471fd69d7d21fc3b57fae9692b87780c0d38d0`) | Amazon, [Flash Board commerce listing](https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G) | commerce gap | labelled face map / three-well face | Three-well contact inventory and labels used for the three-edge position mappings | Retailer evidence, not manufacturer authority; labels do not prove individual depth assignments, dimensions, attachment coordinates, poses, or camera values |
| `sources/user-closeup-front-cord-and-wells.png` (`95df6bf5077282b3511d152bb2a49040e909d17bc95ad93c5831c41b66e4709c`) | User-supplied attachment | user evidence | front face and cord closeup | Front face, deep wells, and visible cord routing | User evidence is not manufacturer authority; crop/perspective do not establish dimensions or additional logical IDs |
| `sources/user-closeup-end-attachment.png` (`d2ddc7bc93df6e0dfdb99e499049076e324a80655f66e2f9d240d0581493fe54`) | User-supplied attachment | user evidence | end attachment closeup | Cylindrical end and cord passage routing | Does not establish a nail, knot dimensions, attachment coordinates, or selectable contacts |
| `sources/user-closeup-opposite-face.png` (`a5aa9472d6666bb60bae1e0193fd19446befe40b8ea81c253d6f0ebc6cb46fc9`) | User-supplied attachment | user evidence | opposite face and routing | Opposite face, shallow ledges, and cord routing | Oblique perspective does not prove individual depths or new logical IDs |
| `sources/user-closeup-three-well-face.png` (`2a5add52598087b5a97a15df410c8b415f41dbc2a4965610b3145a44f4da3130`) | User-supplied attachment | user evidence | three-well face closeup | Three-well face and upper/lower shallow ledges | Lower grooves are not proven separate logical contacts |
| `sources/user-closeup-two-well-face.png` (`fdeed84e7c035418d576b32c4e04d6134dc696563f95095ab6e3cc1b6d7944a7`) | User-supplied attachment | user evidence | two-well face closeup | Two-well face, ledges, and end cord passage | Does not establish dimensions or convert shallow ledges into logical IDs |
| `sources/user-closeup-two-well-face-wide.png` (`739ca6f81201eb0762667a25b5cd672c2af44c499475db4350b3958941ab4904`) | User-supplied attachment | user evidence | two-well face wide oblique | Two-well face and paired end cord routing | Crop/perspective do not establish a new hold inventory |

The seven existing logical IDs are preserved. Visual review corrected the
filename/label mismatch: `manufacturer-front.png` depicts the two-well face,
while `commerce-labelled-faces.jpg` depicts the three-well face. Three-edge
upright/inverted positions map to the three three-edge contacts; two-edge
upright/inverted map to the two edge contacts and two small crimps. The manufacturer source supports
portable cord suspension and the global edge inventory, but does not map
published sizes to individual recesses.

The Amazon annotated face map remains commerce-gap evidence only. It describes
the three-well face as outboard small crimps plus tapered upper and flat lower
ledges, but cannot override the approved seven-ID inventory. Supplied closeups
show intentional shallow lower grooves beneath or adjacent to wells; their
logical interpretation is unresolved. They are retained as user evidence and
may be authored only as nonselectable display geometry. The packet's explicit
`logicalRuling` is `no-new-logical-ids`, with a conflict/ruling retained under
`lower-ledge-interpretation`.

Attachment coordinates, invisible-anchor offset, cord length/radius/material,
canonical poses, and camera settings are display estimates (or unknown where
unsupported). Anchor visibility is deliberately invisible; no cord, anchor,
mounting environment, mounting hardware, or geometry proposal is included in
the evidence packet. The packet validator checks all references against exact
retained bytes and enforces the two-or-more materially distinct approved view
gate before Astra.

## 2026-09-11 review corrections and verification

The earlier two-branch display route reused each branch's first/last shoulder
point and backtracked over its rear bearing segment. Native self-intersection
rejection exposed that defect. The revised display-only route separates the
free-span shoulders and traverses each rear bearing once. Cord radius (2 mm),
rest length (1.56 m per branch), all four bores, seven logical holds, canonical
poses, and the board USDZ/descriptor remain unchanged. These route coordinates
remain estimates, not manufacturer measurements or structural certification.

The durable input is
`Tools/HangboardModels/fixtures/tension_flash_board_two_branch_review_candidate.json`.
Fresh Blender export/reimport evidence is retained separately in
`Tools/HangboardModels/fixtures/tension_flash_board_export_verification.json`.
Its model SHA-256 is
`4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524`;
descriptor SHA-256 is
`fd2c3e057c9feee1d6da57448bd9e4d58510ae8a6c60120282e51b13c228019c`.
The verifier now independently rejects centerline crossings/backtracking and
uses clipped-triangle solid-cylinder tests for the full 3 mm aperture envelope;
radial rays are diagnostic only. Free spans and hold meshes retain 3 mm
clearance; only authored body bearing spans use the 2 mm physical cord radius.
The retained report is checked against production route, passage and asset bytes.

Native USDZ imports contain three interleaved index channels. The mesh-distance
reader now uses SceneKit's declared position channel instead of misreading
normal/UV indices. Native tests cover interleaved and planar layouts, including
a nonzero position channel, and select every Flash Board pose from the bundled
asset. Verified on an isolated iPhone 17 Pro / iOS 26.5 Simulator:
176 tests passed, zero failures. Python package/model validation passed
693 tests and 14 subtests; the focused export-verifier suite passed 31 tests.
Actual Blender compiler export/reimport/determinism and material-import checks
also passed. Commands and native summary are retained under the workspace-owned
`.context/pretty-crocodile-merge-ci`; temporary simulator/config/cache resources
were deleted after verification. Android execution remains unverified locally
because this host lacks an Android SDK and the required Java toolchain.
