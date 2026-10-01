"""Argument guards for compare_exports.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent))
sys.path.insert(0, str(TESTS))

@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_chunk_must_be_a_positive_integer(value, capsys):
    compare_exports = pytest.importorskip("compare_exports")
    with pytest.raises(SystemExit) as raised:
        compare_exports.main(["a.usdz", "b.usdz", "--chunk", value])
    assert raised.value.code == 2
    assert "--chunk" in capsys.readouterr().err


def test_chunk_accepts_positive_values():
    compare_exports = pytest.importorskip("compare_exports")
    assert compare_exports.positive_int("1") == 1
    assert compare_exports.positive_int("2048") == 2048
