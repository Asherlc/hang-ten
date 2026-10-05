# KARMA8A Mini — review #11

The current native revision corrects the wood seat beneath the unchanged granite insert, assigns all exposed stone surfaces to the existing runtime granite finish, and shortens the estimated cord leads from 200 to 110 mm. Its three factual contacts and three authored positions are unchanged. Human acceptance remains pending.

The manufacturer documents 105 × 60 × 30 mm, a 15 mm wooden edge, a 15 mm granite edge and a 60 mm pinch. There is no separately sourced jug for this revision. The native pinch check now measures the correct 60 mm Z span rather than the 30 mm thickness. The front and oblique manufacturer photos show the insert seated against the lower wood rail; unpublished fit details, radii, grooves, cord lengths and support offset remain display estimates. See [source mapping](source-mapping.json).

The prior CAD had 377.773 mm³ of overlapping wood and granite and an unsupported seam beneath the insert. A local native wood seat subtracts the exact unchanged insert and restores 34.436 mm³ beneath it. The corrected overlap is zero. The exterior, all six existing groove cuts, upper wood and pinch surfaces, insert placement, contact facts and cameras are preserved. All exposed insert faces now belong to `nature_stone`; the existing runtime metadata selects wood for the body and granite for that node. The USDZ contains no materials or textures.

The [whole front, side and top comparison](comparison-front-side-top.png) shows the exact prior committed model at left and current export at right. These are neutral CAD renders; they do not prove app texture, selection or interaction. [Oblique comparison](comparison-oblique.png) makes the fitted lower seat visible.

All three canonical cord poses were freshly solved against the current CAD solid; all 12 cached strand routes pass continuous clearance and intersection checks. Only the free leads have a taut-length target; the existing 40 mm cross-return allowance is preserved and is not a claim of tautness. Hidden cord connections are not known from the retained sources. No hidden bore or connection was added.

Native reopen/edit/restore, independent contact/solid/actual-mesh checks and two byte-identical compiler runs pass. All 284 Python tests and all 64 canonical packages pass; Android resource staging matches exact bytes. Current iOS build and app review status are recorded separately in [runtime status](runtime-validation.json). App appearance, wood/granite restoration, highlights, actual workout and orbit behavior remain unverified. Earlier batch captures refer to the original migration assets and cannot establish acceptance of this revision.

[Contact preservation](manifest-preservation.json) · [native checks](independent-native-check.json) · [export checks](independent-export-check.json) · [cord checks](cord-check-report.json) · [continuous clearance](continuous-cached-route-certificate.json) · [Python results](python-validation.json) · [Android staging](android-staging-parity.json) · [delivery identity](delivery-check.json) · [package scope](package-scope-proof.json) · [cleanup](resource-cleanup.json)

The [independent delivery audit](independent-delivery-review.json) passes all 45 checks of identity, preserved history, counts, links and cleanup. It does not establish app appearance or human acceptance.
