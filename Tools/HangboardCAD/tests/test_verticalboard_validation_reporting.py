"""Exercise native validation reporting without requiring a CAD interpreter."""
import importlib.util
import sys
from types import ModuleType
from pathlib import Path

import pytest


@pytest.fixture
def reporting(monkeypatch):
    """Import actual reporting code with isolated, unused CAD dependency stubs."""
    monkeypatch.setenv("HANGTEN_CAD_PYTHONPATH", "")
    for name in ("FreeCAD", "Part"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    pxr = ModuleType("pxr")
    pxr.Usd = ModuleType("pxr.Usd")
    monkeypatch.setitem(sys.modules, "pxr", pxr)
    source = Path(__file__).with_name("verticalboards_native_source_checks.py")
    spec = importlib.util.spec_from_file_location("verticalboard_reporting_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_independent_failures_all_report_before_final_failure(reporting, capsys):
    check = reporting.check
    check("first depth", False, "expected 25, actual 24")
    check("other boundary", True)
    check("last depth", False, "expected 20, actual 18")
    with pytest.raises(AssertionError) as error:
        reporting.finish_checks()
    assert "first depth" in str(error.value)
    assert "last depth" in str(error.value)
    assert "PASS other boundary" in capsys.readouterr().out


def test_unsafe_prerequisite_stops_with_prior_failure_details(reporting):
    reporting.check("source metadata", False, "wrong")
    with pytest.raises(AssertionError) as error:
        reporting.check("one body", False, "missing", fatal=True)
    assert "source metadata" in str(error.value)
    assert "one body" in str(error.value)
