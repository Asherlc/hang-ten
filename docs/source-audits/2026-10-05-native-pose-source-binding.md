# Nature Stone Hanger native bearing source binding

The reverse 6 mm bearing regression uses reviewed native face normals from
[the native bearing audit](../../Tools/HangboardPackages/tests/fixtures/nature-stone-hanger-bearing/display-bearing.json)
and [the independent contact-preservation check](../../Tools/HangboardPackages/tests/fixtures/nature-stone-hanger-bearing/contact-preservation.json).
The test continues to pin both evidence files, check preservation of all seven
wood contact surfaces, and verify upward bearing and rear-facing cameras.
Swapped rotations and reversed cameras must still fail those physical checks.

The contact-preservation check and its historical runtime validation refer to
the CAD source before metadata consolidation in commit `128860ade`. The
historical source was recovered from its Git LFS object and compared with the
consolidated `Hangboards/nature-stone-hanger.FCStd` source (`73b88efa…`):

| Source | SHA-256 |
| --- | --- |
| Historical CAD | `44a081979246f076853a3537bd0b79375c822c554507a7e0d1e04347a25cc9c9` |
| Consolidated CAD | `73b88efa8fb34b9f99a952cc0352bf97a91ac15033919a561d48a255ae83244b` |
| Explicit finger-capacity CAD (2026-10-06) | `8571d08d5101fc13e54745436277a499c3a79b13f7e6d60822b8617c450c38c5` |

The historical and consolidated FCStd archives contain the same 287 members.
Only `Document.xml` differs;
all other members, including every serialized BRep, are byte-for-byte equal.
The new document adds one top-level property, `HangTenSuspensionAuthoring`.
After removing that property and restoring the top-level property count, the
parsed XML trees have identical tags, attributes, non-whitespace text and
ordered children. All existing document properties, objects, placements,
links and contact mappings are therefore unchanged.

This comparison binds the retained normals to the consolidated source without
requiring a historical macOS export to match a Linux export byte for byte.
The regression pins the latest full CAD hash and requires the current
compiled suspension to match it. The current descriptor, suspension and USDZ
must also agree on the model hash. A source change requires updating this
evidence binding; an export with mismatched current files still fails.

The broader camera tests continue to inspect actual exported USD geometry, and
the native compiler tests retain coordinate-frame coverage. Hash agreement
alone does not verify those geometric relationships. This correction changes
no CAD geometry, poses, compiler behavior or runtime data.

The [2026-10-06 capacity audit](2026-10-06-finger-capacity.md) adds reviewed
counts to the eight previously unspecified contacts. Comparing that source
with the consolidated CAD above again gives the same 287 archive members;
every member except `Document.xml` is byte-identical. Removing only the
`HangTenBoardManifest` property from both parsed XML documents gives identical
trees. The manifests differ only in the added capacities. This binds the
retained bearing, contact-preservation and camera evidence to the new source;
the regression still checks the current suspension and model hashes and the
actual physical bearing and camera relationships.
