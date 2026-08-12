# Compact II presentation repair evidence

`CompactBoardIllustration.original.png` is the byte-identical checked-in
presentation source (SHA-256
`5d687fb6e1a33f0f1d9ae221facfc2c831de66d0f9b95b1febadfd924c631b34`).
It is retained as reference evidence only and does not establish board facts,
hold identity, semantic mappings, or vector geometry.

The approved `assets/CompactBoardIllustration.png` is an
`external-generative-adaptation` of that source. Two unconstrained image-edit
attempts were rejected because they changed the board crop and geometry; they
were not used. The accepted file was created by OpenCV Telea pixel inpainting
with radius 3, with writes confined to six integer circular masks of radius 18
pixels centered at `(374, 148)`, `(743, 148)`, `(1035, 148)`, `(1400, 148)`,
`(405, 309)`, and `(1371, 309)` on the original 1774 × 457 canvas.

An exhaustive RGB comparison verifies that every pixel outside those masks is
byte-identical to the source, every mask contains changed pixels, and no other
area changed. Full-resolution inspection of the original, repaired image, and
magnified six-region contact sheets confirmed that all six mounting holes were
removed while the crop, silhouette, board scale, background, hold boundaries,
and other non-fastener detail remained unchanged.
