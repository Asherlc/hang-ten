# Confirmed geometry helper inlining

Single original-type WMO IR confirms outlined triangleClosest, segmentPair,
FusedWitness.consider and mergeFused calls in the fused outside narrowphase. The
native candidate adds only @inline(__always) to those four original functions;
it includes no edge tuple change, compiler flag, arithmetic or model change.
Candidate IR removes the targeted calls, but the outside function grows from
970 to 2,942 LLVM instruction lines. Static line counts are not operation counts.

All 934 query and 2,802 moving-sweep bit checks and RED controls passed. Twenty
strict paired steps retained complete state, conservative clearance bounds and
rollback. All 139 current-source prefix steps and seven alternating step-140
pairs matched complete checkpoint and correction schedule bits, with two
corrections and zero caps or retries.

The median complete-step ratio was **1.055324**, failing the fixed **≤0.80** gate
and showing a regression on this checkpoint. Removing calls is not itself a
performance improvement. The line is closed without annotation/flag tuning,
combining rejected candidates, timing retries or 540-step expansion. No product
code changed; no app/device speed or real-time claim follows. The adjacent JSON
binds the evidence and seven independently verified deleted child groups.
