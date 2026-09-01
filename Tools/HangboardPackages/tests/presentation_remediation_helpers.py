from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


def manifest(
    *, package_ids: list[str], records: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "phase": "sourceReclassification",
        "reviewDate": "2026-08-30",
        "packageIDs": package_ids,
        "records": records,
        "phase1Checks": {
            name: {"status": "pending", "command": None}
            for name in (
                "manifestValidation",
                "packageValidation",
                "packageTestSuite",
                "hangboardsDiff",
            )
        },
    }


def record(
    boards: Path,
    package_slug: str,
    package_id: str,
    presentation_id: str,
    asset_path: str,
) -> dict[str, object]:
    data = (boards / package_slug / asset_path).read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    asset = f"{boards.name}/{package_slug}/{asset_path}"
    digest = hashlib.sha256(data).hexdigest()
    findings = {
        key: {
            "outcome": "conforms",
            "explanation": f"Cited evidence establishes {key}.",
        }
        for key in (
            "productLikeness",
            "material",
            "topology",
            "headOnPerspective",
            "smoothing",
            "framing",
            "crossCatalogConsistency",
        )
    }
    return {
        "packageID": package_id,
        "productName": "Fixture Board",
        "presentationID": presentation_id,
        "assetPath": asset,
        "workingSurface": "Published front working face",
        "physicalRevision": "Revision named by the cited first-party page",
        "manufacturer": "Fixture Maker",
        "materials": ["wood"],
        "formFactor": "fullWidthFixedBoard",
        "currentAsset": {
            "sha256": digest,
            "widthPixels": width,
            "heightPixels": height,
        },
        "decision": "keep",
        "findings": findings,
        "evidence": {
            "official": [
                {
                    "url": "https://manufacturer.example/fixture-board",
                    "publisher": "Fixture Maker",
                    "sourceKind": "officialProductPage",
                    "reviewedAt": "2026-08-30",
                    "revisionApplicability": "Exact named revision",
                    "imageRole": "Straight-on view establishes silhouette and contact layout.",
                    "supportedClaim": "The exact revision is a wood fixed board with the shown front working face.",
                }
            ],
            "independent": [
                {
                    "url": "https://retailer.example/fixture-board",
                    "publisher": "Independent Retailer",
                    "sourceKind": "retailer",
                    "reviewedAt": "2026-08-30",
                    "revisionApplicability": "Exact named revision",
                    "imageRole": "Real-world oblique product view corroborates finish and construction.",
                    "supportedClaim": "The production finish and component inventory match the official revision.",
                }
            ],
            "officialEvidenceGap": None,
            "independentEvidenceGap": None,
        },
        "comparator": {
            "assetPath": asset,
            "materialMatch": "Warm diffuse wood with bounded face-grain detail",
            "formFactorMatch": "Full-width fixed board",
            "reason": "Accepted cohort baseline; style-only: framing, lighting.",
            "baselineGap": None,
        },
        "generation": {
            "prompt": None,
            "sourceImages": [],
            "currentAssetRole": None,
            "candidates": [],
        },
        "final": {
            "acceptedAssetSHA256": digest,
            "finalDimensions": {"widthPixels": width, "heightPixels": height},
            "visualReviewerDecision": "acceptedCurrentAsset",
            "workbenchReview": {
                name: {"status": "pending", "evidence": None}
                for name in ("normal", "allActive", "individualHolds")
            },
            "validation": {
                name: {"status": "pending", "evidence": None}
                for name in (
                    "packageValidation",
                    "focusedTests",
                    "fullPackageSuite",
                    "buildForTesting",
                    "simulatorReview",
                )
            },
        },
    }


def write_manifest(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def empty_phase2_document() -> dict[str, object]:
    document = manifest(package_ids=[], records=[])
    document.update(
        schemaVersion=2,
        phase="assetRemediation",
        phase2={
            "canvasPreflight": {
                "status": "pending",
                "blockedReason": None,
                "classes": [],
            },
            "capabilityProbeCheck": {"artifacts": []},
            "batches": [],
            "finalChecks": {
                name: {"status": "pending", "evidence": None}
                for name in (
                    "crossCatalogReview",
                    "manifestValidation",
                    "finalInventory",
                    "packageTestSuite",
                    "buildForTesting",
                    "simulatorReview",
                    "contextCleanup",
                )
            },
        },
    )
    return document
