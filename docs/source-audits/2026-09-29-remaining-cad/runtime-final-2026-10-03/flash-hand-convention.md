# Flash #14 left/right convention

No contact-ID swap is present in the current descriptor. “Left” consistently means lower native/model X; “right” means higher X. These are stable contact identities, not a screen-side or hand prescription. The native source remains immutable.

| Contact pair | Native X, left / right (mm) | Descriptor nodes, left / right |
|---|---:|---|
| Three-well edges | 112 / 388 | `012` / `013` |
| Two-well edges | 127 / 373 | `014` / `015` |
| Small crimps | 164 / 336 | `009` / `010` |

Node suffixes above belong to `flash_board_body_…`; values come from the descriptor, not pixel measurement. The center edge remains X250 / node `011`.

Screen sides depend on pose and viewing direction. Using the stored quaternions, camera-to-board direction documented in `docs/HANGBOARD_CORD_AUTHORING.md:267`, and up `[0,1,0]`, intrinsic left projects as follows:

| Authored pose | Intrinsic left appears |
|---|---|
| three-edge-upright | screen-left |
| three-edge-inverted | screen-right |
| two-edge-upright | screen-right |
| two-edge-inverted | screen-left |

Whole-frame inspection confirms both cited captures light the viewer-right well. `14-live-hold-two-edge-left.png` is consistent with the opposite-face upright convention. `14-live-front.png` is consistent with the three-edge inverted convention. Neither capture receipt records the actual canonical pose ID; therefore this read-only check cannot certify which pose/runtime camera produced the three-edge frame. If it is independently shown to be the stored three-edge-upright pose with the documented world camera, the presentation needs investigation. The image alone does not establish a contact mapping defect.

There is **no source-backed native blocker**: retained manufacturer evidence does not prescribe these left/right names, and the source notes preserve all seven identities. Swapping immutable native contacts to match screen sides is not justified. The remaining limitation is a complete runtime explanation of the three-edge orientation; this report does not claim app or human acceptance.

Owned by `placid-badger`, agent `/root/flash_board_shape_review`. Only this report pair was created; no external resources were started. Exact input hashes, coordinates, poses and scope are in [flash-hand-convention.json](flash-hand-convention.json).
