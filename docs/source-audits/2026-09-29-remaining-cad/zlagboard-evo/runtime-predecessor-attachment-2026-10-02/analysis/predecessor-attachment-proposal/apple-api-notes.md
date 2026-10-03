# Apple API check

Read through web search on 2026-10-02; paraphrases only. This is API context, not evidence that detachment will repair the observed failure.

- [Entity scene](https://developer.apple.com/documentation/realitykit/entity/scene): scene membership follows the entity hierarchy; nil indicates no current scene attachment.
- [HasHierarchy removeFromParent](https://developer.apple.com/documentation/realitykit/hashierarchy/removefromparent(preservingworldtransform:)): removes an entity from its parent, and can remove a root from its scene. Apple distinguishes this from setting a root's parent to nil, which does not remove that root. Default behavior preserves the relative transform.
- [RealityViewContentProtocol remove](https://developer.apple.com/documentation/realitykit/realityviewcontentprotocol/remove(_:)): removes the specified entity from that content when present.

These contracts do not prove rendering or presentation, nor authorize removing entities owned by a different host. Actual attachment and ownership observations remain required before a diagnostic detach is selected. No production change follows from this documentation check.
