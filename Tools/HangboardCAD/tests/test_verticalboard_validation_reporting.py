"""Exercise native validation reporting without requiring a CAD interpreter."""
import ast
from pathlib import Path

import pytest


def reporting_functions():
    source = Path(__file__).with_name("verticalboards_native_source_checks.py")
    tree = ast.parse(source.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"check", "finish_checks"}]
    namespace = {"FAILURES": []}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    return namespace


def test_independent_failures_all_report_before_final_failure(capsys):
    reporting = reporting_functions()
    check = reporting["check"]
    check("first depth", False, "expected 25, actual 24")
    check("other boundary", True)
    check("last depth", False, "expected 20, actual 18")
    with pytest.raises(AssertionError) as error:
        reporting["finish_checks"]()
    assert "first depth" in str(error.value)
    assert "last depth" in str(error.value)
    assert "PASS other boundary" in capsys.readouterr().out


def test_unsafe_prerequisite_stops_with_prior_failure_details():
    reporting = reporting_functions()
    reporting["check"]("source metadata", False, "wrong")
    with pytest.raises(AssertionError) as error:
        reporting["check"]("one body", False, "missing", fatal=True)
    assert "source metadata" in str(error.value)
    assert "one body" in str(error.value)
