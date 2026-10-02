# Independent Stone Hanger guide feasibility review

The retained probes do not provide a supported final route. The reaction sign
is correct: for unit tangents directed away from a point, material-on-rope
reaction is `−T(a+b)`. It must lie in the nonnegative cone of **active** outward
material normals. Left pitch60 node51 asks for +X reaction while its open groove
can only supply X≤0; it is an unsupported turn. Nodes 52 and 56 have zero cone
residual but are 1.7505 and 1.9995 mm from material, so they cannot bear a 1.5 mm tube.
The retained pitch60 path separately fails continuous radius clearance at
1.311624 mm; optimizer success is insufficient.

The corrected endpoint ±49.75 mm is inside the existing 5.5 mm visible bore interval,
between the real ±52.5 mm side plane and ±47 mm cutoff. The nominal groove/bore
intersection has positive radial room: 0.25/0.50 mm for the actual tube,
0.23/0.48 mm with the existing 0.02 mm proposal margin, and 0.05/0.30 mm under the old
0.2 mm seed inflation. This does not prove the full topology impossible. A
material-side junction can support a cone of both wall normals. The rounded
broad-face departure remains unproven by the retained failures.

Full-length forced station traversal is stronger than “Enters side holes;
notches guide it”. A half-open groove cannot pull a rope inward at an open-side
bend. A taut frictionless cord also cannot follow nonzero circumferential
curvature on a concave cylindrical inner wall; its required reaction has the
opposite sign. Straight passage and supported turns at real convex rims or
junctions are different cases. Arbitrary station equalities and an entire
circular-disk constraint on the open half can supply a fictitious force.

The smallest justified change is authoring/pose work: preserve the native body,
endpoint and tube gates; use actual guide-contact windows rather than forced
full axial stations; reject off-wall or inadmissible-cone turns; and select only
an explicitly estimated pitch/exit side that passes native bearing-up and all 16
route certificates. Use 0.02 mm as the existing proposal margin without changing
the 1.5 mm radius/10 µm final certificate. If no such pose passes, retain
infeasibility rather than add a peg, close the opening or relax gates.

This is a local analytical/code review, not a generated route or global
mechanical-equilibrium certificate. It excludes the active margin-aligned
probes. Exact input hashes, independently recomputed force rows and limits are
in inspection.json. No native jobs, resources, images, shared files or packet
configuration were changed; finalReady remains false.
