# Evo passive natural-workout reproduction — 2026-10-02

The actual workout still **fails without AX polling, taps or Skip** after launch/openURL. Root individually reviewed all 12 whole screenshots: all four first-active captures show correctly red board pockets; all four sampled rest captures show incorrectly red pockets; all four following natural-hang captures show incorrectly blue pockets. No production fix or new acceptance is established.

The routine remained unchanged and the rest lasted **180.015567 seconds** between actual mode mutations. Four screenshots per phase were scheduled at +0.25/+1/+3/+5 seconds after the actual material mutation. [The protocol](raw/caption-passive-normal-workout-landscape/protocol.json), raw command list, harness and capture intervals preserve this distinction. There are no screenshots in the unobserved middle of the 180-second rest; this packet does not claim red persisted throughout that entire interval.

[Root's image review](raw/caption-passive-normal-workout-landscape/root-visual-review.json) and [full correspondence](raw/caption-passive-normal-workout-landscape/passive-correspondence.json) bind exact images and CPU evidence. Correspondence SHA-256 is `86de45e21c03c300cb87de7cdf04b8b1d5968214085f2f673289d0dec01d2b23`; [frozen summary](raw/caption-passive-normal-workout-landscape/frozen-summary.json) SHA-256 is `8ac008b6b456ab5b81713551f367de5ab77bdebacef5ab8d829aa6b0e1fa8a1d`. The initial trace and the post-hang-tail complete **147-record** copy are both retained unchanged.

## Late-bracket limits

The bounded sampler ended before the following natural hang. Early/Rest records include application/window census, but **no fresh late app/window activation or placement census is claimed**. New root/camera membership and Surface records remain available. The following-preview `highlight-before` record144, taken 7.025 seconds after the active mutation and after the late screenshots, retains cached active state and actual red material before applying the next mutation. Its requested mode is preview because it precedes that upcoming write; it is not evidence that the current material was already blue. This supplies the after-bracket for the visibly blue late-hang images, with the census limitation intact.

The hand mesh is absent in first-active +0.25/+1 captures and present by +3; judgments concern board highlighting. One image-review attempt used a duplicated path and failed before opening a file; the corrected whole image was then inspected. That failure is retained in the correspondence record. No image or old result was altered.

## Same binary and retained analysis

No build or source change separates this run from the C/D/E installed debug dylib `57b71dd01b35fb95de9519f85dde8c5232655788baeffe32deb982bd68640267`. The frozen report verifies all five Mach-O payloads and all 12 package comparisons unchanged. [Linked baseline provenance](linked-baseline-provenance.json) checks the run's frozen final source hashes against the exact [C/D/E three-file snapshot](../runtime-caption-boardmap-2026-10-02/frozen-source/snapshot.json) and patch; those source files are not redundantly copied. Later changing live source was not used for this proof.

[Initial-resize audit](analysis/initial-resize-audit/report.json) and [Astra's passive/resize review](analysis/architecture-committee/astra-passive-resize-review.txt) are retained analysis only. Startup navigation/resize/hand history differs from the passing standalone context, but this run does not identify a causal boundary or select a production implementation.

[retention-manifest.json](retention-manifest.json) maps all exact raw scratch bytes to retained paths/hashes. Earlier packet bytes, canonical CAD, global queue/lock and human acceptance remain unchanged. The exact owned Simulator and build/result paths remain live under the existing controller, with cleanup pending; the ownership snapshot is not deletion proof. Packaging made no source, runtime, index or commit changes. Any subsequent resize experiment is outside this appendix.
