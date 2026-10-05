# Nature Stone Hanger native bearing source binding

The reverse 6 mm bearing regression uses reviewed native face normals from
[the native bearing audit](2026-09-29-remaining-cad/nature-stone-hanger/display-and-pose-review/raw/fresh-native-bearing/new-native-bearing.json)
and [the independent contact-preservation check](2026-09-29-remaining-cad/nature-stone-hanger/granite-seat-review/independent-native-check.json).
The test continues to pin both evidence files, check preservation of all seven
wood contact surfaces, and verify upward bearing and rear-facing cameras.
Swapped rotations and reversed cameras must still fail those physical checks.

The contact-preservation check and its historical runtime validation refer to
the CAD source before metadata consolidation in commit `128860ade`. The
historical source was recovered from its Git LFS object and compared with the
current `Hangboards/nature-stone-hanger.FCStd`:

| Source | SHA-256 |
| --- | --- |
| Historical CAD | `44a081979246f076853a3537bd0b79375c822c554507a7e0d1e04347a25cc9c9` |
| Consolidated CAD | `73b88efa8fb34b9f99a952cc0352bf97a91ac15033919a561d48a255ae83244b` |

Both FCStd archives contain the same 287 members. Only `Document.xml` differs;
all other members, including every serialized BRep, are byte-for-byte equal.
The new document adds one top-level property, `HangTenSuspensionAuthoring`.
After removing that property and restoring the top-level property count, the
parsed XML trees have identical tags, attributes, non-whitespace text and
ordered children. All existing document properties, objects, placements,
links and contact mappings are therefore unchanged.

This comparison binds the retained normals to the consolidated source without
requiring a historical macOS export to match a Linux export byte for byte.
The regression pins the full consolidated CAD hash and requires the current
compiled suspension to match it. The current descriptor, suspension and USDZ
must also agree on the model hash. A source change requires updating this
evidence binding; an export with mismatched current files still fails.

The broader camera tests continue to inspect actual exported USD geometry, and
the native compiler tests retain coordinate-frame coverage. Hash agreement
alone does not verify those geometric relationships. This correction changes
no CAD geometry, poses, compiler behavior or runtime data.
