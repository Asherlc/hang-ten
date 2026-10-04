# NUG shorter display cord authoring

Frozen candidate SHA-256: `d34a007dacf5d8718c67e68a605d3496097e26e87539aa804d4903cee3255472`.

The user accepted the revised pinch regions and requested a shorter cord. Four lead rest lengths are now 110 mm (previously 300 mm); anchor offset above board bounds is 50 mm (previously 100 mm). These are explicit display estimates, not manufacturer cord-length claims. Retained manufacturer cord diameter remains 6 mm, and hidden joins remain unspecified.

The unchanged native solver generated all 24 routes across six poses against the final approved source-bound solid. Each pose has solved Y translation -0.004185507 m and a 54.185507 mm vertical support-to-board-top gap. Fresh scratch `--check` passed. Independent certificates passed the full-solid continuous clearance check and complete tube collision gate, preserving the actual mouth and outward entry for every lead.

Physical wood, pinch/jug/edge regions, source/model/descriptor bytes, strand IDs and topology, radii, terminals, camera settings, rotations, horizontal translations, and solver parameters remain unchanged. The semantic mutation proof lists only lead lengths/provenance, anchor offset/provenance, and generated pose heights/routes. No routes were hand authored. The deterministic native section solve is a bounded display approximation; it makes no physical equilibrium or global optimum claim.

Evidence: `solve-short-apply.json`, `solve-short-check.json`, `24-route-certificates.json`, and `mutation-proof.json`. The isolated candidate is `isolated-root/Hangboards/frictitious-nug/suspension.json`. The live-package-unchanged certificate records the state before parent promotion; the parent subsequently promoted the exact candidate and owns live verification, visual review, delivery-lock updates, and Git work.

Ownership: all authored artifacts remain under this workspace-owned scratch directory. No external resources or servers were created; no cleanup remains in this lane.
