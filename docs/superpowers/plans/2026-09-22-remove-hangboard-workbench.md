# Remove Hangboard Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Hangboard Workbench tool, its build/CI/release/hosting, its Workbench-named audit metadata, and all live references, while preserving the shared geometry code that `HangboardPackages` depends on.

**Architecture:** Relocate the one shared module (`board_geometry.py`) into `Tools/HangboardPackages` first so nothing breaks when the Workbench tree is deleted. Then remove the `workbenchReview` audit schema and its data/tests, delete the tool plus its pipelines and hosting config, reword iOS comments/tests, and finally rewrite live docs and delete Workbench-topic docs. Dated historical audit records and Blender's unrelated "Workbench" render-engine docs are left alone.

**Tech Stack:** Python 3.11 (`pytest`), TypeScript/React (deleted), Swift/SwiftUI, GitHub Actions, JSON audit manifests.

**Scope note:** `.usdz` / model-package content is explicitly out of scope and must not be touched.

---

## Task 1: Relocate `board_geometry.py` into `HangboardPackages`

**Files:**
- Move: `Tools/HangboardWorkbench/board_geometry.py` → `Tools/HangboardPackages/src/hangboard_packages/board_geometry.py`
- Move: `Tools/HangboardWorkbench/tests/test_board_geometry.py` → `Tools/HangboardPackages/tests/test_board_geometry.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/geometry_cleanup.py`

- [ ] **Step 1: Move both files with git**

```bash
git mv Tools/HangboardWorkbench/board_geometry.py Tools/HangboardPackages/src/hangboard_packages/board_geometry.py
git mv Tools/HangboardWorkbench/tests/test_board_geometry.py Tools/HangboardPackages/tests/test_board_geometry.py
```

- [ ] **Step 2: Update `board_geometry.py` docstring**

Replace the first line:

```python
"""Exact, single-contour geometry used by the direct Workbench contact editor."""
```

with:

```python
"""Exact, single-contour board geometry shared by package tooling."""
```

- [ ] **Step 3: Update `geometry_cleanup.py` imports**

Replace lines 13–31:

```python
# Add parent directories to path using repository root relative to this file
REPO_ROOT = Path(__file__).resolve().parents[4]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
PACKAGES_ROOT = REPO_ROOT / "Tools" / "HangboardPackages" / "src"
sys.path.insert(0, str(WORKBENCH_ROOT))
sys.path.insert(0, str(PACKAGES_ROOT))

from board_geometry import (
    ClosedPath,
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    flattened_shape_bounds,
    normalized_frame_for_path,
    parse_closed_path,
    shape_for_path,
    union_normalized_frames,
)
from board_geometry_schema import BoardShapeDocument, NormalizedFrame as SchemaNormalizedFrame
```

with:

```python
# Add parent directories to path using repository root relative to this file
REPO_ROOT = Path(__file__).resolve().parents[4]
PACKAGES_ROOT = REPO_ROOT / "Tools" / "HangboardPackages" / "src"
sys.path.insert(0, str(PACKAGES_ROOT))

try:  # Standard package import, plus direct-file execution.
    from .board_geometry import (
        ClosedPath,
        GeometryError,
        NormalizedFrame,
        display_path_for_shape,
        flattened_shape_bounds,
        normalized_frame_for_path,
        parse_closed_path,
        shape_for_path,
        union_normalized_frames,
    )
    from .board_geometry_schema import (
        BoardShapeDocument,
        NormalizedFrame as SchemaNormalizedFrame,
    )
except ImportError:  # pragma: no cover - exercised when run as a direct script
    from board_geometry import (
        ClosedPath,
        GeometryError,
        NormalizedFrame,
        display_path_for_shape,
        flattened_shape_bounds,
        normalized_frame_for_path,
        parse_closed_path,
        shape_for_path,
        union_normalized_frames,
    )
    from board_geometry_schema import (
        BoardShapeDocument,
        NormalizedFrame as SchemaNormalizedFrame,
    )
```

- [ ] **Step 4: Update the ported test imports**

In `Tools/HangboardPackages/tests/test_board_geometry.py`, replace lines 3–33:

```python
import json
import math
import re
import sys
import time
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
VALIDATION_FIXTURES = json.loads(
    (
        REPOSITORY_ROOT
        / "HangTenTests"
        / "Fixtures"
        / "BoardPackageValidationFixtures.json"
    ).read_text(encoding="utf-8")
)
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_geometry  # noqa: E402
from board_geometry import (  # noqa: E402
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    normalized_frame_for_path,
    parse_closed_path,
    shape_for_path,
)
```

with:

```python
import json
import math
import re
import time
from pathlib import Path

import pytest

from hangboard_packages import board_geometry
from hangboard_packages.board_geometry import (
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    normalized_frame_for_path,
    parse_closed_path,
    shape_for_path,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
VALIDATION_FIXTURES = json.loads(
    (
        REPOSITORY_ROOT
        / "HangTenTests"
        / "Fixtures"
        / "BoardPackageValidationFixtures.json"
    ).read_text(encoding="utf-8")
)
```

