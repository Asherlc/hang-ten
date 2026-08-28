# Rock Prodigy Training Center 7/3 repeater source audit

Checked 2026-08-27 against Trango's primary [Rock Prodigy Training Center Use
Instructions PDF](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155).

Classification: board-flexible. The source calls for athlete-selected grips,
does not name a board, specify grip types, prescribe a grip order, or identify
hold features. The import therefore has no `HoldTarget`, applies on every
board, and never substitutes a board's metadata for the source choice.

The source specifies a variable-length session: approximately 5–10 grips and
1–3 sets per grip. Hang Ten represents one exact 4:00 set template rather than
inventing a grip list, an order, a total set count, or a total workout duration.
Athletes repeat the template manually for their chosen grips. The template is
`.official`: every timed interval and instruction is retained unchanged; the
absence of a selected hold is intentional, not an adaptation.

| Source instruction | Imported mapping | Audit decision |
| --- | --- | --- |
| Select approximately 5–10 grips. | Plan subtitle and seventh-repetition instruction say “Self-selected 5–10 grip routine.” | Retained as a range; no grip names, order, or hold targets invented. |
| Complete 1–3 sets on each grip, then move to the next grip. | Seventh-repetition instruction says “complete 1–3 sets per grip, then move to the next.” | Retained as a range; the single set template is manually repeated. |
| A set is 7 repetitions of a 7-second deadhang followed by 3 seconds rest. | Repetitions 1–6 are 10-second rows with 7-second timed work and 3-second rest. | Exact timed cycle retained. |
| After the seventh hang, rest until 4:00 from the first hang (2:53). | Repetition 7 has 180 seconds total with 7 seconds timed work and 173 seconds resting; combined with the first six 10-second rows this ends at 4:00. | Exact terminal recovery retained; it is part of the source set rather than omitted as a post-workout rest. |
| The table rests to 4:00 after the seventh hang (2:53); the surrounding prose separately says a set is followed by a 3-minute rest period between sets. | The seventh-repetition timer uses the table's 2:53 recovery to the 4:00 mark. A following 180-second `.rest` step represents the prose's 3-minute between-set rest. | Both source timings are retained as distinct instructions. The source does not call the table recovery the between-set rest, so the import makes no such equivalence. |
| Use two hands; no pull-ups or lock-offs. | Seventh-repetition instruction says two-handed deadhang and “Do not pull up or lock off.” | Retained verbatim in meaning; no grip or finger cue inferred. |
| Make the final set near failure; change 10 lb between sets and 5 lb for like sets from workout to workout. | Seventh-repetition instruction retains the near-failure and 10 lb / 5 lb loading guidance. | Retained; no load direction or values beyond the source are added. |

No warm-up, cooldown, grip/finger cue, accessory exercise, target mapping, or
fixed total session duration was added. The routine is intentionally
targetless, so there are no board-resolution mappings to audit.
