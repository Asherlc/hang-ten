# Exact supporting-plane query census

The read-only instrumented solver preserved all original triangle calculations.
All 493 states of the 240 Hz turn/return prefix matched an independent original
solver's persisted physics checkpoint and correction decisions. Five fixed steps
were counted. This is a workload screen, not a contact replacement or speed test.

At step140, 837 fused queries visit 14,934 triangles but only 6,462 unique exact
supporting planes per query. Optimistic duplicate-plane elimination is **56.73%**,
above the preregistered necessary 50% threshold. The other checkpoints show
56.41–56.87%. The plane grouping is exact rational arithmetic over the original
Double vertex coordinates, with no approximate coplanarity threshold.

The whole mesh has 10,200 triangles on 9,233 planes, so global plane counts alone
would have hidden this query concentration. This result only justifies examining
reuse in the full row-producing query. Replacing a plane's triangles with one
contact would change fractions, edges, disconnected regions and witness order.
The already closed scalar-only oracle cannot justify a merit-only replacement.
No equivalence certificate, implemented replacement, latency improvement, app
adoption or normal-speed working video follows from this census.

The first build failed on native instrumentation visibility and performed no
simulation. The corrected build and its complete results are retained separately.
All exact new compile/run groups (79999,80179,80402) were cleaned and independently
verified absent. Product source, physical gates and the untracked inventory WIP
are unchanged. The adjacent JSON binds the plan, input plane IDs, output,
provenance and resource receipts by SHA-256.
