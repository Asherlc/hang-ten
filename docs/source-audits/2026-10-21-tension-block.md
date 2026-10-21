# Tension Climbing The Block: primary evidence and contact facts

This audit covers the **2024 maple revision** of **The Block** sold by Tension
Climbing, reviewed on 2026-10-21. The
manufacturer's product handle is `the-block-2`, product ID `8010356195509`,
with one `Regular` option. The handle suffix does not establish a version number.

The manufacturer's [2025-08-25 no-hang guide](https://tensionclimbing.com/blogs/blog/death-taxes-and-the-desire-for-stronger-fingers-a-three-part-series-on-no-hang-training),
FAQ 3, expressly dates the change to maple and increased thickness to 2024.
A [short exact revision excerpt](2026-10-21-tension-block-evidence/manufacturer-2024-maple-revision.md)
is retained. This dates the physical revision but supplies no absolute dimensions.
Older cherry-product dimensions do not establish current maple measurements.

## Approved manufacturer evidence

The user approved these **exact four retained manufacturer gallery photographs**
on **2026-10-21**. The set includes both broad faces, an oblique pocket-face view,
and the true side. Original bytes are retained without cropping or transformation.
The [source manifest](2026-10-21-tension-block-evidence/sources.json) records
publisher, review date, URL, hash, retained path, and supported facts for each file.

| Image | Retained source | SHA-256 | Supports |
| --- | --- | --- | --- |
| I1 | [the-block-1.png](2026-10-21-tension-block-evidence/the-block-1.png) | `95a6bb983c69769cc7e823195147f0600449c30cbbe560dc2871b9ba5470cb12` | Logo face, near straight-on: separate 6 mm and 8 mm edge recesses, central cord and knot. |
| I2 | [the-block-2.png](2026-10-21-tension-block-evidence/the-block-2.png) | `497ee65904a77b3912ce88905233639d1951ca759376c5d0df4ac14712c604b2` | Pocket face, oblique: 20 mm and 10 mm edge recesses, mono and two-finger pocket, cord bridge, stepped side silhouette. |
| I3 | [the-block-3.png](2026-10-21-tension-block-evidence/the-block-3.png) | `109e77abecc20fb463125236164db7d10f3c72ee9a3fa19cb1dfbacc74e4c54c` | Pocket face, near straight-on: 10 mm/20 mm markings, mono and two-finger pocket, two visible cord mouths and bridge. |
| I4 | [the-block-4.png](2026-10-21-tension-block-evidence/the-block-4.png) | `06426e1a8d29eb9d6be7e5ddfe953ae2f7ef4b578670fdfe2c346af87efc1528` | True side: thickness profile and external cord loop/knot; side silhouette shows the lip step. |

The exact original URLs are:

- I1: https://cdn.shopify.com/s/files/1/0653/3706/5653/files/TheBlock1.png?v=1726542608
- I2: https://cdn.shopify.com/s/files/1/0653/3706/5653/files/TheBlock2.png?v=1726542608
- I3: https://cdn.shopify.com/s/files/1/0653/3706/5653/files/TheBlock3.png?v=1726542608
- I4: https://cdn.shopify.com/s/files/1/0653/3706/5653/files/TheBlock4.png?v=1726542608