- [ ] **Step 5: Run the ported test**

Run: `python3 -m pytest tests/test_board_geometry.py -q` (working directory `Tools/HangboardPackages`)
Expected: all tests pass (previously the same file passed in the Workbench suite).

- [ ] **Step 6: Run the full packages suite**

Run: `python3 -m pytest tests -q` (working directory `Tools/HangboardPackages`)
Expected: pass. `geometry_cleanup.py` import changes must not break collection.

- [ ] **Step 7: Commit**

```bash
git add Tools/HangboardPackages/src/hangboard_packages/board_geometry.py \
  Tools/HangboardPackages/src/hangboard_packages/geometry_cleanup.py \
  Tools/HangboardPackages/tests/test_board_geometry.py
git commit -m "refactor(packages): relocate board_geometry out of the workbench tree"
```

---

## Task 2: Remove `workbenchReview` from the audit schema and validation

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`

- [ ] **Step 1: Remove the Workbench check set**

Delete line 91:

```python
_WORKBENCH_CHECKS = frozenset({"normal", "allActive", "individualHolds"})
```

- [ ] **Step 2: Drop the field from `PresentationFinalState`**

Replace:

```python
@dataclass(frozen=True)
class PresentationFinalState:
    accepted_asset_sha256: str | None
    final_dimensions: tuple[int, int] | None
    visual_reviewer_decision: str
    workbench_review: Mapping[str, PresentationCheck]
    validation: Mapping[str, PresentationCheck]
```

with:

```python
@dataclass(frozen=True)
class PresentationFinalState:
    accepted_asset_sha256: str | None
    final_dimensions: tuple[int, int] | None
    visual_reviewer_decision: str
    validation: Mapping[str, PresentationCheck]
```

- [ ] **Step 3: Drop the field from `BootstrapReviewChecks`**

Replace:

```python
class BootstrapReviewChecks:
    evidence_review: PresentationCheck
    visual_review: PresentationCheck
    workbench_review: PresentationCheck
    package_validation: PresentationCheck
```

with:

```python
class BootstrapReviewChecks:
    evidence_review: PresentationCheck
    visual_review: PresentationCheck
    package_validation: PresentationCheck
```

- [ ] **Step 4: Remove `workbenchReview` from the phase-1 `_load_record` final parser**

In `_load_record`, replace the `final` handling:

```python
    final_payload = _mapping(payload["final"], f"{source}.final")
    _closed(
        final_payload,
        {
            "acceptedAssetSHA256",
            "finalDimensions",
            "visualReviewerDecision",
            "workbenchReview",
            "validation",
        },
        f"{source}.final",
    )
```

with:

```python
    final_payload = _mapping(payload["final"], f"{source}.final")
    _closed(
        final_payload,
        {
            "acceptedAssetSHA256",
            "finalDimensions",
            "visualReviewerDecision",
            "validation",
        },
        f"{source}.final",
    )
```

- [ ] **Step 5: Replace the `_load_record` final review construction**

Replace:

```python
    review_payload, validation_payload = (
        _mapping(final_payload["workbenchReview"], f"{source}.final.workbenchReview"),
        _mapping(final_payload["validation"], f"{source}.final.validation"),
    )
    _closed(review_payload, _WORKBENCH_CHECKS, f"{source}.final.workbenchReview")
    _closed(validation_payload, _VALIDATION_CHECKS, f"{source}.final.validation")
    final = PresentationFinalState(
        None
        if final_payload["acceptedAssetSHA256"] is None
        else _sha256(
            final_payload["acceptedAssetSHA256"], f"{source}.final.acceptedAssetSHA256"
        ),
        dimensions,
        _string(
            final_payload["visualReviewerDecision"],
            f"{source}.final.visualReviewerDecision",
        ),
        {
            key: _load_check(
                review_payload[key], f"{source}.final.workbenchReview.{key}"
            )
            for key in _WORKBENCH_CHECKS
        },
        {
            key: _load_check(
                validation_payload[key], f"{source}.final.validation.{key}"
            )
            for key in _VALIDATION_CHECKS
        },
    )
```

with:

```python
    validation_payload = _mapping(
        final_payload["validation"], f"{source}.final.validation"
    )
    _closed(validation_payload, _VALIDATION_CHECKS, f"{source}.final.validation")
    final = PresentationFinalState(
        None
        if final_payload["acceptedAssetSHA256"] is None
        else _sha256(
            final_payload["acceptedAssetSHA256"], f"{source}.final.acceptedAssetSHA256"
        ),
        dimensions,
        _string(
            final_payload["visualReviewerDecision"],
            f"{source}.final.visualReviewerDecision",
        ),
        {
            key: _load_check(
                validation_payload[key], f"{source}.final.validation.{key}"
            )
            for key in _VALIDATION_CHECKS
        },
    )
```

- [ ] **Step 6: Remove `workbenchReview` from `_load_bootstrap_set`**

Replace:

```python
    _closed(checks, {"evidenceReview", "visualReview", "workbenchReview", "packageValidation"}, f"{source}.reviewChecks")
