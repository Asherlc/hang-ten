# Task 1 fix-1 review — two-board evidence correction

Reviewed 2026-09-09 against the prior review `dbc559a5`, correction
`a4f216cf`, `AGENTS.md`, `docs/ADDING_A_BOARD.md`, the full
`add-hangboard` and `migrate-hangboard-to-3d` skill contracts,
`Tools/HangboardModels/evidence_packet.py`, its test suite, the original and
lean migration plans, the source audit, and the retained evidence packets.

## Result: approve the human evidence gate

The prior Critical, High, Medium, and Low findings are corrected.  The
packets and matched official media are approved for the required **human
evidence review gate**.  This approval does not authorize G1 geometry: G1
remains gated on that human review, as required by the migration plan.

## Rechecked corrections

- **Compact 56 mm.** The retained official numbered diagram's lower Compact
  row visibly labels only `#2 56 mm flat sloper` (left and right) and `#9 56
  mm round sloper` (centre).  The Compact packet maps each of the 19 stable
  IDs to its exact `#1`–`#11` callout and occurrence.  Its ruling, brief,
  source audit, and both migration plans now state that these are hold-depth
  callouts, not body/display thickness.  Overall Compact body Z/depth is
  source-unresolved and any existing model depth is explicitly estimated
  authored geometry.
- **Beastmaker per-ID provenance.** All 22 IDs now cite the retained official
  front only for the visual contact ruling.  Each record labels the stable
  ID, position, and edge-versus-pocket kind as inherited existing-package
  metadata, not manufacturer per-ID authority.  The packet, brief, handoff,
  and source audit consistently retain the 22-contact visual count and the
  manufacturer limitation.
- **Literal source wording.** The Beech claim and source audit preserve the
  manufacturer's literal `FCS certified Beech` wording; they no longer
  normalize it to FSC.
- **Negative fixtures.** The Beastmaker fixture retains valid
  `search-snippet.txt` bytes and its matching SHA-256, then reaches the new
  manufacturer-search-result URL rejection with CLI exit 2.  The Compact
  unsnapshotted-commerce fixture reaches the retained-file rejection with
  exit 2.  The corrected original and lean plan text requires those exact
  outcomes.
- **Hashes and durable records.** Recomputed hashes match the briefs and
  source audit: Beastmaker packet
  `1f5a57be0c32ee1fffa4b10c5d494d0540e4d7c7e03ecec78edb25837450b0cf`,
  Beastmaker handoff
  `34a91d0b0d799a31c232691ba29e270899c063f49305337860f363f240f5d3a6`,
  and Compact packet
  `3a6c2c63076fac70aeae5001bacda576038a766969eb8e01dced2a4bea96d91a`.
  The plan requires an Astra handoff only for Beastmaker; no Compact handoff
  is missing.
- **No geometry proposal.** Both packets validate, all declared retained
  source hashes match present regular files, inventories have 22/19 unique
  IDs in the same order as their board records, and neither packet nor the
  Beastmaker handoff contains geometry proposal fields, paths, contours,
  masks, coordinates, radii, or section prescriptions.
- **Compiler evidence.** The unchanged prior compiler log reaches
  `unknown hold_id`, and the owned `compiler-scratch-invalid` output is absent.
  The fresh Blender rerun is honestly recorded as a SIGSEGV during
  factory-startup GPU initialization before the fixture or compiler loaded;
  it does not replace the prior compiler evidence and it left the owned
  scratch directory absent.

## Validator review

`_is_search_result_url` rejects exact hosts and subdomains of Google, Bing,
DuckDuckGo, and `search.yahoo.com`, case-insensitively.  It does not falsely
match an unrelated hostname such as `notgoogle.com`; it does reject the
fixture's `www.google.com` URL after retained-byte/hash validation.  The
targeted suite has 22 collected cases and passes: `22 passed`.

Coverage is intentionally a bounded hostname denylist, not a proof that an
arbitrary URL is a manufacturer page: for example regional Google domains and
other engines such as Brave Search are outside this rule.  That limitation is
not a regression of the repaired fixture contract, because the human evidence
gate still verifies source identity/content and the rule prevents the exact
retained search-result failure mode.  A future general source-authenticity
policy should use an explicit allowlist or an expanded maintained search-host
set rather than relying on this narrow guard.

## Verification

- `python3 -B Tools/HangboardModels/validate_evidence_packet.py` returned 0
  for both approved packets.
- Both rejected packets returned 2 with their documented, distinct errors.
- `uv run --with pytest pytest Tools/HangboardModels/test_evidence_packet.py -q`
  reported `22 passed in 0.08s`.
- `git diff --check dbc559a5..a4f216cf` and the current working diff are clean.

No geometry, package, runtime, or skill implementation was changed by this
review.
