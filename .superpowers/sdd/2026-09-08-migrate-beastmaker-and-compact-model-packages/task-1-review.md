# Task 1 review — Stage 0 two-board evidence packets

Reviewed 2026-09-09 against `f9c133ab`, the retained packet bytes, current
manufacturer pages/media, `docs/ADDING_A_BOARD.md`,
`docs/superpowers/plans/2026-09-08-migrate-beastmaker-and-compact-model-packages.md`,
the lean delta, and `Tools/HangboardModels/evidence_packet.py`.

## Result: not approved for G1

Do not dispatch geometry while the Compact packet describes 56 mm as board
thickness.  The packet validator passes the files, but it validates retained
file integrity and structural references; it cannot establish that a cited
source actually supports a claim.

## Critical — Compact 56 mm is a hold measurement, not overall thickness

`references/woodgrips-boards-depths.jpg` is a numbered hold-depth diagram.
Its lower **Wood Grips Compact** legend reads:

- `2  56 mm flat sloper`
- `9  56 mm round sloper`

The lower diagram does distinguish Compact from the upper Deluxe diagram, but
it supplies individual sloper dimensions only.  It supplies no overall
front-to-back board thickness.  The current manufacturer product page likewise
publishes only Compact face size `24 in x 6.2 in (610 mm x 157 mm)`.

This contradicts the following records:

- `.context/shaky-rat-metolius-wood-grips-compact-ii/evidence-packet.json`:
  `sourcedClaims[5]` (`compact-depth`) and `conflictsAndRulings[0].ruling`.
- `.context/shaky-rat-metolius-wood-grips-compact-ii/evidence-brief.md`:
  “56 mm is qualified display thickness”.
- `docs/source-audits/2026-08-12-beastmaker-board-packages.md`, Stage 0 Compact
  ruling added in `f9c133ab`.
- Both migration plans’ E1 wording, which repeats the unsupported body-depth
  assertion.

Required correction: remove 56 mm as a Compact model/body Z dimension and
record overall thickness as unknown for Astra unless a separate retained
manufacturer dimensional source establishes it.  The diagram may instead be
used, with exact numbered mappings, for the left/right flat slopers and centre
round sloper’s source-backed 56 mm hold-depth designation.  This is not an
instruction to add geometry or a numeric section.

## High — exact inventory provenance is too coarse in both packets

The migration plan requires an exact retained source snapshot for each
source-backed logical-inventory entry.  Both files pass only because the
validator tests that `sourceLocalPath` exists; it does not test whether that
snapshot supports the entry.

### Beastmaker 1000

All 22 `logicalInventory` entries cite
`references/beastmaker-1000-beech.html`.  That page supports the grouped
families (two jugs, 35-degree slopers, one 20-degree sloper, and unpositioned
pocket families), the unpositioned 10 mm small four-finger pair, and the
580 x 150 x 58 mm Beech overall dimensions.  It does **not** position the
groups on stable IDs or distinguish every cavity that the packet calls `edge`
from every cavity that it calls `pocket`.

The official Tulip front (`beastmaker-1000-tulip.jpg`) visually supports the
22-contact ruling: 2 outer jugs, 3 top sloper surfaces, and 17 cavities.  It
does not establish the individual edge/pocket mapping or exact per-ID size and
finger metadata.  Preserve the runtime IDs and metadata unchanged, but mark
the unsupported per-ID mapping as inherited/stable rather than mis-citing the
Beech page as direct authority.  Any primary numbered guide or direct
manufacturer mapping would be needed to upgrade that provenance.

### Metolius Wood Grips Compact II

Every `logicalInventory` entry cites
`references/metolius-wood-grips-ii.html`, which only says the boards offer
jugs, slopers, edges, and pockets.  The retained numbered depth diagram—not
the product page—is the exact source that maps Compact groups 1–11 and their
left/right/centre repetitions.  It supports the current 19-contact grouping
(2 jugs + 3 slopers + 7 upper-row contacts + 7 lower-row contacts) and the
29/19 mm pocket/edge labels.  Repoint or supplement the inventory entries to
that retained diagram before claiming exact source-backed per-ID kinds.

## Medium — negative fixture evidence is structurally useful but does not meet its stated exit contract

Both rejected packets fail with CLI exit **2**, not exit 1 as Task 1/E1 says.
The retained logs accurately report exit 2.  Also, the Beastmaker “search
snippet” fixture is rejected because its retained path is missing; the
validator never reaches its Google URL.  The validator has no manufacturer
hostname/source-content check, so this is not proof that a retained search
snippet labelled `sourceTier: manufacturer` would be rejected.  Keep the
fixtures as missing-snapshot tests, but do not represent them as a complete
search-snippet provenance safeguard without an additional validation rule.

## Low — literal Beech certification wording

The retained/current Beech page says “FCS certified Beech” (apparently a
manufacturer typo).  `sourcedClaims[6]` normalizes that to “FSC-certified”.
Either quote the source’s literal wording or omit this nonessential
certification claim; do not silently correct a manufacturer claim in an
evidence packet.

## Verified evidence and contract items

- Packet SHA-256 values match their briefs and the source-audit record:
  Beastmaker `318bf1f6c155c094a953bdeddb63aa3734bb505e9fd315c66085498793d0302a`;
  Compact `3584001122d631be98cb122abc02c4033157c30250f17442cab6f8482940b240`.
  Every declared retained reference hash matches the present regular file.
- Both approved packets pass `validate_evidence_packet.py`; both negative
  packets fail with the expected retained-source error.  The Beastmaker
  compiler-negative log reaches `unknown hold_id`, emits no descriptor, and
  `compiler-scratch-invalid` is absent.
- Beastmaker’s 580 x 150 x 58 mm qualified Beech/shared-layout ruling is
  correctly retained.  Current primary evidence says `580mm X 150mm X 58mm`.
  The current standard/Tulip-series page says `580mm X 150mm Height X 5mm`;
  treating that final value as a conflict rather than a Tulip thickness fact is
  correct.
- The direct board records and packet inventories have matching ordered stable
  IDs: 22 Beastmaker and 19 Compact.  The Compact front and numbered diagram
  visibly agree with its 19-contact count; the Beastmaker official front
  visibly agrees with 22 contacts.
- Sources are manufacturer-tier only; no retailer claim has been elevated.
  Revision/date/locale, required front/three-quarter/clay-detail review views,
  generic pale-wood fidelity, and deliberate hardware/countersink/logo display
  omissions are recorded.  The latter are display simplifications, not claims
  that the physical products lack mounting hardware (both product pages say it
  is supplied).
- The approved packet JSON contains no proposal keys, paths, contours, masks,
  coordinate arrays, radii, or sections.  The required Astra handoff contains
  only the canonical IDs, frame, review views, omissions, and
  sourced-versus-estimated boundary; it contains no shape proposal.  The
  isolated invalid `.blend` is an allowed compiler-negative fixture, not a
  proposed board model.
- Ownership manifests name this workspace and durable packet roots.  Their
  listed compiler scratch path is absent.  There is no created simulator,
  tunnel, or other live external resource in this evidence task to clean.

## Required approval gate

Correct the Critical and High findings, rehash/revalidate the changed Compact
packet and brief/audit record, then obtain human approval of the corrected
briefs and official media before G1.  No geometry, package, runtime, plan, or
skill change was made by this review.
