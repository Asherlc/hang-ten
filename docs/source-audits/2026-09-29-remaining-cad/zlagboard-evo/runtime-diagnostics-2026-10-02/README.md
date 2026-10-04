# Evo workout rendering diagnostics — 2026-10-02

These temporary DEBUG experiments have not established a production fix. Accepted native geometry, canonical packages, delivery lock, and human acceptance records remain unchanged.

The complete trace shows correct CPU material state around a visibly stale board frame. Removing the hand host produced one successful run between failing controls. A plain PBR second host reproduced the failure. Explicit virtual camera and non-AR ARView probes failed. An entity visibility change rendered its removal but not its subsequent restoration. Recreating the child display view preserved its loaded scene yet made the board disappear.

Raw command logs, images, complete traces, patches, and historical reports are copied byte for byte from the workspace scratch directory. The initial hand-OFF visual misclassification remains retained alongside its explicit correction; use `raw/hand-host-probe-correction.json` and `raw/root-hand-host-reversal-review.json`. Root reviewed all three semantic-identity frames; `raw/root-semantic-identity-review.json` records that both board and hands are absent in the exact initial settled frame. No failing result is rewritten as passing.

`retention-manifest.json` binds every copied byte to its original scratch path and SHA-256. `final-diagnostic-source.patch` records all current temporary source changes against the stated baseline. These changes are experimental, not proposed production code. Simulator/DerivedData cleanup is pending at this snapshot.
