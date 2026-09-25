"""Argument guards for verify_reproducible.py and compare_exports.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent))
sys.path.insert(0, str(TESTS))

import verify_reproducible  # noqa: E402

REPOSITORY = verify_reproducible.REPOSITORY


def test_keep_rebuild_onto_committed_assets_is_rejected_before_any_build(
    monkeypatch, tmp_path, capsys
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("no build may start when the keep destination is unsafe")

    monkeypatch.setattr(verify_reproducible, "compile_into", forbidden)
    monkeypatch.chdir(REPOSITORY)
    with pytest.raises(SystemExit) as raised:
        verify_reproducible.main(
            [
                "--package", "lattice-triple-rung",
                "--keep-rebuild", "Hangboards",
                "--freecad", str(tmp_path / "missing-freecad"),
            ]
        )
    assert raised.value.code == 2
    assert "would overwrite" in capsys.readouterr().err


def test_keep_rebuild_through_a_symlink_alias_is_rejected(tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(REPOSITORY / "Hangboards")
    conflicts = verify_reproducible.keep_conflicts(alias, "lattice-triple-rung")
    assert len(conflicts) == 2


def test_keep_rebuild_elsewhere_is_allowed(tmp_path):
    assert verify_reproducible.keep_conflicts(tmp_path / "out", "lattice-triple-rung") == []


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
