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
| `sources/manufacturer-front.png` (`82915e017550c544354c50086aa1b18b7091b0a6b766629ac196b95237f1d146`) | Tension Climbing, [Flash Board product page](https://tensionclimbing.com/products/flash-board-2) | manufacturer | front/product | Exact product identity, compact cylindrical board, portable cord suspension, and manufacturer product context | Does not map global edge sizes to individual contacts; does not establish attachment coordinates, cord dimensions, knot detail, or canonical poses |
| `sources/commerce-hanging.jpg` (`4a9f8e5639c60631dba9d2149a1cd6cfe2a1426012ef5ac42f442d2f743f1751`) | Backcountry, [Flash Board commerce page](https://www.backcountry.com/tension-flash-board) | commerce gap | hanging / attachment region | Hanging configuration and paired end cord passages; attachment-region context | Retailer evidence, not manufacturer authority; no exact cord dimensions, material, knot geometry, attachment coordinates, or pose values |
| `sources/commerce-labelled-faces.jpg` (`b601ac96f555f7ef10ebbdd955471fd69d7d21fc3b57fae9692b87780c0d38d0`) | Amazon, [Flash Board commerce listing](https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G) | commerce gap | labelled face map | Two-edge contact separation and small-crimp/edge inventory used for the four position mappings | Retailer evidence, not manufacturer authority; labels do not prove individual depth assignments, dimensions, attachment coordinates, poses, or camera values |

The seven existing logical IDs are preserved. Three-edge upright/inverted
positions map to the three three-edge contacts; two-edge upright/inverted map
to the two edge contacts and two small crimps. The manufacturer source supports
portable cord suspension and the global edge inventory, but does not map
published sizes to individual recesses.

Attachment coordinates, invisible-anchor offset, cord length/radius/material,
canonical poses, and camera settings are display estimates (or unknown where
unsupported). Anchor visibility is deliberately invisible; no cord, anchor,
mounting environment, mounting hardware, or geometry proposal is included in
the evidence packet. The packet validator checks all references against exact
retained bytes and enforces the two-or-more materially distinct approved view
gate before Astra.
