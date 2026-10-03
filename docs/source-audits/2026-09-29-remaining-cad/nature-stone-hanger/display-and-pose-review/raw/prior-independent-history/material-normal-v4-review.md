# Independent frozen material-normal v4 review

Both frozen one-lead trials pass the scoped material-normal witness check. Every positive force maps to its actual segment/fraction and has nonempty, local incident facets with nonnegative coefficients. Independent material-point membership and global-nearest arithmetic confirm the unchanged 10 micrometre near-tie activity. Actual facet-normal force reconstruction, rather than just radial directions, passes the unchanged 1e-5 nodal tolerance.

- `offset-anchor-probe.json`: 33 contacts; no invalid material cones. Radial nodal residual 2.35e-16; actual facet force balance residual 1.72285401e-15 and weighted normal-error bound 1.86601166e-15, both below unchanged 1e-5. Maximum tie gap 6.823389 micrometres.
- `native-seed-no-free-knee-probe.json`: 36 contacts; no invalid material cones. Radial nodal residual 2.22e-16; actual facet force balance residual 1.40394921e-07 and weighted normal-error bound 1.40394921e-07, both below unchanged 1e-5. Maximum tie gap 9.165163 micrometres.

Generic reported global-nearest distances differ from the independent calculation by up to 14.74804 nm, and carrier-foot coordinates differ from exact per-triangle projections by up to 6.18504 micrometres. The material points themselves lie on the local triangles and their independently computed near-tie gaps remain below 10 micrometres. No exact per-triangle projection claim is made.

The frozen helper explicitly rejects empty incident sets and recomputes the normal-cone residual from the actual outward normals and coefficients. Barycentric distribution preserves local resultant and moment. Original false tangential directions 0 and 1 remain rejected at residuals approximately 0.047398 and 0.182615. The v3 empty-cone failure and earlier raw diagnostic failures remain immutable history.

The 10 micrometre tie rule admits local opposing bore/rim wall components with actual outward-cone witnesses. These are legitimate directions within the stated numerical near-contact approximation; they do not establish exact simultaneous real-rope contact. Differences between generic triangle/global-nearest projections and the independent arithmetic are recorded explicitly; all activity distances are independently checked against the unchanged 10 micrometre rule. No routing or force tolerance changes.

This is explicitly numerical near-contact and discrete frictionless feasibility. The tie distance, 20 micrometre proposal margin, 10 micrometre contact-envelope allowance and unchanged physical-radius clearance certificate remain separate. The 10 nanometre mesh-incidence approximation and inflated-envelope tube-to-wall gaps are not exact native BRep or real rope contact proof.

No all-pose, 120 mm settled-height, cache, actual-app or global board equilibrium completion follows from these two one-lead trials. No optimizer, CAD job, solver, resource, shared change or packet build ran. Every input and the deferred configuration remained unchanged; `finalReady=false`.
