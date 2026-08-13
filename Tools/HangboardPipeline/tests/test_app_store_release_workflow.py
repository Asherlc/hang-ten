from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"


def test_release_uploads_archived_dsyms_with_scoped_sentry_configuration() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}" in workflow
    assert "SENTRY_ORG: ${{ vars.SENTRY_ORG }}" in workflow
    assert "SENTRY_PROJECT: ${{ vars.SENTRY_IOS_PROJECT }}" in workflow
    assert 'dsym_dir="$PWD/build/HangTen.xcarchive/dSYMs"' in workflow
    assert 'sentry-cli debug-files upload "$dsym_dir"' in workflow
    assert "SENTRY_AUTH_TOKEN =" not in workflow
PROJECT_PATH = REPOSITORY_ROOT / "HangTen.xcodeproj" / "project.pbxproj"


def test_archive_scopes_manual_provisioning_profile_to_app_target() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    project = PROJECT_PATH.read_text(encoding="utf-8")

    assert 'HANGTEN_DEVELOPMENT_TEAM="$APPLE_TEAM_ID"' in workflow
    assert (
        'HANGTEN_PROVISIONING_PROFILE_SPECIFIER="$PROVISIONING_PROFILE_UUID"'
        in workflow
    )
    assert '            DEVELOPMENT_TEAM="$APPLE_TEAM_ID" \\' not in workflow
    assert '            PROVISIONING_PROFILE_SPECIFIER=' not in workflow
    assert 'DEVELOPMENT_TEAM = "$(HANGTEN_DEVELOPMENT_TEAM)";' in project
    assert (
        'PROVISIONING_PROFILE_SPECIFIER = '
        '"$(HANGTEN_PROVISIONING_PROFILE_SPECIFIER)";'
        in project
    )
