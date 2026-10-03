# Independent frozen material-normal v3 review

The frozen v3 trials fail material-normal witness closure. Local mapping, closest-feature distance/tie arithmetic, force sign and radial barycentric balance independently pass, but positive force contributions have empty incident facet arrays and empty cone coefficients while reporting zero cone residual. An empty cone reconstructs zero force, not its unit radial direction.

- `offset-anchor-probe.json`: 33 contacts; invalid material cones [20, 22, 25, 26, 28]. Radial nodal residual 2.14e-16, but actual incident-facet force balance residual 0.147059947 exceeds unchanged 1e-5. Weighted normal-error bound 0.157225477; maximum tie gap 6.830463 micrometres.
- `native-seed-no-free-knee-probe.json`: 36 contacts; invalid material cones [13, 20, 21, 23, 25, 26]. Radial nodal residual 2.43e-16, but actual incident-facet force balance residual 0.140210435 exceeds unchanged 1e-5. Weighted normal-error bound 0.158108984; maximum tie gap 9.165163 micrometres.

Reject empty or nonfinite incident cones and recompute residual from the actual outward normals and nonnegative coefficients before using a force. Check that the force-weighted facet reconstruction passes the unchanged nodal tolerance. Both radial force assembly and local moment preservation are correct; their near-zero residual cannot waive this missing material support.

The 10 micrometre tie distance is accurately reported and its nonempty cones provide local material directions. However, some opposing wall components currently rely on empty cones, so their legitimacy is not demonstrated by this v3 pass. Original bad directions 0 and 1 still fail at residuals approximately 0.047398 and 0.182615. Retain v3 and the former false-positive and exact-closest-only failures as raw diagnostic history.

This is explicitly numerical near-contact and discrete frictionless feasibility. The tie distance, 20 micrometre proposal margin, 10 micrometre contact-envelope allowance and unchanged physical-radius clearance certificate remain separate. The 10 nanometre mesh-incidence approximation and inflated-envelope tube-to-wall gaps are not exact native BRep or real rope contact proof.

No all-pose, 120 mm settled-height, cache, actual-app or global board equilibrium completion follows from these two one-lead trials. No optimizer, CAD job, solver, resource, shared change or packet build ran. Every input and the deferred configuration remained unchanged; `finalReady=false`.