```

with:

```python
    _closed(checks, {"evidenceReview", "visualReview", "packageValidation"}, f"{source}.reviewChecks")
```

and replace:

```python
        BootstrapReviewChecks(*(_load_phase2_check(checks[key], f"{source}.reviewChecks.{key}") for key in ("evidenceReview", "visualReview", "workbenchReview", "packageValidation"))),
```

with:

```python
        BootstrapReviewChecks(*(_load_phase2_check(checks[key], f"{source}.reviewChecks.{key}") for key in ("evidenceReview", "visualReview", "packageValidation"))),
```

- [ ] **Step 7: Remove `workbenchReview` from `_load_phase2_final`**

Replace:

```python
def _load_phase2_final(value: Any, source: str) -> PresentationFinalState:
    payload = _mapping(value, source)
    _closed(payload, {"acceptedAssetSHA256", "finalDimensions", "visualReviewerDecision", "workbenchReview", "validation"}, source)
    dimensions = None if payload["finalDimensions"] is None else _load_required_canvas(payload["finalDimensions"], f"{source}.finalDimensions")
    workbench = _mapping(payload["workbenchReview"], f"{source}.workbenchReview")
    _closed(workbench, {"normal", "allActive", "individualHolds", "hitTest"}, f"{source}.workbenchReview")
    validation = _mapping(payload["validation"], f"{source}.validation")
    _closed(validation, _VALIDATION_CHECKS, f"{source}.validation")
    return PresentationFinalState(
        None if payload["acceptedAssetSHA256"] is None else _sha256(payload["acceptedAssetSHA256"], f"{source}.acceptedAssetSHA256"),
        None if dimensions is None else (dimensions.width_pixels, dimensions.height_pixels),
        _string(payload["visualReviewerDecision"], f"{source}.visualReviewerDecision"),
        {key: _load_phase2_check(workbench[key], f"{source}.workbenchReview.{key}") for key in ("normal", "allActive", "individualHolds", "hitTest")},
        {
            **{key: _load_phase2_check(validation[key], f"{source}.validation.{key}") for key in ("packageValidation", "focusedTests", "fullPackageSuite", "buildForTesting")},
            "simulatorReview": _load_simulator_review(validation["simulatorReview"], f"{source}.validation.simulatorReview"),
        },
    )
```

with:

```python
def _load_phase2_final(value: Any, source: str) -> PresentationFinalState:
    payload = _mapping(value, source)
    _closed(payload, {"acceptedAssetSHA256", "finalDimensions", "visualReviewerDecision", "validation"}, source)
    dimensions = None if payload["finalDimensions"] is None else _load_required_canvas(payload["finalDimensions"], f"{source}.finalDimensions")
    validation = _mapping(payload["validation"], f"{source}.validation")
    _closed(validation, _VALIDATION_CHECKS, f"{source}.validation")
    return PresentationFinalState(
        None if payload["acceptedAssetSHA256"] is None else _sha256(payload["acceptedAssetSHA256"], f"{source}.acceptedAssetSHA256"),
        None if dimensions is None else (dimensions.width_pixels, dimensions.height_pixels),
        _string(payload["visualReviewerDecision"], f"{source}.visualReviewerDecision"),
        {
            **{key: _load_phase2_check(validation[key], f"{source}.validation.{key}") for key in ("packageValidation", "focusedTests", "fullPackageSuite", "buildForTesting")},
            "simulatorReview": _load_simulator_review(validation["simulatorReview"], f"{source}.validation.simulatorReview"),
        },
    )
```

- [ ] **Step 8: Remove `workbenchReview` from the legacy final in `_load_phase2_record`**

Replace:

```python
    legacy["final"] = {
        "acceptedAssetSHA256": final_payload.get("acceptedAssetSHA256"),
        "finalDimensions": final_payload.get("finalDimensions"),
        "visualReviewerDecision": final_payload.get("visualReviewerDecision"),
        "workbenchReview": {name: {"status": "pending", "evidence": None} for name in ("normal", "allActive", "individualHolds")},
        "validation": {name: {"status": "pending", "evidence": None} for name in _VALIDATION_CHECKS},
    }
```

with:

```python
    legacy["final"] = {
        "acceptedAssetSHA256": final_payload.get("acceptedAssetSHA256"),
        "finalDimensions": final_payload.get("finalDimensions"),
        "visualReviewerDecision": final_payload.get("visualReviewerDecision"),
        "validation": {name: {"status": "pending", "evidence": None} for name in _VALIDATION_CHECKS},
    }
```

- [ ] **Step 9: Update `_checks_are_pending`**

Replace:

```python
def _checks_are_pending(record: PresentationRemediationRecord) -> bool:
    return all(
        check.status == "pending" and check.evidence is None
        for check in (
            *record.final.workbench_review.values(),
            *record.final.validation.values(),
        )
    )
