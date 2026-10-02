# One-shot nonlinear KKT defect correction

The retained late-step audit localized backtracking to finite-step force–geometry
interaction. This separately registered screen tests that measured mechanism on
only update 15 at alpha 0.23872889767888264, the first recorded proposal with no
native witness-branch changes. It computes one correction and discards the state.
No closed configuration is rerun, no cap/physical threshold is changed, and the
closed explicit derivative kernel is not integrated into a solver.

For F = (a, b, h, sv), p = alpha d and the retained origin's complete Jacobian K,
compute R = F(y+p) - F(y) - Kp, solve Ke = -R and evaluate y+p+e. Retained condensed
matrix entries are unchanged. Their contact D J-transpose J term is removed and
-J ds restored when constructing the complete stationarity Kp. Equality and
contact feasibility defects and the exact slack–force product defect are included.
Existing contact elimination recovers correction forces and slacks. No extra
alpha/alpha-squared scaling of e, repeated centering, clipping or second correction.

[Wachter–Biegler section 2.4](https://optimization-online.org/wp-content/uploads/2004/03/836.pdf)
provides precedent for reusing a KKT factorization after a rejected trial, but its
SOC primarily corrects feasibility. This full KKT stationarity-defect correction
is distinct; no stock IPOPT method, Maratos diagnosis or convergence theorem is
claimed. The standalone native screen reconstructs and factors the original matrix
then solves one RHS; it does not measure live factor reuse or frame speed.

## Local result

- Original proposal residual score: 1833.222; initial score: 434.403.
- Corrected score: 202.371; unchanged Armijo maximum: 434.392.
- Original matrix residual: 3.39e-21; one band-plus-height solve, no refinement.
- Full recovered linear certificate: stationarity 1.22e-20, equality 1.77e-21,
  contact feasibility zero, complementarity 3.23e-27.
- Minimum resulting s/v fraction of base: 0.776475 / 0.562698, above the original
  0.005 fraction-to-boundary margin.
- Combined proposal-plus-correction relative displacement per rest link:
  0.0146007, below the original 0.1 trust bound; maximum movement 0.139006 mm.
- Original native ordered-topology refresh passes and all 280 particles are
  outside under the original ray parity. Refreshed portal segments 161 and 117
  match those used by the independent score, with fractions 0.996296 and 0.000869.

This formerly rejected proposal now passes the original **iteration trial guards**.
It is neither a complete accepted time step nor a final physical/numerical
certificate. Whole-motion CCD, final convergence/global merit, all-contact physical
verification, trajectory, catalog, frame performance and device gates are still
required. No state was published and no app recording was made.

Astra reviewed signs/scaling and independently checked portal fractions. The review
found that output correctedTerms contained updated force/slack values but origin
geometry fields. The field is now explicitly named
updatedForceSlackTermsWithOriginGeometry; the raw first output and original input
bindings are retained. Numerical arrays and score were not recomputed or changed.
Native guard build initially used a nonexistent input decode API; the fresh next
build uses the original descriptor decode/validation path. No algorithm change.

All six fresh process groups and four drivers were cleaned and checked absent.
No app, model, material, seated-cord, workspace/branch, rendering or PR529 changes.
Broader Python/Xcode suites were not rerun; the failing live inventory WIP remains
untracked. Evidence, source snapshots, exact R/RHS/correction, independent recovery
checks, original native guards and ownership receipts are in
`.context/strong-owl-live-physics-nonlinear-defect-screen`. Companion summary binds
SHA-256, including the pre-normalization output and reviewed source snapshot.
