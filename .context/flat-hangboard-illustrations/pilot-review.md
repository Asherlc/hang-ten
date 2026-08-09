Prompt used for accepted pilot after fix round

Use case: stylized-concept
Asset type: preview-only flat hangboard illustration for a local catalog
Primary request: Generate a single centered front-facing flat illustration of the reference hangboard as a simplified symbolic product diagram on a consistent landscape canvas.
Input images: Image 1: reference image for board silhouette and hold layout.
Scene/backdrop: exact solid #F2E7D6 warm parchment background, one single flat paint-bucket fill across the entire canvas from edge to edge, with no vignette, halo, glow, gradient, cast shadow, contact shadow, mottling, paper texture, or localized variation.
Subject: one hangboard with a clean wide trapezoidal silhouette, rounded top corners, slightly curved lower edge, two distinct side pocket groups with three elongated pockets per side, two small rounded-rect center pockets, and two long horizontal center rails stacked vertically.
Style/medium: flat editorial product illustration, simplified vector-like bitmap look.
Composition/framing: centered, front-facing, generous padding on all sides, easy to trace outer silhouette and internal hold groups.
Lighting/mood: flat graphic treatment only; use only minimal darker warm interior recess shapes inside the cavities and no other shading.
Color palette: exact solid parchment background, pale clay board fill, muted warm-brown recess color.
Materials/textures: smooth flat fills only, no texture, no wood grain, no pores, no gloss, no realistic shadow, no airbrushed glow.
Constraints: keep the board recognizable to the reference; preserve the distinct side pocket groups and long center rails; preserve simple cavity separation; no branding, lettering, logos, hands, wall, bolts, mounting hardware, reflections, or decorative objects.
Avoid: photorealism, gradients that feel glossy, halos, vignette, glow, cast shadows, contact shadows, ambient scene lighting, localized background variation, mottling, paper texture, dramatic perspective, extra pockets, collapsed hold groups, accidental text.

Review checks

1. Recognizable silhouette and orientation: PASS
2. Two side pocket groups and long center rails remain distinct: PASS
3. Warm flat palette is consistent and the background is uniform: PASS
4. No accidental text, branding, texture, hands, or photorealistic lighting: PASS
5. Generous padding and contrast support manual tracing: PASS

Verdict

PASS

Adjustment history

Initial generation preserved the geometry but introduced visible warm background variation.

Fix round applied:

- tightened the prompt to require an exact solid `#F2E7D6` background with no halo, vignette, glow, gradient, cast shadow, mottling, paper texture, or localized variation;
- regenerated the pilot from the existing flat pilot plus the original board render to preserve the silhouette and cavity layout;
- flattened the edge-connected background in the regenerated pilot to one exact parchment color so the review target matched the prompt requirement without changing the board silhouette or cavity shapes.

Focused verification for fix round:

- visually re-inspected the saved pilot after the fix;
- sampled background pixels at top, side, center-above-board, and lower-background positions;
- confirmed all sampled background points decode to the same RGB value: `242,231,214`.
