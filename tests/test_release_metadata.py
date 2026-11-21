"""The version lives in one place and every release file agrees with it."""
import re
from pathlib import Path

from app.config.settings import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_version_is_semantic():
    assert re.fullmatch(r"\d+\.\d+\.\d+", APP_VERSION)


def test_changelog_leads_with_the_current_version():
    headings = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", _read("CHANGELOG.md"), re.MULTILINE)
    assert headings and headings[0] == APP_VERSION


def test_readme_names_the_current_version_and_installer():
    readme = _read("README.md")
    assert f"**الإصدار {APP_VERSION}**" in readme
    assert f"DailySticky-Setup-{APP_VERSION}.exe" in readme


def test_installer_takes_its_version_from_the_build():
    script = _read("installer/DailySticky.iss")
    assert "#ifndef MyAppVersion" in script
    assert not re.search(r'#define\s+MyAppVersion\s+"', script)  # never hardcoded
    assert "DailySticky-Setup-{#MyAppVersion}" in script


def test_installer_recognises_an_installed_copy():
    script = _read("installer/DailySticky.iss")
    assert "AppId={{D37E8C21-6A18-4F92-B72F-89E3A59102B4}" in script  # must never change
    for name in ("ReadInstalledVersion", "CompareVersions", "InitializeSetup", "PrepareToInstall"):
        assert name in script


def test_build_script_reads_the_version_and_hands_it_to_the_installer():
    build = _read("packaging/build_windows.ps1")
    assert "APP_VERSION" in build
    assert "/DMyAppVersion=" in build
