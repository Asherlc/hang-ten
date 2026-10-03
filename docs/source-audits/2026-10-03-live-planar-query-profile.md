# Planar query diagnostic, no acceptance retry

One serial fixed 3,236-query run splits the already failed clipped planar query.
Instrumentation enabled/disabled outputs have identical complete Double bits and
ordering. Original maximum depths also match exactly on this corpus.

Instrumented total46.846ms: original triangles/merge22.989ms for131,143 faces;
BVH traversal/sort11.475ms for3,236 queries; planar candidate1.540ms for1,684
calls (membership nested0.502ms for3,092 calls); planar hits/merge0.611ms;
remainder10.232ms. Region counts18,149 include many plane-separated skips;
1,771 boundary pairs remain. Empty timer pairs cost0.647ms per10,000, so the
per-face timers materially inflate their bucket. These diagnostic times cannot
be substituted into a complete-step budget or the failed acceptance gate.

Polygon membership is too small to justify another tuning continuation. The
remaining original-face work and traversal warrant a distinct representation
hypothesis, not a speed claim. A source-transform ambiguity and a missing
Foundation import were fixed before the one successful diagnostic run. Three
newly owned process groups are independently absent; hashes are in companion
JSON. Product source and seated cords unchanged; real-time video outstanding.
