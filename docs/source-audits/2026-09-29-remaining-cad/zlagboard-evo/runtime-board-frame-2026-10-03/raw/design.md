# Board frame renderer candidate

The goal is correct neutral/active/preview board frames throughout the real workout, with native CAD, finish metadata, authored contact coverage, cord geometry, perspective framing, orbit and zoom preserved. Existing evidence shows correct CPU mutations coexisting with stale presented RealityView frames.

This bounded candidate opts the two workout BoardMap callsites into explicit RealityRenderer frames. It reuses the loaded BoardModelRealityScene and all its material/pose/framing logic. Rendering occurs only for semantic, viewport or gesture changes. One in-flight render serializes scene mutation; a revision owns its result and stale completions cannot publish. No timer drives redraw. Existing live picking remains for interactive maps. Runtime images are generated from native entities and never added to model packages.

First compare live and candidate in one binary on a fresh owned Simulator, with real hands, ordinary navigation, muted audio, natural7/180/7 timing and passive whole screenshots. Missing/stale frames fail. If the candidate passes, validate Pro plus interaction, clearing, latest-request ownership and clean production configuration before adoption. A constant white analytic environment is a declared display-lighting adaptation requiring visual assessment.
