# Static hand-image prototype: technical pass, visual failure

The corrected static image path completed its technical checks, but **failed visual equivalence**: the generated pair is vertically inverted relative to the live reference, and the hands are substantially darker, especially the left. Selected fingers remain visibly red. Root inspected the three whole final images: live app view, image app view, and generated hand PNG. No workout sequence, color-workflow success, production repair, or human acceptance is established.

## Preserved sequence

The initial live reference passed its helper and root whole-image review on binary `8f5e60e00100deaf70bbafc25e54e04f5a1221db6942762e40a0b9d5e52aab2a`. Its paired image attempt failed with `invalidViewport` before scene construction/render submission; it produced no hand PNG or app screenshot. That trace lacked viewport dimensions, so its specific cause remains unproved.

The v3 viewport-readiness correction was applied and built as binary `f6c9dd2cc35c65a07f3c9a04883cfcb38b8ea4c138276a3137e21961e41dcd30`. The fresh live-b/image-b technical gates passed. The later trial recorded an initial 120×0-point viewport, then 370×462.333-point viewport at scale 3; the initial request was consumed without scene construction and revision 2 completed. Those measurements belong to the later trial and do not retroactively prove the initial failure's cause.

At publication the image arm had no live hand make or public ARView observed. This is a bounded technical observation, not proof of GPU inactivity. No obvious clipping was found in the inspected views, but the cream background alone cannot establish all transparency cases. Retained PNG metadata records 8-bit components, alpha info 1, and sRGB; it does not repair the visible inversion or darkness. Coordinates/lighting research is separate and no subsequent patch or trial outcome is included.

See the [whole-image index](index.md). The final findings retain root's exact three-image review; earlier live-a root review remains separate. All images are original bytes, without cropping or processing.

## Evidence and ownership

The original 52-file initial freeze and 63-file final freeze remain exact and retain their original manifests. The packet also includes the separately authorized initial findings, rejected v1 and applied v2/v3 source/patch history, helper v1–v6 corrections and reviews, both build/install/parity records, frozen applied source snapshots, raw failures, and app cleanup records. No app bundle or DerivedData is copied. `retention-manifest.json` maps each source to its retained path; `retained-files.sha256.json` hashes every packet file except itself.

Trial app cleanup is recorded per arm. The root controller retains the existing Simulator and DerivedData; this packet claims no broader cleanup. Native assets remain unchanged in the retained package checks. Prior packets and acceptance records are untouched. Raw log/patch whitespace is preserved; only this README and the image index receive editorial whitespace checks.
