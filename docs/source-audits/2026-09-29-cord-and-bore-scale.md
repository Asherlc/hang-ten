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
| Current displayed cords | Same native test, transient cord segment visual bounds and entity scales | Both boards render a 4 mm diameter with unit cord and segment scales. There is no extra relative scene shrink. |
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

The native iOS Simulator test passed with both actual USDZ models and rendered
cord meshes: one test, zero failures. The test checks metre-scale body widths,
4 mm segment diameters on both radial axes, and unit cord/segment scales. The
live 12 mm rope is not yet enabled in the app; the numerical settling gates are
still in progress. This audit makes no live-physics completion claim.