```

with:

```python
def _checks_are_pending(record: PresentationRemediationRecord) -> bool:
    return all(
        check.status == "pending" and check.evidence is None
        for check in record.final.validation.values()
    )
```

- [ ] **Step 10: Remove the keep-time Workbench checks**

Replace:

```python
        if any(not _check_pending(record.final.workbench_review[name]) for name in ("normal", "allActive", "individualHolds")):
            raise PresentationRemediationAuditError("keeps retain pending Phase 1 Workbench checks")
        hit_test = record.final.workbench_review["hitTest"]
        if hit_test.status != "notRequired" or hit_test.evidence is None:
            raise PresentationRemediationAuditError("keep hitTest must be factually notRequired")
        if any(not _check_pending(record.final.validation[name]) for name in ("packageValidation", "focusedTests", "fullPackageSuite", "buildForTesting")):
```

with:

```python
        if any(not _check_pending(record.final.validation[name]) for name in ("packageValidation", "focusedTests", "fullPackageSuite", "buildForTesting")):
```

- [ ] **Step 11: Remove the completed-action Workbench requirement**

Replace:

```python
        if any(not _check_passed(check) for check in record.final.workbench_review.values()):
            raise PresentationRemediationAuditError("completed Phase 2 action requires four passed Workbench checks")
        if not _check_passed(package_check) or not _check_passed(focused_check):
```

with:

```python
        if not _check_passed(package_check) or not _check_passed(focused_check):
```

- [ ] **Step 12: Remove the non-completed Workbench prewrite guard**

Replace:

```python
        if any(
            not _check_pending(check)
            for check in record.final.workbench_review.values()
        ):
            raise PresentationRemediationAuditError(
                "non-completed action cannot prewrite Workbench results"
            )
        if any(
            not _check_pending(check)
            for check in (package_check, focused_check, full_check, build_check)
        ):
```

with:

```python
        if any(
            not _check_pending(check)
            for check in (package_check, focused_check, full_check, build_check)
        ):
```

- [ ] **Step 13: Update bootstrap acceptance to three checks**

Replace:

```python
    all_four = all(_check_passed(check) for check in (checks.evidence_review, checks.visual_review, checks.workbench_review, checks.package_validation))
```

with:

```python
    all_three = all(_check_passed(check) for check in (checks.evidence_review, checks.visual_review, checks.package_validation))
```

Then replace:

```python
        record_reviews_pass = (
            record.final.visual_reviewer_decision == "acceptedPhase2"
            and all(_check_passed(check) for check in record.final.workbench_review.values())
            and _check_passed(package_check)
        )
        if not all_four or not record_reviews_pass or bootstrap.accepted_at is None or bootstrap.blocked_reason is not None:
            raise PresentationRemediationAuditError(
                "bootstrap acceptance requires passed evidence, visual, Workbench, and package review"
            )
```

with:

```python
        record_reviews_pass = (
            record.final.visual_reviewer_decision == "acceptedPhase2"
            and _check_passed(package_check)
        )
        if not all_three or not record_reviews_pass or bootstrap.accepted_at is None or bootstrap.blocked_reason is not None:
            raise PresentationRemediationAuditError(
                "bootstrap acceptance requires passed evidence, visual, and package review"
            )
```

- [ ] **Step 14: Update the bootstrap `selected` and `blocked` branches**

Replace:

```python
            or not _check_pending(checks.visual_review)
            or not _check_pending(checks.workbench_review)
            or not _check_pending(checks.package_validation)
```

with:

```python
            or not _check_pending(checks.visual_review)
            or not _check_pending(checks.package_validation)
```

Replace both occurrences of:

```python
                    checks.evidence_review,
                    checks.visual_review,
                    checks.workbench_review,
                    checks.package_validation,
```

with:

```python
                    checks.evidence_review,
                    checks.visual_review,
                    checks.package_validation,
```

- [ ] **Step 15: Reword `_COHORT_BASELINE_REASON`**

Replace:

```python
_COHORT_BASELINE_REASON = (
    "Accepted cohort bootstrap baseline after direct evidence, Workbench, package, "
    "and visual review; style-only for downstream use, no geometry."
)
```

with:

```python
_COHORT_BASELINE_REASON = (
    "Accepted cohort bootstrap baseline after direct evidence, package, and visual "
    "review; style-only for downstream use, no geometry."
)
```

- [ ] **Step 16: Confirm no Workbench symbols remain in the module**

Run: `rg -n 'workbench|Workbench' Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py`
Expected: no output.

- [ ] **Step 17: Commit**

```bash
git add Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py
git commit -m "refactor(audit): remove Workbench review schema and validation"
```

---

## Task 3: Remove `workbenchReview` from manifest, helpers, and tests

**Files:**
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Modify: `Tools/HangboardPackages/tests/presentation_remediation_helpers.py`
- Modify: `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`
- Modify: `Tools/HangboardPackages/tests/test_hard_cut_audit.py`

- [ ] **Step 1: Strip `workbenchReview` from the canonical manifest**

Run from the repository root:

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json")
data = json.loads(path.read_text(encoding="utf-8"))
removed = 0
for record in data["records"]:
    if "workbenchReview" in record["final"]:
        record["final"].pop("workbenchReview")
        removed += 1
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("removed", removed)
PY
```

