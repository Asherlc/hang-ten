# Multi-angle board-evidence review

Reviewed 2026-09-09 against `4987c3df` (`docs: add multi-angle board
evidence`), the multi-angle gate added by `1c31be9b`, its review in
`0f66129a`, `AGENTS.md`, the active migration plan/spec, and the complete
`add-hangboard` and `migrate-hangboard-to-3d` skills. This is an evidence-only
review: no runtime, model-generator, skill, packet, or Astra changes were
made.

## Decision

**Do not send Beastmaker 1000 geometry work to Astra. The combined human gate
is not ready.** The retained 9c image is an authentic exact-revision commerce
source, but visual inspection at its original 1800 × 513 pixels finds it is a
second near-straight-on front product view, not a materially distinct oblique,
side, back, or profile image. Its small elevation/lighting difference does not
reveal usable top-plane or side/profile geometry beyond the manufacturer front.
It must not be counted as the second view. Retain it as corroborative
exact-revision commerce media if useful, but obtain and retain a genuine
profile, side, back, or clearly three-quarter image, then repeat human review.

**Metolius Wood Grips Compact II has a qualifying two-image candidate set, but
still needs explicit human approval before an Astra physical-fidelity task.**
The image pair is materially distinct: the Bergfreunde image visibly exposes
the laminated top plane, outer end/side rollovers, and front-depth transitions
that the manufacturer front product view does not. It is commerce-gap evidence
only, and its limits in the packet are appropriately conservative.

## Exact image verdicts

| board / retained image | provenance and exact-revision linkage | verified pixels / SHA-256 | review verdict |
| --- | --- | --- | --- |
| Beastmaker 1000 — `references/beastmaker-1000-tulip.jpg` | Manufacturer. The retained Beastmaker 1000 Series page identifies the product as Beastmaker 1000 Series and links the exact Tulip asset. | 2500 × 735; `b97c4a0fc1c6f8971cb7610a2ec2a979415e6c9018398c18ab76ed90034fdfae` | **Qualifies as front.** Complete head-on product image; supports face inventory/relative placement only. |
| Beastmaker 1000 — `references/9c-beastmaker-1000-03.jpg` | Commerce-gap. The retained 9c page names vendor Beastmaker and product 1000 Series and directly declares this exact 1800 × 513 asset as its product/OG image. | 1800 × 513; `db2bdac139d56951a04d674020e1ab50d2f36c1cb40aed158838da4bce195356` | **Does not qualify as second angle.** It is a near-front variant/crop-lighting presentation, not materially distinct profile evidence. The packet claim that it supports top-plane/side-roundover continuity overstates what is visible. |
| Metolius Wood Grips Compact II — `references/compact-training-board.jpg` | Manufacturer. The retained Metolius Wood Grips II page links the exact Compact asset and distinguishes the Compact and Deluxe family. The visual layout is the short two-row Compact, not the taller Deluxe. | 2000 × 2000; `d72c7027d82980306e0e2a50d94394c174dce8ba0fd9bb239c704f099f05ed03` | **Qualifies as manufacturer front.** Supports complete Compact face inventory and relative placement, not rear/profile dimensions. |
| Metolius Wood Grips Compact II — `references/bergfreunde-compact-ii-oblique.jpg` | Commerce-gap. The retained Bergfreunde page title/data identify “Metolius Wood Grips Compact II - Training board”, SKU `342-0111`, and link the exact 1500-pixel image. The source does not present a Deluxe alternative. | 1500 × 1500; `1729ecad6eec3df71c9e8e06341c10cc936631edf47948fd17235ed9a5bd991a` | **Qualifies as a materially distinct commerce oblique.** Complete Compact board with visible top lamination, end rollovers, and front-depth transitions; does not establish rear geometry or measured body depth. |

## Packet, source, and handoff checks

- Both packets validate with `python3 -B Tools/HangboardModels/validate_evidence_packet.py`; their on-disk SHA-256 values match the updated briefs/source audits: Beastmaker `483fd0c89efe6e6d3e7d7628a310b64f64138c29820a381b25e5f3020a269050`, Compact II `fe4a13559dfc8b734e349005444599407cb8cb7358350a095c0c3cdd451f62c3`.
- All four selected assets are retained original-resolution JPEG source media with matching packet hashes and direct retained-page linkage. They are not generated renders, search thumbnails, or legacy package raster assets/paths. The selected claims preserve manufacturer versus commerce tier, record the manufacturer second-angle gap, and do not allow commerce claims to override manufacturer facts.
- The exact board identities are supported: 9c labels Beastmaker 1000 Series rather than 2000; Metolius/Bergfreunde identify Wood Grips Compact II and the visible two-row Compact layout rather than Deluxe. This does not cure the Beastmaker angle failure.
- The packets record support limitations and retain no geometry proposal. The Compact commerce notes are honest. Beastmaker's claimed side/top support is not: visual review rejects that inference.
- Beastmaker's `astra-handoff.md` names both retained images, their hashes, page relationship, tier, and limitations. It is nevertheless not an approved handoff because its second listed image fails the visual gate. Compact's `evidence-brief.md` names both candidate images and all required metadata; a future Compact Astra correction must receive both only after explicit human approval. There is no need to pass unrelated legacy/generated render output.

## Human gate required next

1. Gather a complete exact Beastmaker 1000 side, back, profile, or clearly
   three-quarter source image; prefer manufacturer media, otherwise retain a
   page-linked authorized-commerce image with tier, hash, pixels, angle, and
   limitations.
2. Correct the Beastmaker packet/brief/handoff to remove the unsupported
   second-angle assertion, then validate it and conduct a new human review of
   the exact two-or-more image set.
3. Obtain explicit human approval separately for Beastmaker's replacement set
   and Compact's existing candidate set. Only then may Astra receive every
   approved image for the relevant board; no geometry work is authorized by
   this review itself.

## Checks

- `shasum -a 256` over the four retained images and both packet JSON files
  matched the recorded values.
- `sips -g pixelWidth -g pixelHeight -g format` confirmed 2500 × 735,
  1800 × 513, 2000 × 2000, and 1500 × 1500 JPEGs respectively.
- `python3 -B Tools/HangboardModels/validate_evidence_packet.py` passed for
  both exact packet JSON paths.
- `git diff --check` passed for `4987c3df`, `1c31be9b`, and `0f66129a`.
