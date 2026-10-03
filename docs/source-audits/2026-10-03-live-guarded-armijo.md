# Guarded sufficient-decrease screen

Native-only stricter acceptance: original merit test intersected with Armijo
sigma=0.1. The guarded derivative covers objective and L1 lengths only when
all other merit hinges are strictly inactive. Equality at a hinge falls back.
Supports have zero displacement; attachments follow board-height displacement.
Fixtures check one-sided absolute derivatives, hinge equality and those bindings.

The exact-decoded 108-step original prefix matches retained counts/alpha/norms.
On fixed step109, **no correction is eligible**, so all 11 QPs and the result
match original exactly. Original mesh metrics pass; strict reference converges
in 15 QPs and differs by 0.14715 µm. The fixed <=5-QP mechanism gate fails before
timing; **guarded variant CLOSED, unadopted**. No seven-pair result exists and this
does not establish failure of a fully differentiated Armijo method.

The first build failed in a fixture; the next runs caught a one-ULP Foundation
NSDecimalNumber parsing error in the prior reference, already documented by
ExactCheckpointJSON.swift. Using that existing exact decoder fixes the harness,
without relaxing equality. All original physics, QP, global merit function,
trust/caps/convergence/mesh/CCD/rollback conditions remain unchanged.

A complete contact derivative is a distinct necessary-output successor to the
ineligible guarded rule, with its own derivative oracle and fixed checkpoint.
It must not be sold as a route to 4 ms from this single tail example. No product
change or recording is claimed. Adjacent JSON binds evidence and cleanup.
