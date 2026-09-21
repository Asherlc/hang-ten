"""Closed document-only checks for Batch 04 source retention and rulings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = REPO_ROOT / "docs/source-audits"
IMPORT_ROOT = AUDIT_ROOT / "2026-09-20-hangboards-batch-04-model-imports"
EVIDENCE_ROOT = IMPORT_ROOT / "evidence"
SOURCE_REGISTER = AUDIT_ROOT / "2026-09-20-batch-04-3d-source-register.json"
SOURCE_CONTACT_AUDIT = AUDIT_ROOT / "2026-09-20-batch-04-source-to-contact-audit.md"

EXPECTED_APPROVED_SHA256 = {
    "crimptonite-helium-mobile/Helium--mobile-hangboard-by-Crimptonite_06.jpg": "9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40",
    "crimptonite-helium-mobile/182984fc8f-Helium--mobile-hangboard-by-Crimptonite_08.jpg": "5d5c18d45ae6d30e6e951aa158a30b303d42d4583d18d4a6d82075ff5de50f6a",
    "metolius-light-rail-2-0/Light-Rail-2-PT.jpg": "7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272",
    "metolius-light-rail-2-0/metolius-light-rail-1.jpg": "93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a",
    "metolius-rock-rings-3d/Rock-Rings-black-white.jpg": "d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c",
    "metolius-rock-rings-3d/xaEAAOSwFtFmDzoB.webp": "b510bd192bb6fe54c6e4dcfa98c9d684a2db7582cbfd3682cebb6e031494a8f0",
    "metolius-rock-rings-3d/KQkAAOSwjmJmDzoE.webp": "df263e67395aa17a2f4df263ca74e4cbbfb7bfcf9c75e0dfa611d352ad3d3cba",
    "owl-climb-poker/61cd4a213f-owlclimb_poker19_0.jpg": "4bae58b408b3f3a82c524b1101079eafa01cd062c398cb203d4803fce9850eab",
    "owl-climb-poker/d8dc16e362-owlclimb_poker19_1.jpg": "0c1d54cb2bc4d8e7fa285f3053b927d7c1a1b3fbafdf0b5d7aface9c82d0dbad",
    "owl-climb-poker/3231a07015-owlclimb_poker19_2.jpg": "5fbff79f31db8e85d078a74eb629abd069fc276ac128b3d85a84fc15ad9f1c4e",
    "owl-climb-poker/340a73e020-owlclimb_poker19_3.jpg": "ae39598fbf75c0e4e4dfbb599c724ff1e2531ef12ecca84b3504805e7bc3af13",
    "yy-vertical-penta-evo/14b413b6dd-yy-vertical-agres-nomades-penta-evo-3.webp": "83b95adc297d634659654f6f27bb43ebae1c53b171b747568ac5e022754e6571",
    "yy-vertical-penta-evo/9957e0d26b-yy-vertical-agres-nomades-penta-evo-6.webp": "1107039ef6d2877cd68a293683c72ec93f3166633199d45484f58c13b48aa2fc",
    "trango-rock-prodigy-pivot/22840-501_RockProdigyPivotGrey_MainImage.jpg": "339f743c7e5fff0b0619314cf6781d8f602c1545975390f4ab4424aa7461bf5d",
    "trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage4_DualBoard.jpg": "e05deb5c0ea6d3361122926d7b3efee6b72bb9aad0a75fc09663bf599731e3e4",
    "trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg": "7aa2556dec24293e62c2be110fa7dfb6bcf118333ff35693e455a8a7babc67f7",
    "trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage2_CloseUp.jpg": "26cf8d599a1a08bbcbbf688e14c9806d5f2381dc2aecdb608998ab22cee2c1b3",
}

EXPECTED_SOURCE_DOCUMENT_SHA256 = {
    "crimptonite-helium-mobile/media-manifest.json": "2841b57cb5343d91fa2a66329fe3bbc845b869de160f3055cd3b430398294f91",
    "crimptonite-helium-mobile/source-register.json": "c4619bbb7ca8012356c3e3ec5512716456223923e32ddba5612227e2ad1c855b",
    "metolius-light-rail-2-0/media-manifest.json": "c870c458cf99db377c8f605b98ef018b746261917e3ef243373f6b6c434fc0ac",
    "metolius-light-rail-2-0/source-register.json": "2b57d65fbc4e314cc7bcf94edfd0575586b88b468418f09bb1890d65f0383907",
    "metolius-rock-rings-3d/media-manifest.json": "f895e826496054a55cb2f0f0dde7dd7dd4f2bb31bd60051d192647b657d1a195",
    "metolius-rock-rings-3d/source-register.json": "c69be609ed85dafb880f53a61e73086b628393ab5cc13f3681baa85eae8a6050",
    "owl-climb-poker/media-manifest.json": "e8a7d2468b51e252c6c64f89b59ddbaced8938559ed22ef3942159c8e7d89c40",
    "owl-climb-poker/source-register.json": "b1befaeb5ef5c62ce8031c8213f8efd5414d97f950e2d285dc59b8f11ac767a0",
    "trango-rock-prodigy-pivot/media-manifest.json": "0d2357684eb79b71776203d230b5b1d883caa4befa1820d3d03ca805694c5991",
    "trango-rock-prodigy-pivot/source-register.json": "1adbbe777d377cf1a8f35538b7f9c1b47cbf7e7bedfb7d155c737ab825e65754",
    "yy-vertical-penta-evo/media-manifest.json": "ce4b9290f251afcbdeb106b1b342c2af735508c5b4c079045f970975000f9d4d",
    "yy-vertical-penta-evo/source-register.json": "a43ad34a360a95ed71a6e82db6523a2f9f000549a1486e981a150956d9ce58cd",
}

EXPECTED_SOURCE_DELIVERY_SHA256 = {
    "crimptonite-helium-mobile.glb": "afae2ca4bff5a42af68820682a68a49e1235d4c5332759f9df461475424ab2a6",
    "metolius-light-rail-2-0.glb": "dbd8c47af8d9b1a7f36fc0f8634e4c6afda484d97988729570b685adf7cbb99e",
    "metolius-rock-rings-3d.glb": "f282fa3db0a41eea2a8e892873ae6273ef3b46c66d9c42639ed106038be721db",
    "owl-climb-poker.glb": "7e56200618987e5c35efbc9902aa214414fa999e6b529e6baf627075aa381e12",
    "yy-vertical-penta-evo.glb": "0968a2b6946b5a76a729033f069aa3a080bd17b625d894a349b0c5484bb99efc",
    "trango-rock-prodigy-pivot-rejected.glb": "0c342998ced0a3fa99172ff08adf1d605933405df5520ec0833db23d5c2edda8",
}

PIVOT_PATCH_MAPPINGS = {
    "wing crest": "outer-wedge-pinch", "wing inner": "outer-wedge-pinch",
    "rail lower": "variable-edge", "rail upper": "variable-edge",
    "rail-end outer": "variable-edge", "rail-end inner": "variable-edge",
    "supported lower": "medium-crimp", "supported upper": "large-crimp",
    "two-finger top": "two-finger-pocket", "two-finger side": "two-finger-pocket",
    "three-finger top": "three-finger-pocket", "top sloped": "upper-sloped-crimp",
    "side sloped": "outer-sloped-crimp", "lower-wave sloper": "lower-sloper",
}

PIVOT_DELIVERED_SUFFIXES = {
    "wing crest": "wing-crest", "wing inner": "wing-inner",
    "rail lower": "rail-lower", "rail upper": "rail-upper",
    "rail-end outer": "rail-end-outer", "rail-end inner": "rail-end-inner",
    "supported lower": "supported-lower", "supported upper": "supported-upper",
    "two-finger top": "twofinger-top", "two-finger side": "twofinger-side",
    "three-finger top": "threefinger-top", "top sloped": "top-sloped-crimp",
    "side sloped": "side-sloped-crimp", "lower-wave sloper": "lower-wave-sloper",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_pivot_retired_ids() -> dict[str, str]:
    contacts = (
        "large-crimp", "lower-sloper", "medium-crimp", "outer-sloped-crimp",
        "outer-wedge-pinch", "three-finger-pocket", "two-finger-pocket",
        "upper-sloped-crimp", "variable-edge",
    )
    return {
        f"{contact}-{side}{suffix}": f"{contact}-{side}"
        for contact in contacts
        for side in ("left", "right")
        for suffix in ("", "-orientation-2", "-orientation-3", "-orientation-4")
    }


def test_batch04_source_register_and_pivot_mapping_are_closed() -> None:
    register = json.loads(SOURCE_REGISTER.read_text())
    assert register["schemaVersion"] == 1
    assert set(register["boards"]) == {
        "crimptonite.helium-mobile", "metolius.light-rail-2",
        "metolius.rock-rings-3d", "owl-climb.poker", "yy.penta-evo",
        "trango.rock-prodigy-pivot",
    }
    audit = SOURCE_CONTACT_AUDIT.read_text()
    assert audit.startswith("# Batch 04 Source-to-Contact Audit")
    assert "| Pivot source patch | Slot | Left contact | Right contact |" in audit
    pivot = register["boards"]["trango.rock-prodigy-pivot"]
    assert pivot["pivotPatchMappings"] == PIVOT_PATCH_MAPPINGS
    assert pivot["selectablePositions"] == ["p1", "p2", "p3", "p5"]
    assert pivot["transitionOnlyPositions"] == ["p4"]
    assert pivot["retiredPresentationIDToContactID"] == _expected_pivot_retired_ids()
    delivered = pivot["pivotPatchMappingsByDeliveredID"]
    assert set(delivered) == {
        f"pv-{side}-{suffix}"
        for side in ("L", "R")
        for suffix in PIVOT_DELIVERED_SUFFIXES.values()
    }
    for patch, suffix in PIVOT_DELIVERED_SUFFIXES.items():
        assert delivered[f"pv-L-{suffix}"] == PIVOT_PATCH_MAPPINGS[patch]
        assert delivered[f"pv-R-{suffix}"] == PIVOT_PATCH_MAPPINGS[patch]


def test_batch04_register_closes_contact_merges_faces_and_cord_rulings() -> None:
    boards = json.loads(SOURCE_REGISTER.read_text())["boards"]
    assert boards["crimptonite.helium-mobile"]["sourceToContact"] == {
        "front lip 14": "edge-14", "reverse lip 14": "edge-14",
        "front lip 22": "edge-22", "reverse lip 22": "edge-22",
        "centre 10": "center-edge-10", "centre 18": "center-edge-18",
        "top jug": "top-jug", "rear jug/sloper": "back-jug-sloper",
    }
    assert boards["owl-climb.poker"]["faceMappings"] == {
        "photo 0": "face-a", "photo 1": "face-b", "photo 2": "face-c", "photo 3": "face-d",
    }
    assert boards["owl-climb.poker"]["restoredContacts"] == [
        "face-d-left-deep-rounded-recess", "face-d-right-deep-rounded-recess",
    ]
    assert boards["metolius.rock-rings-3d"]["slotMappings"] == {
        "jug": ["jug-left", "jug-right"],
        "pocket-40": ["pocket-40-four-left", "pocket-40-four-right"],
        "pocket-32": ["pocket-32-three-left", "pocket-32-three-right"],
        "pocket-25": ["pocket-25-two-left", "pocket-25-two-right"],
    }
    assert boards["yy.penta-evo"]["slotMappings"] == {
        slot: [f"{slot}-left", f"{slot}-right"]
        for slot in ("edge-25", "edge-20", "edge-15", "edge-10", "mono", "duo", "tray")
    }
    assert {package: record["ruling"] for package, record in boards.items()} == {
        "crimptonite.helium-mobile": "pairedLeadCord exterior leads only; no inferred interior route or twoBranchCord.",
        "metolius.light-rail-2": "pairedLeadCord upper-entry exterior leads only; no underside mouth or hidden vertical bore.",
        "metolius.rock-rings-3d": "two independent pairedLeadCord systems; no inter-unit connection or central through-bore.",
        "owl-climb.poker": "noDocumentedSuspension; excluded.",
        "yy.penta-evo": "two independent paired exterior loops through the existing central ring; no invented channel or knot.",
        "trango.rock-prodigy-pivot": "noDocumentedSuspension; pulley-kit ropes are not Pivot suspension.",
    }


def test_batch04_retains_every_approved_hashed_byte() -> None:
    for relative_path, expected_sha256 in EXPECTED_APPROVED_SHA256.items():
        retained = EVIDENCE_ROOT / relative_path
        assert retained.is_file(), retained
        assert _sha256(retained) == expected_sha256


def test_batch04_copied_source_documents_are_present_and_parseable() -> None:
    for slug in (
        "crimptonite-helium-mobile", "metolius-light-rail-2-0", "metolius-rock-rings-3d",
        "owl-climb-poker", "yy-vertical-penta-evo", "trango-rock-prodigy-pivot",
    ):
        for filename in ("source-register.json", "media-manifest.json"):
            retained = EVIDENCE_ROOT / slug / filename
            assert retained.is_file(), retained
            json.loads(retained.read_text())
            assert _sha256(retained) == EXPECTED_SOURCE_DOCUMENT_SHA256[f"{slug}/{filename}"]


def test_batch04_retained_source_delivery_glbs_match_batch_checksums() -> None:
    batch_checksums = json.loads((IMPORT_ROOT / "batch-checksums.json").read_text())
    retained_to_original = {
        "crimptonite-helium-mobile.glb": "models/crimptonite-helium-mobile/crimptonite-helium-mobile.glb",
        "metolius-light-rail-2-0.glb": "models/metolius-light-rail-2-0/metolius-light-rail-2-0.glb",
        "metolius-rock-rings-3d.glb": "models/metolius-rock-rings-3d/metolius-rock-rings-3d.glb",
        "owl-climb-poker.glb": "models/owl-climb-poker/owl-climb-poker.glb",
        "yy-vertical-penta-evo.glb": "models/yy-vertical-penta-evo/yy-vertical-penta-evo.glb",
        "trango-rock-prodigy-pivot-rejected.glb": "models/trango-rock-prodigy-pivot/trango-rock-prodigy-pivot.glb",
    }
    for retained_name, original_path in retained_to_original.items():
        retained = IMPORT_ROOT / "source-delivery" / retained_name
        assert retained.is_file(), retained
        assert _sha256(retained) == EXPECTED_SOURCE_DELIVERY_SHA256[retained_name]
        assert _sha256(retained) == batch_checksums[original_path]


def test_batch04_register_records_exact_evidence_status_and_supersession() -> None:
    register = json.loads(SOURCE_REGISTER.read_text())
    light_rail = register["boards"]["metolius.light-rail-2"]
    treeline = next(item for item in light_rail["evidence"] if item["retainedPath"].endswith("metolius-light-rail-1.jpg"))
    assert treeline["sha256"] == EXPECTED_APPROVED_SHA256["metolius-light-rail-2-0/metolius-light-rail-1.jpg"]
    assert treeline["replayURL"] == "https://web.archive.org/web/20260129012402id_/https://images.squarespace-cdn.com/content/v1/5b4544e485ede17941bc95fc/452f6e96-37f1-454d-a405-e801658501a5/metolius-light-rail-1.jpg"
    assert treeline["replayedAt"] == "2026-01-29T01:24:02Z"
    assert treeline["changedLiveSHA256"] == "7d06ec5f74917b909b031ac72067944f8cf72b14481aa0e31eafc272600c0aea"
    assert treeline["status"] == "replayedExactBytes"
    penta = register["boards"]["yy.penta-evo"]
    assert all(item["binaryURL"] is None and item["status"] == "unhashed" for item in penta["evidence"])


def test_batch04_supersedes_historical_audits_without_opening_the_cord_manifest() -> None:
    cord_audit = (AUDIT_ROOT / "2026-09-13-model-hangboard-cord-audit.md").read_text()
    assert "Unpromoted Batch 04 packages remain outside this closed machine-readable" in cord_audit
    assert "pulley-kit ropes are not Pivot suspension" in cord_audit
    orientation_audit = (AUDIT_ROOT / "2026-09-11-3d-board-orientation-audit.md").read_text()
    assert "retain only selectable `p1`,\n`p2`, `p3`, and `p5`" in orientation_audit
    assert "`p4` is manufacturer Orientation 3 Switch transition" in orientation_audit
    remediation = json.loads(
        (AUDIT_ROOT / "2026-08-30-hangboard-presentation-remediation-manifest.json").read_text()
    )
    assert remediation["schemaVersion"] == 2
    assert {
        "crimptonite.helium-mobile", "metolius.light-rail-2", "metolius.rock-rings-3d",
        "owl-climb.poker", "yy.penta-evo", "trango.rock-prodigy-pivot",
    } <= set(remediation["packageIDs"])
