# Composed predictor screen: closed on accuracy

The user authorized this isolated predictor/velocity change and subsequently all
isolated experiments. Native-only, original triangle authority, material model,
CCD, global correction and physical gates were retained. No product change.

The checkpoint adapter fixture now includes a nonempty contact hint and compares
all persisted fields against the explicitly converted expected checkpoint. It
passed, along with the 36 scalar force cases. The earlier 240 Hz preflight passed
20 complete checkpoint and control-decision comparisons.

The first composed 120 Hz step differs from the two-step 240 Hz trajectory by
24.403 µm, and from the strict same-input reference by 24.387 µm. Board height
matches within 0.194 nm, so the earlier gravity-integration defect is removed.
However, maximum rope endpoint velocity already differs by 28.514 mm/s.

The second step fails the unchanged 50 µm pose gate: 173.901 µm rope difference,
1.312 µm board-height difference, 208.017 mm/s maximum rope-velocity difference
and 28.975 mm/s board-velocity difference. Original-mesh/material metrics pass:
clearance margin 99.528 µm, strain 0.01252%, length error 1.370 µm. Neither step
hit a correction cap or retried. This separates physical feasibility from
trajectory accuracy: matching free integration cannot replace changing contact
forces. This is consistent with the derived changing-force defect; it does not
identify one specific contact feature as its cause.

Complete step times were 13.922 and 53.552 ms, using 6 and 12 QPs. These are two
host observations, not a p95 or device measurement. Timing includes diagnostic
trace collection. Execution stopped at the first pose failure; no formula,
tolerance or cap tuning followed. No simulator recording or adoption is justified.

Active contacts are recorded as QP-local row IDs with particle incidence and full
affine geometry. They are not stable triangle-feature identities across states.
The adjacent JSON binds evidence hashes. Exact process groups 83462 and 84195
were cleaned by the owner and independently verified absent.
