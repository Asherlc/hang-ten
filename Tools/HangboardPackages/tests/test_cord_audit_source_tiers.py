from __future__ import annotations

import pytest

from hangboard_packages.cord_audit import CordAuditError, _source_tier


def test_source_tier_accepts_exact_independent_value() -> None:
    assert _source_tier("independent", "evidence.sourceTier") == "independent"


def test_source_tier_rejects_nearby_unknown_value() -> None:
    with pytest.raises(CordAuditError, match="must be one of"):
        _source_tier("independent-field", "evidence.sourceTier")