Expected: prints `removed 85`.

- [ ] **Step 2: Verify the manifest diff is removals only**

Run: `git diff --stat docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
Then run: `git diff docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json | rg '^\+' | rg -v '^\+\+\+'`
Expected: no added lines.

- [ ] **Step 3: Remove the helper builder**

In `Tools/HangboardPackages/tests/presentation_remediation_helpers.py`, delete:

```python
            "workbenchReview": {
                name: {"status": "pending", "evidence": None}
                for name in ("normal", "allActive", "individualHolds")
            },
```

so the `final` mapping is:

```python
            "finalDimensions": {"widthPixels": width, "heightPixels": height},
            "visualReviewerDecision": "acceptedCurrentAsset",
            "validation": {
```

- [ ] **Step 4: Update the parametrized reclassification test**

In `Tools/HangboardPackages/tests/test_presentation_remediation_audit.py`, replace:

```python
@pytest.mark.parametrize(
    ("section", "check_name"),
    [("workbenchReview", "normal"), ("validation", "packageValidation")],
)
```

with:

```python
@pytest.mark.parametrize(
    ("section", "check_name"),
    [("validation", "packageValidation")],
)
```

- [ ] **Step 5: Update the unknown-status test**

Replace:

```python
    record["final"]["workbenchReview"]["normal"]["status"] = "invented"
```

with:

```python
    record["final"]["validation"]["packageValidation"]["status"] = "invented"
```

- [ ] **Step 6: Update the missing-keys mutation**

Replace:

```python
        (
            lambda d: d["records"][1]["final"]["workbenchReview"].pop(
                "hitTest"
            ),
            "workbenchReview is missing keys",
        ),
```

with:

```python
        (
            lambda d: d["records"][1]["final"]["validation"].pop(
                "simulatorReview"
            ),
            "validation is missing keys",
        ),
```

- [ ] **Step 7: Delete the Workbench directory scan test**

In `Tools/HangboardPackages/tests/test_hard_cut_audit.py`, delete the entire function:

```python
def test_workbench_has_no_older_schema_adapter_or_hold_wire_contract() -> None:
    workbench = REPOSITORY_ROOT / "Tools" / "HangboardWorkbench"
    sources = _source_text(workbench, {".py", ".ts", ".tsx"})
    for prohibited in (
        "_schema_v2",
        "_legacy_editor",
        "_schema_v2_board",
        "holdGeometry",
        "holdID",
        'board["holds"]',
        "board['holds']",
        "schemaVersion == 2",
    ):
        assert prohibited not in sources
```

- [ ] **Step 8: Confirm no Workbench references remain in packages tests/src**

Run: `rg -n 'workbench|Workbench' Tools/HangboardPackages/src Tools/HangboardPackages/tests`
Expected: no output.

- [ ] **Step 9: Run the packages suite**

Run: `python3 -m pytest tests -q` (working directory `Tools/HangboardPackages`)
Expected: pass.

- [ ] **Step 10: Run the inventory validation**

Run: `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
Expected: passes with the same package/draft counts as before.

- [ ] **Step 11: Commit**

```bash
git add docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  Tools/HangboardPackages/tests/presentation_remediation_helpers.py \
  Tools/HangboardPackages/tests/test_presentation_remediation_audit.py \
  Tools/HangboardPackages/tests/test_hard_cut_audit.py
git commit -m "test(audit): drop Workbench review data and assertions"
```

---

## Task 4: Delete the tool, CI, release, and hosting

**Files:**
- Delete: `Tools/HangboardWorkbench/` (remainder)
- Delete: `.github/actions/build-hangboard-workbench/`
- Delete: `.github/workflows/hangboard-workbench-pr.yml`
- Delete: `.github/workflows/hangboard-workbench-pr-comment.yml`
- Delete: `.github/workflows/hangboard-workbench-release.yml`
- Delete: `render.yaml`
- Modify: `.github/ci-paths.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/dependabot.yml`
- Modify: `.gitignore`

- [ ] **Step 1: Delete the tool tree and pipelines**

```bash
git rm -r Tools/HangboardWorkbench
git rm -r .github/actions/build-hangboard-workbench
git rm .github/workflows/hangboard-workbench-pr.yml
git rm .github/workflows/hangboard-workbench-pr-comment.yml
git rm .github/workflows/hangboard-workbench-release.yml
git rm render.yaml
```

- [ ] **Step 2: Clean `.github/ci-paths.yml`**

Remove the `workbench_web`, `workbench_native`, and `workbench` blocks entirely, remove the two Workbench lines from `python`, and remove the Workbench pyproject line from `workflow`. The resulting file is:

```yaml
ios:
  - 'HangTen/**'
  - 'HangTenTests/**'
  - 'HangTenUITests/**'
  - 'HangTen.xcodeproj/**'
  - '.github/ExportOptions.plist'
  - 'HangTen/Resources/CountdownAudio/**'
python:
  - 'Tools/HangboardPackages/**'
  - 'HangTenUITests/**'
  - 'scripts/hangboard-packages.sh'
  - 'scripts/run-supported-python.sh'
shared_board_content:
  - 'Tools/HangboardPackages/**'
  - 'Hangboards/**'
  - 'scripts/hangboard-packages.sh'
  - 'scripts/stage-board-packages.py'
  - 'scripts/run-supported-python.sh'
metadata:
  - 'metadata/**'
  - 'scripts/validate-app-store-metadata.sh'
  - 'HangTen.xcodeproj/**'
  - 'HangTen/Resources/Assets.xcassets/AppIcon.appiconset/**'
workflow:
  - '.github/workflows/**'
  - '.github/ci-paths.yml'
  - '.github/actions/**'
```

- [ ] **Step 3: Remove the unused CI outputs**

In `.github/workflows/ci.yml`, delete these two lines under `outputs:`:

```yaml
      workbench_web: ${{ steps.filter.outputs.workbench_web }}
      workbench_native: ${{ steps.filter.outputs.workbench_native }}
```

- [ ] **Step 4: Remove the Workbench dependabot entry**

In `.github/dependabot.yml`, delete:

```yaml
  - package-ecosystem: pip
    directory: /Tools/HangboardWorkbench
    schedule:
      interval: weekly
    open-pull-requests-limit: 10
```

- [ ] **Step 5: Clean `.gitignore`**

Delete these lines and their comments:

```gitignore
# Workbench's local board-library lock
/Hangboards/.workbench.lock

# PyInstaller output for the local workbench release build
/Tools/HangboardWorkbench/packaging/build/
/Tools/HangboardWorkbench/packaging/dist/
/Tools/HangboardWorkbench/packaging/*.spec
/Tools/HangboardWorkbench/node_modules/
/Tools/HangboardWorkbench/app.js
```

- [ ] **Step 6: Lint the workflows**

Run: `python3 -c "import yaml,glob;[yaml.safe_load(open(p)) for p in glob.glob('.github/workflows/*.yml')+['.github/ci-paths.yml','.github/dependabot.yml']];print('ok')"`
Expected: `ok`.

If `actionlint` is available, also run: `actionlint`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add -A .github .gitignore render.yaml Tools/HangboardWorkbench
git commit -m "chore: delete Hangboard Workbench tool, CI, release, and hosting"
```

---

## Task 5: Update iOS app and test references

**Files:**
- Modify: `HangTen/Models/BoardStorage.swift`
- Modify: `HangTen/Views/BoardEditor/BoardEditorSession.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/HoldPathEngineTests.swift`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`

- [ ] **Step 1: Reword the `BoardStorage.swift` comment**

Replace:

```swift
        // The Workbench editor supports off-canvas hold geometry (e.g. x = -0.3,
```

with:

```swift
        // The board editor supports off-canvas hold geometry (e.g. x = -0.3,
```

(Preserve the rest of the comment block.)

- [ ] **Step 2: Reword the two `BoardEditorSession.swift` comments**

Replace:

```swift
    /// where all interactive editing happens (Workbench display-path parity).
```

with:

```swift
    /// where all interactive editing happens (display-path parity).
```

Replace:

```swift
    /// into it, mirroring the Workbench display-path save pipeline. Control
```

with:

```swift
    /// into it, mirroring the display-path save pipeline. Control
```

- [ ] **Step 3: Reword the `BoardPackageStoreTests.swift` comment**

Replace the phrase:

```swift
    /// Swift's discovery sort must agree with the Workbench's directory
```

with:

```swift
    /// Swift's discovery sort must agree with the package directory
```

- [ ] **Step 4: Rename the `HoldPathEngineTests.swift` test**

Replace:

```swift
    func testOutlinePresetGenerationMatchesWorkbenchSerialization() throws {
```

with:

```swift
    func testOutlinePresetGenerationMatchesCanonicalSerialization() throws {
```

- [ ] **Step 5: Remove the `.workbench.lock` operational-file allowance**

In `HangTenTests/BoardSourceBoundaryTests.swift`, delete the entire test function:

```swift
    func testPackageDiscoveryAllowsOnlySafeWorkbenchLockOperationalFile() throws {
        let repositoryRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let hangboardsURL = repositoryRoot.appendingPathComponent("Hangboards", isDirectory: true)
        let packageURL = hangboardsURL.appendingPathComponent("fixture-board", isDirectory: true)
        let lockURL = hangboardsURL.appendingPathComponent(".workbench.lock")
        let unexpectedFileURL = hangboardsURL.appendingPathComponent("unexpected.txt")
        let outsideLockURL = repositoryRoot.appendingPathComponent("outside-lock")
        try FileManager.default.createDirectory(at: packageURL, withIntermediateDirectories: true)
        try Data(#"{"id":"fixture.board"}"#.utf8).write(
            to: packageURL.appendingPathComponent("board.json")
        )
        defer { try? FileManager.default.removeItem(at: repositoryRoot) }

        try Data().write(to: lockURL)
        XCTAssertEqual(
            try discoveredPackagePaths(at: repositoryRoot),
            ["fixture.board": "fixture-board"]
        )

        try FileManager.default.removeItem(at: lockURL)
        try Data().write(to: outsideLockURL)
        try FileManager.default.createSymbolicLink(
            at: lockURL,
            withDestinationURL: outsideLockURL
        )
        XCTAssertThrowsError(try discoveredPackagePaths(at: repositoryRoot))

        try FileManager.default.removeItem(at: lockURL)
        try FileManager.default.createDirectory(at: lockURL, withIntermediateDirectories: false)
        XCTAssertThrowsError(try discoveredPackagePaths(at: repositoryRoot))

        try FileManager.default.removeItem(at: lockURL)
        try Data().write(to: unexpectedFileURL)
        XCTAssertThrowsError(try discoveredPackagePaths(at: repositoryRoot))
    }
```

Then in the test helper `discoveredPackagePaths(at:)`, delete the special-case branch:

```swift
            if child.lastPathComponent == ".workbench.lock" {
                guard values.isRegularFile == true, values.isSymbolicLink != true else {
                    throw PackageDiscoveryError.invalidRootChild(child.lastPathComponent)
                }
                continue
            }
```

so the loop proceeds directly from the resource values to the directory guard:

```swift
            let values = try child.resourceValues(forKeys: [
                .isDirectoryKey,
                .isRegularFileKey,
                .isSymbolicLinkKey
            ])
            guard values.isDirectory == true, values.isSymbolicLink != true else {
                throw PackageDiscoveryError.invalidRootChild(child.lastPathComponent)
            }
```

- [ ] **Step 6: Confirm no Workbench references remain in iOS sources/tests**

Run: `rg -n 'workbench|Workbench' HangTen HangTenTests`
Expected: no output.

- [ ] **Step 7: Build and run the affected unit tests**

Use the `validate-hang-ten-ios` skill (or `scripts/ci-run-xctest.sh` with `XCTEST_ONLY_TESTING=HangTenTests`) to build and run at least `HangTenTests/BoardPackageStoreTests`, `HangTenTests/BoardSourceBoundaryTests`, and `HangTenTests/HoldPathEngineTests`.
Expected: build succeeds and the suites pass.

- [ ] **Step 8: Commit**

```bash
git add HangTen HangTenTests
git commit -m "refactor(ios): remove Workbench references and lock allowance"
```

---

## Task 6: Rewrite live docs and delete Workbench-topic docs

**Files:**
- Delete the eight Workbench-topic Superpowers docs (listed below)
- Modify: `AGENTS.md`, `README.md`, `docs/ADDING_A_BOARD.md`, `docs/IOS_SIMULATOR_VALIDATION.md`, `docs/source-audits/2026-08-12-hangboard-batch-template.md`, `docs/source-audits/screenshots/pr-246/README.md`

- [ ] **Step 1: Delete Workbench-topic docs**

```bash
git rm docs/superpowers/plans/2026-08-19-react-workbench-editor.md \
  docs/superpowers/plans/2026-08-20-source-only-workbench-bundling.md \
  docs/superpowers/plans/2026-08-20-workbench-editor-history-shortcuts.md \
  docs/superpowers/plans/2026-08-16-github-oauth.md \
  docs/superpowers/specs/2026-08-19-react-workbench-editor-design.md \
  docs/superpowers/specs/2026-08-20-source-only-workbench-bundling-design.md \
  docs/superpowers/specs/2026-08-20-workbench-editor-history-shortcuts-design.md \
  docs/superpowers/specs/2026-08-16-github-oauth-design.md
```

- [ ] **Step 2: Reword `AGENTS.md`**

Replace:

```markdown
When the checked-out schema and Workbench support shape constraints, prefer an
```

with:

```markdown
When the checked-out schema and the board editor support shape constraints, prefer an
```

Replace:

```markdown
accepted process is direct path authoring, package validation, and human visual
review in Workbench and the app.
```

with:

```markdown
accepted process is direct path authoring, package validation, and human visual
review in the app.
```

- [ ] **Step 3: Reword `README.md`**

Replace:

```markdown
`GITHUB_OAUTH_CLIENT_ID` in the iOS app's Info.plist. This iOS-only restriction
does not apply to the browser-hosted Workbench, whose server-side OAuth flow
retains its separately hosted `GITHUB_CLIENT_SECRET` configuration. The app
requests `repo read:org` and no longer accepts personal access tokens.
```

with:

```markdown
`GITHUB_OAUTH_CLIENT_ID` in the iOS app's Info.plist. The app requests
`repo read:org` and no longer accepts personal access tokens.
```

Replace:

```markdown
schema-v3 validation. Remote model editing is unsupported; iOS and Workbench
treat model packages as read-only, while raster Workbench editing remains
contact-native.

Use the packaged macOS Hangboard Workbench for direct local visual editing.
Browser-hosted Workbench deployments must use the GitHub-backed
`--allow-remote` server mode.

For raster packages, Workbench edits are explicit operator changes to canonical
package geometry; the saved paths remain the exact rendering and hit-testing
source of truth. Model packages are read-only for geometry editing and use
their mesh and descriptor as the presentation source.
```

with:

```markdown
schema-v3 validation. Remote model editing is unsupported; the app treats model
packages as read-only and uses their mesh and descriptor as the presentation
source.

For raster packages, board-editor edits are explicit operator changes to
canonical package geometry; the saved paths remain the exact rendering and
hit-testing source of truth.
```

- [ ] **Step 4: Reword `docs/ADDING_A_BOARD.md`**

Replace:

```markdown
raster fallback and is read-only in Workbench.
```

with:

```markdown
raster fallback and is read-only in the in-app board editor.
```

Replace:

```markdown
Open the completed raster package in Hangboard Workbench. Deliberately draw and
```

with:

```markdown
Open the completed raster package in the in-app board editor. Deliberately draw and
```

- [ ] **Step 5: Remove the Workbench section from `docs/IOS_SIMULATOR_VALIDATION.md`**

Delete this section in full (including its heading and the `## Create and identify a dedicated device` heading stays):

```markdown
## Workbench handoff boundary

The browser suite's **Validate** tool accepts only an explicit UUID from the
caller and formats copyable build, install, launch, and screenshot commands.
It does not create, delete, boot, erase, or archive simulators, and it never
commits, pushes, or synchronizes remotely. Before entering a UUID in the
browser, create and record the dedicated simulator under this ownership
contract. The caller is responsible for booting, reviewing, and cleaning up
that exact UUID; never substitute `booted` or another workspace's device.

```

- [ ] **Step 6: Reword the source-audit template**

In `docs/source-audits/2026-08-12-hangboard-batch-template.md`:

Replace:

```markdown
Author each normalized closed path deliberately in `board.json`, then refine it
in Workbench against the primary evidence. Mirror a reviewed side exactly when
```

with:

```markdown
Author each normalized closed path deliberately in `board.json`, then refine it
against the primary evidence. Mirror a reviewed side exactly when
```

Replace:

```markdown
Record package-validator output and the visual reviewer/date. Inspect normal
paths in Workbench and active/highlight alignment in the app on an owned
simulator.
```

with:

```markdown
Record package-validator output and the visual reviewer/date. Inspect normal
paths and active/highlight alignment in the app on an owned simulator.
```

Replace the table header:

```markdown
| package slug | validator result | Workbench review | app highlight review | unresolved omissions |
```

with:

```markdown
| package slug | validator result | visual review | app highlight review | unresolved omissions |
```

- [ ] **Step 7: Reword the PR-246 screenshot note**

In `docs/source-audits/screenshots/pr-246/README.md`, replace:

```markdown
with a compact Workbench inspection capture from the same final review set.
```

with:

```markdown
with a compact overlay inspection capture from the same final review set.
```

- [ ] **Step 8: Confirm only allowed residual references remain**

Run: `rg -n -i 'workbench' --glob '!docs/source-audits/**/blender-smooth-shading-*.html' --glob '!docs/superpowers/specs/2026-09-22-remove-hangboard-workbench-design.md' --glob '!docs/superpowers/plans/2026-09-22-remove-hangboard-workbench.md'`
Expected: only dated historical audit records and incidental historical plan/spec mentions (per spec policy). No live config, code, README, AGENTS.md, ADDING_A_BOARD, or IOS_SIMULATOR_VALIDATION hits.

- [ ] **Step 9: Run the documentation contract test**

Run: `python3 -m pytest tests/test_documentation_paths.py -q` (working directory `Tools/HangboardPackages`)
Expected: pass (`README`/`ADDING_A_BOARD` still contain the required phrases such as `directly discovered` and `assets/primary.png`).

- [ ] **Step 10: Commit**

```bash
git add -A AGENTS.md README.md docs
git commit -m "docs: remove Hangboard Workbench references and Workbench-topic docs"
```

---

## Task 7: Final verification sweep

**Files:** none (verification only)

- [ ] **Step 1: Full packages suite**

Run: `python3 -m pytest tests -q` (working directory `Tools/HangboardPackages`)
Expected: pass.

- [ ] **Step 2: Inventory validation**

Run: `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
Expected: pass.

- [ ] **Step 3: Repo-wide residual check**

Run: `rg -n -i 'workbench' --glob '!**/node_modules/**'`
Expected: only Blender Workbench references, unedited dated historical audit records, and the removal spec/plan themselves. Investigate any other hit before finishing.

- [ ] **Step 4: Confirm the tool and pipelines are gone**

Run: `test ! -e Tools/HangboardWorkbench && test ! -e render.yaml && test ! -e .github/actions/build-hangboard-workbench && echo gone`
Expected: `gone`.

- [ ] **Step 5: Push**

```bash
git push
```