The [current manufacturer product page](https://tensionclimbing.com/products/the-block-2)
and its [official product endpoint](https://tensionclimbing.com/products/the-block-2.js)
establish the name, maple construction, adjustable attachment point, nominal
contact depths, named pinch options, and the gallery's association with this
product. Selected factual fields from the endpoint's 2026-10-21 response are
retained in [manufacturer-product-facts.json](2026-10-21-tension-block-evidence/manufacturer-product-facts.json),
SHA-256 `196d16597c89fd12dcdd561bde75b7927904b8ed4e398d0a3b3ee3a469f33943`. This is an **extracted-facts record**, not
an unmodified source snapshot. It retains the source URL and raw response
SHA-256 `5dd334c1ad8c4b75fa4281889475840f9e57b59a7cdb1fead72953390cbc40ca` for provenance, while excluding
full descriptive prose, safety/marketing paragraphs, price and inventory.

## Official video evidence and revision limits

V1 is [Block Overview with Quinn Spadafora](https://www.youtube.com/watch?v=DTeHZ5-4Umk),
published by Tension Climbing and linked directly from its
[2025-09-08 overview page](https://tensionclimbing.com/blogs/training-tools/the-block-overview).
The pale maple body, six-recess layout and stepped side silhouette match approved
I2/I3. Its 3:13–3:39 demonstration moves the cord through the board and adjusts
exterior loops. The authoring represents that connection graph as five joined
spans: two back-face leads, two straight through-bore segments, and one exposed
front-face bridge. Retained full frames support the physical relationships:

- [V1 at 3:13](2026-10-21-tension-block-evidence/v1-193s.png): current pocket-face layout and initial cord position.
- [V1 at 3:21](2026-10-21-tension-block-evidence/v1-201s.png): cord being drawn through, with the stepped side visible.
- [V1 at 3:36](2026-10-21-tension-block-evidence/v1-216s.png): loops on both broad faces and the two straight front/back passage locations.

V2 is [The Block Overview from Tension Climbing](https://www.youtube.com/watch?v=xGoMPVtR0cI),
published by the manufacturer on 2021-01-29. It shows an **older cherry revision**.
Its front pocket/edge arrangement matches the approved current six-recess layout,
but it does not establish the current maple thickness, material, or dimensions.
Only its demonstrated finger/thumb relationship is used, corroborated against
I2/I3:

- [V2 at 0:47](2026-10-21-tension-block-evidence/v2-047s.png): fingers and thumb engage the two long front recesses in opposition across the central ridge.
- [V2 at 1:50](2026-10-21-tension-block-evidence/v2-110s.png): another angle of the same front pinch engagement.

These are uncropped decoded frames; their exact source URLs with timestamps,
publisher, review date, hashes and revision caveats are in the source manifest.
Video demonstrations support qualitative topology and contact relationships,
not factory metrology or training prescriptions. Only the relevant frames are
retained with this audit; full videos and transcripts are not catalog sources.

## Published facts and field mapping

| Field or physical feature | Supported value | Primary evidence |
| --- | --- | --- |
| Board name / manufacturer | The Block / Tension Climbing | Product page and retained extracted-facts record |
| Physical equipment | One portable block; its faces/orientations belong to one product | Product page; I1–I4 |
| Material | Maple | Product page and retained extracted-facts record |
| 20 mm edge | Edge; nominal depth 20 mm | Product page; engraved label in I2/I3 |
| 10 mm edge | Edge; nominal depth 10 mm | Product page; engraved label in I2/I3 |
| 8 mm edge | Edge; nominal depth 8 mm | Product page; engraved label in I1 |
| 6 mm edge | Edge; nominal depth 6 mm | Product page; engraved label in I1 |
| Two-finger pocket | Pocket; nominal depth 25 mm; `fingerCapacity: 2` | Product page; oblong pocket in I2/I3 |
| Mono pocket | Pocket; nominal depth 25 mm; `fingerCapacity: 1` | Product page; round pocket in I2/I3 |
| Narrow incut pinch | Named incut pinch; opposing inner long walls/rims of the 10 mm and 20 mm front recesses, shared with those edges | Current product name/classification; I2/I3; V2 at 0:47 and 1:50 with older-revision caveat |
| Wide flat pinch | Manufacturer names this pinch option and classifies it as flat | Product page and retained extracted-facts record |
| Micro flat pinch | Manufacturer names this pinch option and classifies it as flat | Product page and retained extracted-facts record |
| Adjustable attachment point | Product supports weights, resistance bands and free-hanging setups | Product page and retained extracted-facts record |

The four edge recesses and the two pockets are six distinct physical contacts.
The four edges are reviewed as practical four-finger contacts per hand:
**`fingerCapacity: 4` is an explicit visual estimate**, based on the complete long,
continuous recesses in I1–I3, reviewed 2026-10-21. It is not a published finger
count, a grip prescription, or a guarantee for every hand size. The pocket
capacities of 2 and 1 are published counts and remain distinct.

The manufacturer's names do not prescribe crimp, drag, or open-hand posture.
Do not derive training-plan instructions from these board facts. Optional
reciprocal pairing, extra grip classifications and pinch measurements need
their own support before inclusion.

Optional board-level and contact-level `handCapacity` are omitted. The official
videos demonstrate one-hand use, but do not establish the maximum number of
hands that can physically engage one Block. The app uses this field as a
capacity ceiling, so a one-hand demonstration is insufficient support for a
one-hand limit. This omission is separate from the required finger-capacity
estimates above.

## Physical contact mapping

The narrow incut pinch is the front central ridge used by opposing fingers and
thumb inside the 10 mm and 20 mm long recesses. This mapping is a physical
review inference from the V2 demonstration and the matching current front-face
layout in I2/I3; the current product page supplies the pinch's name and incut
classification. It does not import the older cherry board's dimensions.

`pinch-narrow-incut` reuses the two actual inner long-wall/rim regions already
owned by the corresponding 10 mm and 20 mm edge contacts. The native model's
two live binders carry `AdditionalContactIDs` for this shared physical contact.
They do not add coincident overlays or duplicate the board surface. The pinch
has **estimated `fingerCapacity: 4`**, reviewed 2026-10-21 from the complete
ridge span in I2/I3 and the demonstrated multiple-finger opposition in V2.
The video is not claimed to publish a four-finger count.

The manufacturer's **wide flat** and **micro flat** pinch labels remain genuine
product facts, but their distinct physical surfaces are not mapped by the
reviewed primary evidence. This audit assigns neither an invented highlight
region nor finger count to them. Nine named options are not evidence for nine
disjoint regions. Preserve the entire physical board geometry while omitting
unmapped selectable contact labels until a specific physical/source mapping is
established.

## Published dimensions and display estimates

Published contact depths are 20/10/8/6 mm for the edges and 25 mm for each
pocket. The current manufacturer page, extracted-facts record and revision statement
do not publish absolute overall dimensions, recess widths/lengths, corner or
lip radii, cord diameter, or cord length. Unsupported values remain absent from
factual board/contact measurements.

The native source uses these **operator-selected display estimates**, not
published measurements or image-derived metrology:

| Native display parameter | Estimated value |
| --- | --- |
| Overall envelope | X 150 mm × Z 112 mm × Y 44 mm |
| Broad face planes | Front Y = −22 mm; back Y = +22 mm |
| Stepped 10 mm side | Front plane moves to Y = −12 mm at X < −35 mm |
| Two straight front/back bores | X = −20/+20 mm, Z = 0, radius 4.5 mm |

The approved side and oblique images guide the qualitative relationships.
The maple revision's increased thickness is sourced; its exact 44 mm display
thickness is estimated. Old cherry listings, commerce summaries, AI-generated
specifications and third-party replicas supply no current maple measurements.
Cord and pose inputs are also **display estimates**:

| Authored suspension input | Estimated value or scope |
| --- | --- |
| Cord radius | 2.5 mm on all five spans |
| Back-face lead allowances | 220 mm per lead |
| Exposed front bridge allowance | 60 mm |
| Through-bore allowances | 50 mm per bore segment, over a 44 mm native channel |
| Canonical poses | Seven estimated rotations/cameras: four edges, two pockets and narrow incut pinch |
| Four edge poses and narrow incut pinch | World X display offset +80 mm |
| Back-face 8 mm and 6 mm edge poses | World Z display offset −140 mm, in addition to +80 mm world X |
| Pocket poses | No authored X/Z display offset |

These per-span rest-length allowances are solver inputs, not factory cord
measurements or a measured total cord length. The seven canonical poses relate
to the sourced contact inventory; their rotations, cameras and placement are
authored display choices.

Canonical `camera.viewDirection` is expressed in the **unposed model's space**
and rotates with the posed board. The front-face 20/10 mm edges, two pockets
and narrow incut pinch use `[0, -0.12, -1]` (model-space −Z). The back-face
6/8 mm edges use `[0, -0.12, 1]` (model-space +Z) to expose their actual rear
contact surfaces. These directions are display-camera choices tied to the
contact locations in approved I1–I3, not sourced product tilt measurements.

## Suspension connection graph and CAD mapping

The current product description establishes an adjustable attachment point.
I2/I3 show two pocket-face cord mouths and their **external bridge**; I1/I4 show
external cord, loop, knot/tails and the side. The current V1 demonstration at
3:13–3:39 draws the cord through the two front/back passages and changes the
exterior loop distribution. Together they support **two straight front/back
bores with adjustable exterior loops on both broad faces**, rather than a hidden
U-shaped passage connecting two mouths inside the wood.

The CAD source therefore retains two straight native voids. Their positions,
radius and precise factory sections are the display estimates above. There is
no invented interior lateral join or internal U-turn. A visible exterior bridge
remains exterior; the demonstrated connection graph is retained.

The authored `cadRoutedCord` suspension uses
`ropeSolver.method: "nativeRoutes"` and **five connected spans**:

| Strand ID | Physical connection |
| --- | --- |
| `left-lead` | Invisible display support to left back-face mouth |
| `left-bore` | Left back-face mouth to the matching front-face mouth through the straight CAD void |
| `front-bridge` | Exposed connection between the two front-face mouths |
| `right-bore` | Right front-face mouth to the matching back-face mouth through the straight CAD void |
| `right-lead` | Right back-face mouth to the invisible display support |

Incident spans share the exact same native CAD mouth-center coordinates at
all four board joins. The two bore segments explicitly retain continuity
through the wood; the front bridge stays exposed. This connection graph adds
no hidden lateral passage or U-turn and uses the existing schema.

`nativeRoutes` computes each span against the actual CAD solid under its own
rest-length allowance. The solver does **not** simulate continuous sliding of
one rope between spans or redistribute a measured total rope length. The
2.5 mm radius, 220 mm lead allowances, 60 mm bridge allowance, 50 mm bore
allowances and all seven canonical poses are the display estimates listed
above. The 80 mm world-X shift in the edge and pinch displays and the
additional −140 mm world-Z shift for the two back-face edges are pose-placement
estimates; they do not change the retained physical board geometry. Knot
geometry, hardware and full factory cord length are not claimed.

The [generic cord-path validator](../../Tools/HangboardPackages/src/hangboard_packages/cord_paths.py)
measures the continuous arc through unambiguous degree-two endpoint joins.
Its existing ordinary-bend neighborhood therefore continues across a split
between two strand records. Ambiguous junctions do not acquire an inferred
continuation. Cord radii, native-solid clearance and tube/topology rejection
outside that local continuous-arc neighborhood remain in force; no radius is
reduced to make the connected graph acceptable.

The native source retains authoring inputs rather than solved routes.
Generated clearance, routes and settled heights belong in the ignored
suspension artifact under the [cord authoring contract](../HANGBOARD_CORD_AUTHORING.md).

## Authored geometry review artifact

[Front, side and top geometry review](2026-10-21-tension-block-evidence/authored-geometry-review.png)
is an **authored Hang Ten review sheet**, shown to the user during this addition.
It places gray native-export previews beside the four complete approved
manufacturer images. It is not a manufacturer photograph, a dimensional source,
or evidence of runtime cord rendering. This is a new catalog addition with no
prior committed Tension Block geometry; the sheet labels that absence rather
than supplying invented prior views. The source manifest records its separate
artifact type, provenance, caveat and hash. Physical geometry is unchanged by
the suspension pose offsets above.

## Native app review artifacts

These representative native iOS app screenshots were independently visually
reviewed. They show the unselected board, front and rear edge highlighting,
the two-finger pocket in both orientations, the shared narrow-pinch rim/wall
highlights, and the visible cord spans. They are **runtime review artifacts**,
not manufacturer evidence or additional geometry sources:

- [Unselected board, portrait](2026-10-21-tension-block-evidence/app-normal-portrait.png).
- [20 mm front edge, portrait](2026-10-21-tension-block-evidence/app-edge-20-portrait.png).
- [6 mm rear edge, portrait](2026-10-21-tension-block-evidence/app-edge-6-portrait.png).
- [25 mm two-finger pocket, portrait](2026-10-21-tension-block-evidence/app-pocket-two-finger-25-portrait.png).
- [Narrow incut pinch, portrait](2026-10-21-tension-block-evidence/app-pinch-narrow-incut-portrait.png).
- [25 mm two-finger pocket, landscape](2026-10-21-tension-block-evidence/app-pocket-two-finger-25-landscape.png).

The source manifest binds these unchanged screenshots to native source SHA-256
`6ce0fc85d838ebacabced3d5d5a25ed4f5e41023c5f3261e9e89d9bfc271dfef`
and generated model SHA-256
`14ffd797a5e5422a5600a9fc28d17898f66e2eb4bab03ac600698a85c4deb725`.
The rear-edge capture exposes the rear contact and its two back-face leads;
the pinch capture shows both reused inner rims rather than adding a new
surface over the central body. These images establish the displayed states
only. Broader runtime validation and delivery records remain separate from
the source facts in this audit.
