# Focused renderer review closure

The raw independent review and implementation review retain their original pre-fix/pending status. This note records the subsequently available parent-owned iOS results without rewriting those raw documents.

The nested path selector regression `testNestedSurfaceSelectorsPreserveAttachmentNeutralityAndInheritedWood` failed before the correction: [red summary](selector-red-summary.json), [command](selector-red-command.json), [raw log](selector-red.log). After sharing the existing name-first/relative-path-second lookup for material traversal within each instance, the same test passed: [green summary](selector-green-summary.json), [command](selector-green-command.json), [raw log](selector-green.log). The summaries show one failed test before and one passed test after, with no failures in the green run. This closes the concrete path-selector finding, including attachment neutrality, unnamed-child inheritance and restored wood selection.

The initial wood coverage/highlight/restoration and scene-isolation tests show two failures before adoption and two passes afterward: [red summary](ios-red-summary.json) and [green summary](ios-green-summary.json), with the exact commands and logs alongside them. The [tests-first snapshot](selector-fix/tests-first-snapshot.json), [implementation review](selector-fix/implementation-review.json) and [renderer adoption proof](renderer-adoption-proof.json) preserve the implementation identities and review scope.

These are focused implementation-stage proofs. They do not assert final native-package publication, complete final integration testing, app visual acceptance or human approval. This packet assembly performed no test run or simulator operation.
