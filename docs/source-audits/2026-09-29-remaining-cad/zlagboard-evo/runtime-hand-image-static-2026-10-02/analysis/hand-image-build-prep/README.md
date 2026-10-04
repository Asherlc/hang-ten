# Prepared hand-image prototype install/parity

This worker prepared only and executed no build, install, Simulator query, or controller signal. Root subsequently started the one build independently; the helper now has no xcodebuild execution path. Use the already registered Simulator `BDCA0D77-94C2-4A97-900B-443F75C64691`, cleanup controller PID `96137`, and `ios-diagnosis/DerivedData-placid-badger-cad-second-half`. Existing lifecycle owns cleanup; this helper neither creates resources nor changes its cleanup marker.

Root must grant exclusive build/install ownership and write a new gate copied from `gate-template.json`, setting both authorization booleans true only after review. Its five hashes bind the frozen `evo/hand-image-prototype-applied/source` files. Before starting, the helper verifies the exact cleanup controller PID and absolute-or-repo-relative lifecycle argv, resource registry/ownership, no cleanup request, booted owned device, and current source parity. No live prerequisite has been claimed to pass during preparation.

Invocation after that gate:

```sh
rtk proxy python3 .context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/hand-image-build-prep/build-install-parity.py --gate <root-authorized-gate.json> --completed-build-record .context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo/hand-image-prototype-build-command.json --output .context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo/hand-image-prototype-build
```

The output directory must be new. Root must fill `completedBuildRecordSHA256` from the completed successful `evo/hand-image-prototype-build-command.json`. The helper requires exit 0, no timeout/interruption, and the exact generic Simulator/Debug/existing-DD/600-second recipe. It retains a byte-exact copy of that record and its stdout/stderr; it does not rerun the build or create a result bundle. Install is bounded to 60 seconds and the exact UUID; the current installed container is queried after install (20 seconds), never reused from an older proof. No app launch or test run occurs.

The reviewed bounded-command helper retains exclusive raw stdout/stderr, timeout/interruption and exit records. INT/TERM is forwarded to that helper, which terminates/waits for its own process group. Failure stops subsequent steps; root's existing lifecycle retains responsibility for exact resource cleanup. No shared process or resource is signaled.

Parity covers five frozen source files, all five built plus five installed Mach-O payloads (including `HangTen.debug.dylib`), and twelve package files (Evo/Pro × board/descriptor/USDZ × built/installed): 27 checks. Mach-O magic discovery requires the known five-payload set and stops on unexpected additions. Package expectations are the unchanged prior frozen hashes, not newly generated baselines. Source hashes are checked before accepting the completed build record and after install. The root-applied frozen-source provenance binds the independently executed build. Build products remain in the already owned DD for the separately authorized runtime review.

Static syntax validation uses Python AST only. No compilation or runtime success is claimed. If root changes the prototype after this preparation, replace the gate with the new reviewed frozen hashes; do not relax a mismatch.
