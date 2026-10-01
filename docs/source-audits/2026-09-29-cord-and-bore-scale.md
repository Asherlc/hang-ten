# Cord and bore scale audit — 29 September 2026

The operator reports that the rendered cord looks far thinner than the openings
and requests three times the current cord diameter. This audit distinguishes
actual scene dimensions from uncertain reconstruction dimensions. It does not
approve reducing the requested thickness.

## Evidence and dimensions

| Quantity | Evidence | Finding |
| --- | --- | --- |
| Mini Bar overall length | [Lattice product page](https://latticetraining.com/product/mini-bar-portable-hangboard/), retrieved 29 September 2026 | Marketing specification says 15.5 cm; the same page's tech table says 15 cm. The current CAD uses 155 mm, consistent with the specific marketing specification. |
| Mini Bar scene width | Native `BoardModelRealityTests.testCordAndCADModelShareMeterScale` | RealityKit body bounds measure 0.155 m. |
| Clavellium scene width | Same native test; retained approved display reconstruction | RealityKit body bounds measure 0.080 m. This does not establish a factory measurement. |
| Historical displayed cords before the operator correction | Same native test, transient cord segment visual bounds and entity scales | Both boards render a 4 mm diameter with unit cord and segment scales. There is no extra relative scene shrink. |
| Mini Bar internal bore | Native `LeftChannelDiameter` and `RightChannelDiameter` sketch circles | The CAD uses a 2.7 mm radius. `suspension.json` explicitly calls the resulting 5.4 mm diameter a display estimate. The manufacturer page supplies no bore or cord diameter. |
| Clavellium center opening | Source-bound physics descriptor exported from native channel void | The reconstructed opening is 24 × 26 mm. These dimensions remain estimates; see the Clavellium source audit. |
| Requested cord | Operator instruction, 3× current diameter | 12 mm diameter. It fits the reconstructed Clavellium center opening. |

The Mini Bar's authored 5.4 mm throat cannot accommodate a 12 mm diameter within
that CAD solid. This is a model inconsistency requiring evidence review, not
proof that the real product cannot accommodate the requested appearance. Neither
an exception to the 3× instruction nor a larger factory bore is established.
Surface openings seen obliquely are not reliable measurements of the internal
throat. No automatic pixel measurement or geometry inference was used.

## Verification

The initial native iOS Simulator test passed with both actual USDZ models and
4 mm rendered cords: one test, zero failures. The committed regression now
checks metre-scale body widths, 7 mm segment diameters on both radial axes for
static cords, a 3.5 mm vertex radius for live cords, and unit cord/segment scales.
Both shipped static suspensions also use radius 3.5 mm. The later correction
below supersedes the historical 12 mm request; live physics is integrated only
for Clavellium, and catalog/device gates remain separate.

## Operator correction after the initial audit

The operator subsequently rejected the 12 mm target, supplied **7 mm** as the
real cord diameter, and explicitly confirmed this for both Clavellium and
Mini Bar. The new target is **3.5 mm radius** for rendering and collision,
replacing the earlier threefold target on those boards. The retained 2 mm
baseline uses scale 1.75. This operator statement is the source for the updated
diameter; it does not verify the estimated CAD bore. The Mini Bar's 5.4 mm
throat estimate remains inconsistent even with 7 mm and requires evidence
review. Clavellium's documented round-cord adaptation of a flat sling remains.

## Mini Bar correction from the confirmed diameter

The two native channel sketch radii are now 3.7 mm, giving a **7.4 mm
estimated bore diameter**. This uses the operator's 7 mm cord measurement
plus 0.2 mm radial display clearance. It supersedes the unsupported 5.4 mm
bore estimate and preserves the manufacturer's 155 mm overall width.
`DiameterProvenance` on both native sketches records this distinction.

The source audit also found that the original ergonomic-jug contact surface
continued across the bore openings. A ray through each displayed mouth hit that
contact overlay, whereas the exact native wood solid admitted the ray into the
channel. Each contact surface is now a parametric intersection with the final
wood body, preserving the four grip identities while excluding openings from
rendering and picking. A failing exported-mesh ray regression captures this
physical/render discrepancy. The USDZ remains unbound and contains no cord.

The static authoring solver needed a bounded fallback for curved channel
sections whose closest separation underestimates the wider throat. It increases
only its temporary closure until there is one bearing outline; all resulting
routes still undergo signed-distance checks against the original complete CAD
solid. The existing rectangular-channel behavior is unchanged. The four Mini
Bar poses regenerate with 3.586–3.588 mm minimum sampled exterior centerline
clearance at the confirmed 3.5 mm radius. Each loop remains 0.82 m and the
CAD-measured hidden centerline length remains 87.214214 mm.

Current source/export, native visual proof and package hashes are recorded in
the delivery evidence after the final contact-surface rebuild. This diameter
correction does not establish Mini Bar live dynamics; its curved-channel and
cross-rope adapters remain a separate promotion gate.

### Final diameter-correction validation

The Mini Bar CAD source rebuilds byte-identically to model SHA-256
`4b4e9950b01fa303f36b27ad2841ea697cc4ed93f5dff61827b11a6f3fcfa2ca`.
The package tests plus focused diameter/section tests pass (419 tests).
The corrected package passed the full native suite (1,280 tests, three
existing skips, zero failures). The screenshot audit then caught clipping
while orbiting; after fitting the same geometry in the actual camera basis,
all 20 native scene tests pass, including all four Mini Bar poses at three
azimuths. User-selected grip rotations are unchanged.

[Front/side/top mesh comparison](2026-09-29-mini-bar-seven-mm-evidence/strong-owl-mini-front-side-top.png)
and [all four native grip views](2026-09-29-mini-bar-seven-mm-evidence/strong-owl-mini-native-pose-matrix.png)
were shown during review. The latter uses the complete board-map rectangle
measured from native accessibility bounds; untouched full-screen originals
and build/source hashes remain in the same evidence directory. The delivery
lock verifies 49 models and 117 pinned files.
