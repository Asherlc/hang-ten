# Split Palm hold-map evidence limits and direct-path review

Reviewed 2026-08-19 and remediated 2026-08-26. This audit records the limited
evidence used for the So iLL Split Palm package and the review constraints for
its canonical hold paths. It is not a manufacturer feature map. The committed
paths are deliberately operator-authored, directly editable package data.

## Evidence limits

| source | supported facts | limits |
| --- | --- | --- |
| [So iLL Split Palm product page](https://soillholds.com/products/split-palm) | Product identity, product dimensions, official gallery and lifestyle views, and category-level wording | No complete feature map, individual feature labels, depth, finger capacity, or grip posture |
| Official gallery and lifestyle views on that page | Visible surface boundaries, approximate bilateral symmetry, and candidate independently usable surfaces | Whether every visible surface is a separate intended hold or its intended use |
| Customer wording on that page: two slopers, a pinch, and multiple crimp sizes and angles | Category support for slopers, a pinch, and multiple edge/crimp surfaces | A mapping from those categories to a particular visible surface |

The package therefore retains product-level identity and dimensions from the
product page. Its 20 hold IDs and hold kinds are provisional visual inferences:
two slopers, one inferred pinch, and seven edge/crimp surfaces per side. It
omits unsupported depth, measurement, finger-capacity, grip-posture, and
feature-detail metadata. A later source that identifies individual features
supersedes these inferences.

## Canonical path review

`Hangboards/soill-split-palm/board.json` is the sole canonical geometry for
rendering, highlighting, hit testing, and editing. An operator deliberately
drew and reviewed one closed path for each hold against the official evidence;
the package contains 20 unique hold IDs, 20 geometry pieces, and 10 exact
left/right mirrored pairs. Paths remain independently editable so an evidence
update can revise one surface without changing another.

Review accepts the package only when all of these conditions hold:

- the product facts remain traceable to the sources above and every inference
  remains labeled provisional;
- each hold has one deliberate, closed canonical path representing its reviewed
  surface, without an unintended whole-piece target;
- visual review in Hangboard Workbench and the app shows distinct hold targets
  without unintended coverage of an adjacent reviewed surface;
- each justified mirrored pair is numerically exact, while uncertain asymmetry
  is not erased; and
- package validation passes and unsupported optional metadata remains omitted.

Changes to this hold map must begin with the primary manufacturer evidence,
then be made directly in the canonical paths and reviewed by an operator in
Workbench and the app. Keep review notes limited to what the evidence supports;
do not turn a provisional visual inference into a product claim.
