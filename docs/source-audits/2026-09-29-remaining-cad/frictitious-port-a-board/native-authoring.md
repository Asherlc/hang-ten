# Port-A-Board — native CAD source audit

Published 128×140×48 mm; source seven edge depths 30/25/20/15/12/10/8, exterior jug and side pinch. Lower front cavity has asymmetric left angled/right rounded profile.

Body corner 24 mm, outer round 4 mm. Upper cavity 92×40 mm center z 32; reverse lower center z −36; symmetric lip rounds 2 mm. Deliberately drawn lower 30 mm asymmetric path uses lines/arcs, not pixel extraction. Front/rear well radius 5.5/depth 4 at x ±50, z 0. Unpublished widths, spacing, corners and mouths are display estimates.

Removed pocket-30-two-finger-mono, an unsupported duplicate semantic ID for the same 30 mm cavity. Retained edge-30 and all eight other actual contacts unchanged. Finger-placement capability does not create another physical contact. Existing saved snapshots remain historical; unknown exact targets fail closed under existing app contract.

The FCStd is the self-contained geometry and metadata authority: constrained Sketcher profiles, analytic Part extrusions/lofts, cuts/fusions/fillets, and native face SubShapeBinders. No imported facet solids, textures, materials, hardware, image tracing or geometry-generation scripts are retained. This is a display model; estimated dimensions are not manufacturing specifications. The schema label `native-parametric-measured-profile` identifies the supported native source type; these raster migrations did not measure an old display mesh.

Source authorization: the first six boards inherit September20 approval only for byte-identical retained primary visual sources. Refreshed HTML is separately authorized primary research and is explicitly distinguished in sources.json. YY exact packets were approved September29; additional primary search was expressly authorized by the user. No human CAD acceptance is implied.

[Visual comparison](review/index.html) includes every prior committed raster and current front/side/top/rear/oblique CAD view. There was no prior CAD side/top view. [Native cord evidence](native-cord-evidence.json) records known exposed routes and unknown hidden connections; source-visible topology governs and guessed hidden joins are omitted. Native cord solve reports and descriptor binding are recorded in validation.json. Human acceptance remains pending the requested one-at-a-time app review after the complete batch.

[Contact contract](contact-contract.json) compares retained logical fields to the frozen baseline. Native acceptance reopens/recomputes every source, verifies constrained sketches and valid actual body/contact surfaces, then changes a real dimension and checks both body and contact update without saving. Compile reports validate source SHA, descriptor/model pairing, contact inventory, exact supported grip depths, surface partition, and material-free output.

## Primary evidence

- [PA-1](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard) — Exact identity, marketed edge-depth language, jug/pinch uses, mounting/suspension context, and gallery provenance. Its wording alone does not establish a second physical 30 mm surface. SHA-256 `d0f031c2a16336226117f059a11487a0cb24b2b71a8f836a4d686d2f26ae8a68`.
- [PA-2](https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840) — Front 20, 25, and one continuous asymmetric 30 mm recess, center body/rim, and paired cord passages. SHA-256 `1509f81ed1dcf960a8ee1e91424e538de5aa890698b351a12fe2f1c36e4859e1`.
- [PA-3](https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840) — Reverse 15, 12, 8, and 10 mm recesses and continuity within one body. SHA-256 `38522abf6ccfa4a0f18dac57e5bbbf9a6290de4cd6a030756248f1a0314f70f4`.
- [PA-4](https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840) — Board thickness, rounded side profile, face relationship, and external cord path. SHA-256 `61221d7cb34edf3c5fd13e2300045050a0d7149424be9c5bcf8ded6c021df8e7`.
- [PA-5](https://frictitiousclimbing.com/cdn/shop/files/PAB-homewall-1.jpg?v=1784658897&width=3840) — Scale in hand, center ridge/30 mm region use, and paired lead-cord arrangement from both front passages. SHA-256 `a2cc5ec6e79272241c8f24891d91f89d075c3ebadc69b731d082a20775a43cd3`.

The [continuous cord certificate](cord-continuous-clearance.json) checks the exact rounded runtime routes, including fixed-support legs and final terminals, against the native collision solid using adaptive signed-distance bounds. Every route passes the explicit 0.01 mm numerical tolerance; reported values are conservative lower bounds, not sampled minima.

[Camera correction proof](camera-correction-proof.json) records local front/rear and inverted viewing directions. The correction changes camera metadata only; native assets, routes, heights and cord dimensions remain byte/value identical.
