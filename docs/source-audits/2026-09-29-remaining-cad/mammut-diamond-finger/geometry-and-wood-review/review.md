# Mammut Diamond Finger source and display geometry

This record explains the source evidence and display estimates behind `Hangboards/mammut-diamond-finger.FCStd`. The [human review record](../human-review.json) records acceptance of the shown revised geometry and wood finish with “Good enough”.

## Primary evidence and supported geometry

The [full manufacturer press document](sources/manufacturer-press-release.docx), [extracted text](sources/press-release-text.txt), three complete embedded images and [source provenance](sources/press-provenance.json) are retained together. The publisher is Mammut; the original [press DOCX](https://cdn.uc.assets.prezly.com/da46d83b-e3f0-484b-b349-2047c1a0da6c/-/inline/no/202003_Mammut_DiamondFingerHangboard.docx) has SHA-256 `7312bb772da797aca3cfa7f6368761cb5a9c97cfda00f19537888fa2ac7fcc1f`. Its product facts state 85 cm width and walnut wood. Additional manufacturer research was user-authorized. The embedded product picture repeats the retained front view; it does not supply a manufacturer side view.

The exact-revision [manufacturer product photograph](https://static.mammut.com/master/2060-00020-7458_main_75743.jpg) and [manufacturer manual](https://static.mammut.com/file/2060-00020_man_en_070420_DiamondFingerHangboard_Manual.pdf) remain the visual evidence referenced in [source reasoning](native-author/source-reasoning.md). Their already-retained hashes are respectively `d08c0f36233171789ff450f4429646079f67ca2506da2f794ecf61089982014f` and `0ada1438277dae39cf96e45dc72f9d0aabe383502718368f143212bf8e51b024`.

The sources support flatter machined terraces and straight chamfers, narrower upper ends, three lower lobes with straight-sided notches, horizontal pill-shaped openings and slots, Z-shaped lateral shelves, an angular central tray with a lower dip, upper inset steps, and a central sloper. These features were deliberately authored as native geometry; no pixels were measured, traced or registered.

Only the 850 mm overall width is manufacturer-backed here. The 196 mm height, 78 mm thickness, whole side profile, cavity depths, floor slopes, wall tapers, bevel widths and round radii are operator-selected display estimates. The 42 mm mono depth, 0.8 mm rounds and specific floor angles are not manufacturer specifications. The sampled tray/shelf recess depths in the diagnostic reports describe the authored CAD, not a measured physical board. The central and lateral floors deliberately tilt toward the front; the sources do not establish that angle. This choice must be disclosed during human review.

## Display finish

The display uses the shared procedural wood finish. Package-owned `media.display.surfaceFinish: "wood"` selects it; no new appearance schema or separate wood renderer is introduced. This is the existing generic wood display finish, not a calibrated walnut grain or stain reproduction. USDZ meshes must remain unbound, without materials or textures; wood is applied by the app renderer.

## Geometry review

Review the [app comparison](app-before-after.png), [front/side/top comparison](front-side-top-comparison.png), [compiled raking comparison](compiled-previews/comparison-raking.png), and [native section diagram](native-final/previews/native-central-and-lateral-sections.png). These show the approved display revision; they do not establish manufacturing tolerances.

The [native partition proof](native-final/partition-fix-proof.json) records that the export seams preserve the body and contact surfaces. The [export verification](runtime-proof/export-verification.json) records matching native facets, watertightness and unbound USDZ meshes. Capture-time identities are retained in those reports; the current runtime export is generated from CAD.

[Installed-app provenance](integration/installed-app-provenance.json), [app validation](app/after-app/validation.json), and [drag observations](app/after-app/extra-validation.json) bind the following views to the displayed revision. The reviewer found no source-supported shape blocker. Shared wood is golden tan rather than a calibrated walnut reproduction; lighting can make the estimated recesses appear shallower than their native sections.

- Actual app: [unselected wood](app/after-app/wood-unselected.png), [left jug](app/after-app/jug-left.png), [central tray](app/after-app/center-tray.png), [right inset](app/after-app/inset-right.png), [first orbit](app/after-app/wood-orbit-left.png), [second orbit](app/after-app/wood-orbit-right.png).
- Prior app: [left jug](app/before-app/jug-left.png), [central tray](app/before-app/center-tray.png), [right inset](app/before-app/inset-right.png). The [comparison provenance](app-comparison-provenance.json) identifies the before/after composition.
- Official exported geometry: [front](compiled-previews/comparison-front.png), [side](compiled-previews/comparison-side.png), [top](compiled-previews/comparison-top.png), [oblique](compiled-previews/comparison-oblique.png), [raking](compiled-previews/comparison-raking.png), with [compiled-preview provenance](compiled-previews/provenance.json).

The inherited description of 21 surfaces versus 16 selectable contacts is not evidence for adding grips. Contact inventory changes require primary source support and a separate review.
