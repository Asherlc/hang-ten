from __future__ import annotations

import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT = REPO_ROOT / "docs/source-audits/2026-09-20-j-bryant-ftg-32-3d.md"
SNAPSHOT_ROOT = REPO_ROOT / "docs/source-audits/2026-09-13-model-cord-snapshots"
SNAPSHOTS = {
    "j-bryant-ftg-32-01-suspended-pair-front.jpg": "f276704568bb877405617446e7527183ad81291df8e9231611487e52cadd533c",
    "j-bryant-ftg-32-02-material-oblique.jpg": "13e329556225441266c61d7ee4f0aea8bdb49129c02450cd2ae1756fce50adb7",
    "j-bryant-ftg-32-03-dimensions.png": "4551e29ccb0202d769ff6b7d4cf66e0308fb6cffe000059c0b6bafa313d7247c",
    "j-bryant-ftg-32-04-depth-guide.png": "119395ee56ab6f534558991c5167cd0d7f74578115b39b242ea1d293133e101c",
    "j-bryant-ftg-32-05-weight-loading.png": "d137c6538a7d13352899b7d7a3bc246b6c76586eba5259cd294a5efeb60e973c",
    "j-bryant-ftg-32-06-one-hand-loading.png": "61c9fb581ed214f2ae76d578147aabb63d894e6dd3f41ec5c2f2fb9abd05561f",
    "j-bryant-ftg-32-07-suspended-training.png": "3bd9cffa6952e7ad24c8ac57006e90cff81117fc22f3d59a35e8b9af144f5dd7",
}


def test_exact_user_gallery_snapshots_are_retained_byte_for_byte() -> None:
    assert AUDIT.is_file()
    audit = AUDIT.read_text(encoding="utf-8")
    for filename, expected_sha256 in SNAPSHOTS.items():
        path = SNAPSHOT_ROOT / filename
        assert path.is_file(), filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha256
        assert filename in audit
        assert expected_sha256 in audit


def test_source_audit_pins_mutable_commerce_evidence_and_estimate_boundary() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    for required in (
        "B0FZGY19T9",
        "FTG-32",
        "https://www.amazon.com/dp/B0FZGY19T9",
        "925b818fbfea32f4446d532151d0faa76c9d53a3ba3847f679081210fcc8aa54",
        "27b2689f3b79b63610d5d26f70693f78e2197aa5d1f7d610bda3c961d2b27874",
        "mutable",
        "displayEstimate",
        "105 × 77 × 37 mm",
        "16 mm",
        "25 mm",
        "145 mm and 260 mm are suspension heights, not rope lengths",
        "rear connecting segment is deliberately omitted",
        "No routines or training claims are added",
    ):
        assert required in audit
