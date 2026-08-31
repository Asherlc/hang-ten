from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import (
    write_board_package,
    write_multi_presentation_board_package,
    write_primary_only_draft,
)
from test_presentation_remediation_audit import _manifest, _record, _write_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "hangboard-packages.sh"


def _run_cli(
    *args: str,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = sys.executable
    environment.update(environment_overrides or {})
    return subprocess.run(
        [str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def _json_output(output: str) -> dict[str, object]:
    return json.loads(output[output.find("{") :])


def _write_audit_ledger(
    path: Path, *, hold_id: str = "hold-left", kind_outcome: str = "verified"
) -> Path:
    ledger = path / "metadata-ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "reviewedBoardIDs": ["fixture.board"],
                "sloperOnlyBoardIDs": [],
                "records": [
                    {
                        "boardID": "fixture.board",
                        "holdIDs": [hold_id],
                        "field": "kind",
                        "outcome": kind_outcome,
                        "reviewedAt": "2026-08-25",
                        "source": {
                            "kind": "manufacturer",
                            "url": "https://example.com/fixture-source",
                            "label": "Fixture manufacturer source",
                        },
                        "value": "jug",
                        **(
                            {"reason": "Fixture adapted role."}
                            if kind_outcome == "adapted"
                            else {}
                        ),
                    },
                    *[
                        {
                            "boardID": "fixture.board",
                            "holdIDs": [hold_id],
                            "field": field,
                            "outcome": "unavailable",
                            "reviewedAt": "2026-08-25",
                            "source": {
                                "kind": "manufacturer",
                                "url": "https://example.com/fixture-source",
                                "label": "Fixture manufacturer source",
                            },
                            "reason": "The manufacturer source does not establish this value.",
                        }
                        for field in (
                            "sizeMillimeters",
                            "depthRangeMillimeters",
                            "fingerCapacity",
                            "handCapacity",
                            "gripType",
                            "features",
                        )
                    ],
                    {
                        "boardID": "fixture.board",
                        "holdIDs": [hold_id],
                        "field": "sloper",
                        "outcome": "notApplicable",
                        "reviewedAt": "2026-08-25",
                        "source": {
                            "kind": "manufacturer",
                            "url": "https://example.com/fixture-source",
                            "label": "Fixture manufacturer source",
                        },
                        "reason": "The hold is not a sloper.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return ledger


def test_package_cli_reports_directly_discovered_boards_and_drafts(
    tmp_path: Path,
) -> None:
    write_board_package(tmp_path / "package-board", board_id="fixture.board")
    write_primary_only_draft(tmp_path / "draft-board")

    result = _run_cli("status", "--root", str(tmp_path))

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "boards": [{"id": "fixture.board", "path": "package-board"}],
        "drafts": ["draft-board"],
    }


def test_package_cli_final_inventory_rejects_drafts(tmp_path: Path) -> None:
    write_primary_only_draft(tmp_path / "draft-board")

    result = _run_cli(
        "validate",
        "--root",
        str(tmp_path),
        "--final-inventory",
    )

    assert result.returncode == 1
    assert "missing board.json" in result.stderr


def test_package_cli_audit_metadata_reports_coverage(tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    write_board_package(packages / "package-board", board_id="fixture.board")
    ledger = _write_audit_ledger(tmp_path)

    result = _run_cli(
        "audit-metadata", "--root", str(packages), "--ledger", str(ledger)
    )

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "reviewedBoardIDs": ["fixture.board"],
        "sloperOnlyBoardIDs": [],
        "fields": {
            "kind": {
                "populated": 1,
                "verified": 1,
                "adapted": 0,
                "unavailable": 0,
                "notApplicable": 0,
            },
            **{
                field: {
                    "populated": 0,
                    "verified": 0,
                    "adapted": 0,
                    "unavailable": 1,
                    "notApplicable": 0,
                }
                for field in (
                    "sizeMillimeters",
                    "depthRangeMillimeters",
                    "fingerCapacity",
                    "handCapacity",
                    "gripType",
                    "features",
                )
            },
            "sloper": {
                "populated": 0,
                "verified": 0,
                "adapted": 0,
                "unavailable": 0,
                "notApplicable": 1,
            },
        },
        "boards": [
            {
                "boardID": "fixture.board",
                "populated": 1,
                "verified": 1,
                "adapted": 0,
                "unavailable": 6,
                "notApplicable": 1,
                "unaccountedFields": 0,
            }
        ],
    }


def test_package_cli_audit_metadata_reports_nonzero_adapted_coverage(
    tmp_path: Path,
) -> None:
    packages = tmp_path / "packages"
    write_board_package(packages / "package-board", board_id="fixture.board")
    ledger = _write_audit_ledger(tmp_path, kind_outcome="adapted")

    result = _run_cli(
        "audit-metadata", "--root", str(packages), "--ledger", str(ledger)
    )

    assert result.returncode == 0, result.stderr
    report = _json_output(result.stdout)
    assert report["fields"]["kind"]["adapted"] == 1
    assert report["boards"] == [
        {
            "boardID": "fixture.board",
            "populated": 1,
            "verified": 0,
            "adapted": 1,
            "unavailable": 6,
            "notApplicable": 1,
            "unaccountedFields": 0,
        }
    ]


def test_package_cli_audit_metadata_rejects_unknown_hold(tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    write_board_package(packages / "package-board", board_id="fixture.board")
    ledger = _write_audit_ledger(tmp_path, hold_id="unknown-hold")

    result = _run_cli(
        "audit-metadata", "--root", str(packages), "--ledger", str(ledger)
    )

    assert result.returncode == 1
    assert result.stderr == "error: unknown hold ID: unknown-hold\n"


def test_package_cli_audit_presentations_reports_selected_lane(tmp_path: Path) -> None:
    boards = tmp_path / "Hangboards"
    write_multi_presentation_board_package(boards / "fixture-board")
    manifest = _write_manifest(
        tmp_path,
        _manifest(
            package_ids=["fixture.board"],
            records=[
                _record(
                    boards,
                    "fixture-board",
                    "fixture.board",
                    "front",
                    "assets/primary.png",
                ),
                _record(
                    boards, "fixture-board", "fixture.board", "back", "assets/back.png"
                ),
            ],
        ),
    )

    result = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--package-id",
        "fixture.board",
    )

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "decisions": {"keep": 2},
        "evidenceBlockedAssets": [],
        "packageCount": 1,
        "packageIDs": ["fixture.board"],
        "presentationCount": 2,
    }


def test_package_cli_audit_presentations_prints_domain_error_first_line(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "fixture-board")
    record = _record(
        boards, "fixture-board", "fixture.board", "primary", "assets/primary.png"
    )
    record["decision"] = "not-a-decision"
    manifest = _write_manifest(
        tmp_path, _manifest(package_ids=["fixture.board"], records=[record])
    )

    result = _run_cli(
        "audit-presentations", "--root", str(boards), "--manifest", str(manifest)
    )

    assert result.returncode == 1
    assert (
        result.stderr.splitlines()[0]
        == "error: records[0].decision must be one of ['edit', 'keep', 'regenerate', 'removeUnsupportedPresentation', 'splitPhysicalRevision']"
    )


def test_wrapper_rejects_python_3_11_3_before_validation(tmp_path: Path) -> None:
    package_root = tmp_path / "packages"
    write_board_package(package_root / "package-board", board_id="fixture.board")
    version_override = tmp_path / "python-version"
    version_override.mkdir()
    (version_override / "sitecustomize.py").write_text(
        "import sys\nsys.version_info = (3, 11, 3, 'final', 0)\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "status",
        "--root",
        str(package_root),
        environment_overrides={"PYTHONPATH": str(version_override)},
    )

    assert result.returncode == 69
    assert result.stderr == (
        "Hangboard package validation requires Python 3.11.4 or newer.\n"
    )


def _write_wrapper_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, dict[str, str]]:
    repository = tmp_path / "repository"
    script = repository / "scripts" / "hangboard-packages.sh"
    script.parent.mkdir(parents=True)
    script.write_bytes(SCRIPT_PATH.read_bytes())
    script.chmod(0o755)

    pyproject = repository / "Tools" / "HangboardPackages" / "pyproject.toml"
    pyproject.parent.mkdir(parents=True)
    pyproject.write_text("[project]\nname = 'fixture'\n", encoding="utf-8")

    environment_bin = repository / ".context" / "hangboard-packages-venv" / "bin"
    environment_bin.mkdir(parents=True)
    python = environment_bin / "python"
    python.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = '-m' ] && [ \"$2\" = 'pip' ]; then\n"
        '  printf \'%s\\n\' "$*" >> "$FAKE_PIP_LOG"\n'
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    entry_point = environment_bin / "hangboard-packages"
    entry_point.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    entry_point.chmod(0o755)
    pip_log = tmp_path / "pip.log"
    environment = {
        **os.environ,
        "FAKE_PIP_LOG": str(pip_log),
        "HANGBOARD_PYTHON": str(python),
    }
    return script, pyproject, entry_point, pip_log, environment


def test_wrapper_reinstalls_when_pyproject_is_newer_than_entry_point(
    tmp_path: Path,
) -> None:
    script, _, entry_point, pip_log, environment = _write_wrapper_fixture(tmp_path)
    os.utime(entry_point, (1, 1))

    result = subprocess.run(
        [str(script), "status"],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert "-m pip install --disable-pip-version-check -e" in pip_log.read_text(
        encoding="utf-8"
    )


def test_wrapper_keeps_install_when_pyproject_is_not_newer_than_entry_point(
    tmp_path: Path,
) -> None:
    script, pyproject, entry_point, pip_log, environment = _write_wrapper_fixture(
        tmp_path
    )
    os.utime(pyproject, ns=(entry_point.stat().st_mtime_ns,) * 2)

    result = subprocess.run(
        [str(script), "status"],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert not pip_log.exists()
