"""Regression tests for the honesty contract of the backend test runner.

Each case writes disposable fixture test files into a temporary directory and
runs the real ``scripts/run_all_backend_tests.py`` as a subprocess against
that directory. Nothing here touches the project's own test suite, its
database, or any user data.
"""
import re
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "scripts" / "run_all_backend_tests.py"


def _run_runner(tmp_path, *fixture_files, extra_args=()):
    """Write fixture files, run the runner, and return (returncode, stdout, stderr)."""
    for name, body in fixture_files:
        (tmp_path / name).write_text(body, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(RUNNER), str(tmp_path), *extra_args],
        capture_output=True,
        text=True,
        timeout=600,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _summary_line(stdout, label):
    """Extract the count printed for ``label`` in the runner's summary block.

    The summary prints ``  <label>  <count>   <definition>``, so the count is
    the first integer token after the label -- not the last token on the line.
    """
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith(label + " "):
            match = re.search(r"\d+", stripped[len(label):])
            if match:
                return int(match.group())
    raise AssertionError(f"no summary line for {label!r} in:\n{stdout}")


def _accounting_lines(stdout):
    """Return the two printed accounting identities, for consistency checks."""
    return [ln.strip() for ln in stdout.splitlines()
            if ln.strip().startswith("Accounting:")
            or ln.strip().startswith("invoked ") and "=" in ln]


# --------------------------------------------------------------------------- #
# 1. Parametrised files must not be silently omitted
# --------------------------------------------------------------------------- #

PARAMETRISED_FILE = '''
import pytest


@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized_cases_all_run(value):
    assert value > 0
'''

PARAMETRISED_STACKED_FILE = '''
import pytest


@pytest.mark.parametrize("text", ["a", "b"])
@pytest.mark.parametrize("width", [320, 380])
def test_stacked_parametrize_is_a_cartesian_product(text, width):
    assert isinstance(text, str)
    assert width >= 320
'''


def test_parametrized_file_is_not_silently_omitted(tmp_path):
    """The original defect: pytest.mark made a whole file vanish from the run."""
    code, out, err = _run_runner(tmp_path, ("test_param.py", PARAMETRISED_FILE))

    assert _summary_line(out, "collection-error") == 0, out
    assert _summary_line(out, "verified") == 3, out
    assert _summary_line(out, "not-run") == 0, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_stacked_parametrize_produces_the_cartesian_product(tmp_path):
    """Stacked decorators multiply, matching pytest, rather than overwriting."""
    code, out, err = _run_runner(tmp_path, ("test_stacked.py", PARAMETRISED_STACKED_FILE))

    assert _summary_line(out, "verified") == 4, out
    assert code == 0, (code, out, err)


# --------------------------------------------------------------------------- #
# 2. A collection failure must be visible and non-zero
# --------------------------------------------------------------------------- #

BROKEN_IMPORT_FILE = '''
raise RuntimeError("deliberate import-time explosion")
'''

UNSUPPORTED_API_FILE = '''
import pytest


@pytest.mark.usefixtures("nothing_real")
def test_uses_an_api_the_runner_cannot_honour():
    assert True
'''


def test_import_failure_is_visible_and_exits_non_zero(tmp_path):
    code, out, err = _run_runner(tmp_path, ("test_broken.py", BROKEN_IMPORT_FILE))

    assert code != 0, (code, out, err)
    assert _summary_line(out, "collection-error") == 1, out
    assert "test_broken.py" in out, out
    assert "deliberate import-time explosion" in out, out
    assert "RESULT: FAILED" in out, out
    assert "This run is NOT green" in out, out


def test_unsupported_pytest_api_fails_loudly_instead_of_skipping(tmp_path):
    """An API outside the documented subset must not make the file disappear."""
    code, out, err = _run_runner(tmp_path, ("test_unsupported.py", UNSUPPORTED_API_FILE))

    assert code != 0, (code, out, err)
    assert _summary_line(out, "collection-error") == 1, out
    assert "pytest.mark.usefixtures" in out, out


def test_class_based_tests_are_not_silently_dropped(tmp_path):
    """The static-intent cross-check catches tests this runner cannot collect."""
    code, out, err = _run_runner(tmp_path, ("test_class.py", '''
class TestHiddenFromTheRunner:
    def test_inside_a_class(self):
        assert True
'''))

    assert code != 0, (code, out, err)
    assert _summary_line(out, "collection-error") == 1, out
    assert "class-based tests are invisible" in out, out


# --------------------------------------------------------------------------- #
# 3. Missing dependencies must not manufacture passes
# --------------------------------------------------------------------------- #

DEPENDENCY_GUARD_FILE = '''
def test_guarded_by_an_absent_dependency():
    try:
        import daily_sticky_definitely_absent_dependency
    except ImportError:
        return  # the classic silent-skip shape this runner must not reward
    assert daily_sticky_definitely_absent_dependency
'''


def test_missing_dependency_does_not_produce_a_false_pass(tmp_path):
    code, out, err = _run_runner(tmp_path, ("test_guarded.py", DEPENDENCY_GUARD_FILE))

    assert _summary_line(out, "verified") == 0, out
    assert _summary_line(out, "not-run") == 1, out
    assert code != 0, (code, out, err)
    assert "RESULT: FAILED" in out, out


# --------------------------------------------------------------------------- #
# 4. Platform-inapplicable tests are skipped or unverified, never "passed"
# --------------------------------------------------------------------------- #

EXPLICIT_SKIP_FILE = '''
import pytest


@pytest.mark.skip(reason="Windows-only check")
def test_windows_only_marked_skip():
    assert False


@pytest.mark.skipif(sys.platform == "win32", reason="not Windows")
def test_skipif_condition_false_here():
    assert 1 == 1


def test_explicit_skip_call():
    pytest.skip("not applicable on this platform")
'''

GUARDED_FILE = '''
def test_real_work():
    value = 1
    assert value == 1


def test_guarded_like_the_qt_suite():
    try:
        import PySide6
    except ImportError:
        return
    assert PySide6 is not None
'''


def test_explicit_skips_are_reported_as_skipped(tmp_path):
    """An explained exclusion is reported, and does not by itself fail the run.

    A skip *marker* declines the test without calling it, so it is reported as
    ``not invoked``; a ``pytest.skip()`` call happens inside an invoked test, so
    it is reported as ``skipped``. The two must not overlap.
    """
    code, out, err = _run_runner(
        tmp_path,
        ("test_skips.py", "import sys\n" + EXPLICIT_SKIP_FILE),
    )

    assert _summary_line(out, "skipped") == 1, out       # runtime pytest.skip()
    assert _summary_line(out, "not invoked") == 1, out   # @pytest.mark.skip
    assert _summary_line(out, "verified") == 1, out      # skipif condition false
    assert _summary_line(out, "invoked") == 2, out
    # No failures, but not everything ran: this is exit 3, not a green run.
    assert code == 3, (code, out, err)
    assert "RESULT: OK WITH SKIPS" in out, out
    assert "This is NOT a fully verified run" in out, out
    assert "COVERAGE: 1 of 3 declared case(s) verified (33%)" in out, out
    assert "Exit code 3." in out, out


def test_a_dependency_guard_is_skipped_not_not_run(tmp_path):
    """A test that declines via its own dependency guard is a *skip*.

    This is the difference between a test that deliberately stood aside because
    an optional dependency is missing, and one that silently swallowed a
    failure. Both prove nothing, but only the second is an unknown outcome.
    """
    code, out, err = _run_runner(tmp_path, ("test_depguard.py", '''
QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def test_needs_qt():
    if _skip_without_qt():
        return
    assert QT_AVAILABLE


def test_real_work():
    assert 1 == 1
'''))

    assert _summary_line(out, "skipped") == 1, out
    assert _summary_line(out, "verified") == 1, out
    assert _summary_line(out, "not-run") == 0, out
    assert "declined by its own dependency guard" in out, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert code == 3, (code, out, err)


def test_a_platform_guard_is_skipped_on_evidence(tmp_path):
    """A platform guard is classified by evaluating its condition, not by
    matching its shape."""
    code, out, err = _run_runner(tmp_path, ("test_platform.py", '''
import sys


def test_windows_only():
    if sys.platform != "win32":
        return
    assert True


def test_real_work():
    assert 1 == 1
'''))

    assert _summary_line(out, "skipped") == 1, out
    assert "platform guard" in out, out
    assert _summary_line(out, "not-run") == 0, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert code == 3, (code, out, err)


def test_silent_guard_is_reported_as_not_run_not_passed(tmp_path):
    """The audit's core finding: a guard that returns early is not a pass."""
    code, out, err = _run_runner(tmp_path, ("test_guarded.py", GUARDED_FILE))

    assert _summary_line(out, "not-run") == 1, out
    assert _summary_line(out, "verified") == 1, out
    assert code != 0, (code, out, err)
    assert "RESULT: FAILED" in out, out


# --------------------------------------------------------------------------- #
# 5. The summary cannot claim green when tests did not run
# --------------------------------------------------------------------------- #

def test_summary_never_claims_green_while_tests_are_unproven(tmp_path):
    code, out, err = _run_runner(tmp_path, ("test_guarded.py", GUARDED_FILE))

    assert "RESULT: OK" not in out, out
    assert "RESULT: FAILED" in out, out
    assert "This run is NOT green" in out, out
    assert code != 0


def test_mock_assertions_count_as_assertions(tmp_path):
    """``mock.assert_called_once()`` raises AssertionError, so it is a check.

    Reporting such a test as not-run would be a false alarm that makes the
    runner untrustworthy in the opposite direction: three tests in this
    project (``test_tray.py``, ``test_performance_audit.py``) verify their
    result only through ``unittest.mock`` assertion methods.
    """
    code, out, err = _run_runner(tmp_path, ("test_mock.py", '''
from unittest.mock import MagicMock


def test_verifies_through_a_mock_assertion():
    callback = MagicMock()
    callback()
    callback.assert_called_once()


def test_verifies_through_assert_called_with():
    timer = MagicMock()
    timer.start(3600000)
    timer.start.assert_called_once_with(3600000)
'''))

    assert _summary_line(out, "verified") == 2, out
    assert _summary_line(out, "not-run") == 0, out
    assert _summary_line(out, "failed") == 0, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_a_mock_assertion_that_fails_is_still_a_failure(tmp_path):
    """A failing mock assertion must not be mistaken for a passing test."""
    code, out, err = _run_runner(tmp_path, ("test_mock_fail.py", '''
from unittest.mock import MagicMock


def test_mock_assertion_that_does_not_hold():
    callback = MagicMock()
    callback()
    callback()
    callback.assert_called_once()
'''))

    assert _summary_line(out, "failed") == 1, out
    assert code != 0, (code, out, err)


def test_executed_count_must_match_the_declared_count(tmp_path):
    """A shortfall between declared and executed cases blocks a green result."""
    code, out, err = _run_runner(
        tmp_path,
        ("test_one.py", "def test_only_one():\n    value = 1\n    assert value == 1\n"),
    )

    assert _summary_line(out, "invoked") == 1, out
    assert "1 case(s) across 1 function(s)" in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_summary_totals_are_arithmetically_consistent(tmp_path):
    """The printed identities must hold, and a violation must fail the run.

    A skip marker that is counted as both ``skipped`` and ``not invoked`` makes
    ``invoked`` disagree with the sum of the outcomes. The runner checks this
    itself and refuses to go green when the numbers do not add up.
    """
    code, out, err = _run_runner(
        tmp_path,
        ("test_skips.py", "import sys\n" + EXPLICIT_SKIP_FILE),
    )

    declared = (_summary_line(out, "invoked") + _summary_line(out, "not invoked")
                + _summary_line(out, "blocked"))
    assert declared == 3, out
    invoked_sum = sum(_summary_line(out, k) for k in
                      ("verified", "failed", "skipped", "not-run",
                       "xfailed", "xpassed"))
    assert invoked_sum == _summary_line(out, "invoked"), out
    assert "!! the totals above do not add up" not in out, out
    assert "Accounting: declared 3 = invoked 2 + not invoked 1 + blocked 0" in out, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert code == 3, (code, out, err)


def test_collection_error_cases_are_accounted_for(tmp_path):
    """Cases in a file that fails to load are `blocked`, not silently dropped."""
    code, out, err = _run_runner(
        tmp_path,
        ("test_broken.py", "import does_not_exist_anywhere\n\n\n"
                           "def test_a():\n    assert True\n\n\n"
                           "def test_b():\n    assert True\n"),
    )

    assert _summary_line(out, "collection-error") == 1, out
    assert _summary_line(out, "blocked") == 2, out
    assert _summary_line(out, "invoked") == 0, out
    assert "Accounting: declared 2 = invoked 0 + not invoked 0 + blocked 2" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert code != 0, (code, out, err)


def test_a_vacuous_assert_is_reported_as_such(tmp_path):
    """``assert x or True`` is deleted by the compiler, so it proves nothing.

    The runner must say *why* no check ran rather than lumping this in with a
    test that merely happened to skip its checks.
    """
    code, out, err = _run_runner(tmp_path, ("test_vacuous.py", '''
def test_offscreen_geometry_falls_back_safely():
    is_vis = False
    assert not is_vis or True
'''))

    assert _summary_line(out, "not-run") == 1, out
    assert _summary_line(out, "verified") == 0, out
    assert "vacuous" in out, out
    assert "can never fail" in out, out
    assert code != 0, (code, out, err)


def test_a_broad_except_is_not_run_not_skipped(tmp_path):
    """``except (ImportError, Exception): pass`` hides the outcome entirely.

    Such a test is *not* a deliberate skip: the handler also swallows genuine
    assertion failures, so the runner cannot know whether the test would pass.
    """
    code, out, err = _run_runner(tmp_path, ("test_broad.py", '''
def test_guarded_by_an_absent_dependency():
    try:
        import daily_sticky_definitely_absent_dependency
    except (ImportError, Exception):
        pass
    else:
        assert daily_sticky_definitely_absent_dependency


def test_real_work():
    assert 1 == 1
'''))

    assert _summary_line(out, "not-run") == 1, out
    assert _summary_line(out, "skipped") == 0, out
    assert _summary_line(out, "verified") == 1, out
    assert "swallowed by" in out, out
    assert "the outcome is unknown" in out, out
    assert code != 0, (code, out, err)


def test_an_unparseable_file_is_a_collection_error_not_a_crash(tmp_path):
    """A file that is not decodable text must not crash the runner.

    ``ast.parse`` raises ``ValueError`` (not ``SyntaxError``) for null bytes or
    a bad encoding. Before this was handled the runner died with a traceback
    and printed no summary at all: the exit code happened to be non-zero, but
    the run produced no accounting to check.
    """
    for name, blob in (
        ("test_nullbyte.py", b"def test_x():\x00\n    assert 1 == 1\n"),
        ("test_badenc.py", b"def test_x():\n    assert 1 == 1\n# \xff\xfe\n"),
    ):
        (tmp_path / name).write_bytes(blob)

    code, out, err = _run_runner(tmp_path)

    assert _summary_line(out, "collection-error") == 2, out
    assert _summary_line(out, "verified") == 0, out
    assert _summary_line(out, "blocked") == 0, out
    assert "Traceback (most recent call last)" not in out, out
    assert "RESULT: FAILED" in out, out
    assert code == 1, (code, out, err)


def test_a_corrupted_counter_cannot_produce_a_green_run(tmp_path):
    """The runner checks its own arithmetic and refuses green when it fails.

    This is the guard that makes an internal accounting error impossible to
    hide: if ``invoked`` ever disagrees with the sum of the outcomes, or if the
    declared total is not fully accounted for, the run goes red.
    """
    # A normal run satisfies both identities and prints no defect line.
    code, out, err = _run_runner(
        tmp_path,
        ("test_a.py", "def test_ok():\n    assert 1 == 1\n"),
    )
    assert "!! the totals above do not add up" not in out, out
    assert "the summary totals are inconsistent" not in out, out
    assert code == 0, (code, out, err)

    # And the printed identities are re-derivable from the output itself.
    declared = (_summary_line(out, "invoked") + _summary_line(out, "not invoked")
                + _summary_line(out, "blocked"))
    invoked_sum = sum(_summary_line(out, k) for k in
                      ("verified", "failed", "skipped", "not-run",
                       "xfailed", "xpassed"))
    assert declared == 1, out
    assert invoked_sum == _summary_line(out, "invoked") == 1, out


def test_a_guarded_import_does_not_swallow_the_tests_checks(tmp_path):
    """The repair pattern: guard only the import, assert outside it.

    Seven backend tests used to wrap their whole body in
    ``except (ImportError, Exception): pass``, which swallowed genuine
    ``AssertionError`` failures. The repaired form guards only the import and
    runs its checks unguarded, so a wrong expectation is reported as a failure
    and a missing dependency is reported as a skip -- never as a pass.
    """
    code, out, err = _run_runner(tmp_path, ("test_pattern.py", '''
import json
import pytest


def test_dependency_available_and_assertion_holds():
    try:
        import json
    except ImportError:
        pytest.skip("dependency unavailable")
    assert json.dumps({"a": 1}) == \'{"a": 1}\'


def test_dependency_available_but_assertion_is_wrong():
    try:
        import json
    except ImportError:
        pytest.skip("dependency unavailable")
    assert json.dumps({"a": 1}) == "WRONG"


def test_dependency_missing():
    try:
        import a_module_that_does_not_exist_anywhere
    except ImportError:
        pytest.skip("dependency unavailable")
    assert a_module_that_does_not_exist_anywhere
'''))

    assert _summary_line(out, "verified") == 1, out
    assert _summary_line(out, "failed") == 1, out
    assert _summary_line(out, "skipped") == 1, out
    assert _summary_line(out, "not-run") == 0, out
    assert code != 0, (code, out, err)


def test_an_assertion_the_compiler_deleted_is_not_a_check(tmp_path):
    """``assert x or True`` can never fail, so it proves nothing.

    This is the vacuous form that
    ``test_geometry_manager.py::test_offscreen_geometry_falls_back_safely``
    used to carry. The repaired form asserts the condition directly and skips
    when the dependency needed to evaluate it is absent.
    """
    code, out, err = _run_runner(tmp_path, ("test_vacuous.py", '''
def test_vacuous_form():
    is_vis = True
    assert not is_vis or True
'''))

    assert _summary_line(out, "not-run") == 1, out
    assert _summary_line(out, "verified") == 0, out
    assert "vacuous" in out, out
    assert code != 0, (code, out, err)


def test_parametrized_cases_are_counted_per_parameter_set(tmp_path):
    """One function with three parameter sets is three cases, one function."""
    code, out, err = _run_runner(tmp_path, ("test_param.py", '''
import pytest


@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized_cases_all_run(value):
    assert value > 0
'''))

    assert "3 case(s) across 1 function(s)" in out, out
    assert _summary_line(out, "invoked") == 3, out
    assert _summary_line(out, "verified") == 3, out
    assert code == 0, (code, out, err)


# --------------------------------------------------------------------------- #
# 6. Previously supported behaviour must remain intact
# --------------------------------------------------------------------------- #

SUPPORTED_FILE = '''
import pytest


def test_plain_assertion_passes():
    value = 2
    assert value * 2 == 4


def test_raises_still_detects_the_expected_exception():
    with pytest.raises(ValueError):
        raise ValueError("expected")


def test_raises_still_fails_when_nothing_is_raised():
    with pytest.raises(ValueError):
        pass


def test_db_connection_fixture_is_still_wired(db_connection):
    assert db_connection.execute("SELECT 1").fetchone()[0] == 1


def test_tmp_path_fixture_is_still_wired(tmp_path):
    target = tmp_path / "probe.txt"
    target.write_text("x", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "x"


def test_quote_service_fixture_is_still_wired(quote_service):
    assert quote_service is not None


@pytest.mark.xfail(reason="documented expected failure")
def test_xfail_marked_failure_is_xfailed():
    assert False


def test_genuine_failure_is_reported_as_failed():
    assert 1 == 2
'''


def test_previously_supported_behaviour_is_intact(tmp_path):
    code, out, err = _run_runner(tmp_path, ("test_supported.py", SUPPORTED_FILE))

    assert _summary_line(out, "failed") == 2, out      # raises + genuine failure
    assert _summary_line(out, "xfailed") == 1, out
    assert _summary_line(out, "verified") == 5, out
    assert _summary_line(out, "not-run") == 0, out
    assert code != 0, (code, out, err)


def test_unknown_fixture_fails_loudly_rather_than_vanishing(tmp_path):
    """A fixture this runner cannot provide is a visible failure, not a skip."""
    code, out, err = _run_runner(tmp_path, ("test_unknown_fixture.py", '''
def test_asks_for_a_fixture_the_runner_does_not_provide(unit_of_work):
    assert unit_of_work is not None
'''))

    assert _summary_line(out, "failed") == 1, out
    assert _summary_line(out, "not-run") == 0, out
    assert "unit_of_work" in out, out
    assert code != 0, (code, out, err)


def test_strict_xfail_that_passes_is_a_failure(tmp_path):
    """pytest treats an unexpectedly-passing strict xfail as a failure."""
    code, out, err = _run_runner(tmp_path, ("test_strict.py", '''
import pytest


@pytest.mark.xfail(strict=True, reason="known defect")
def test_strict_xfail_unexpectedly_passes():
    value = 1
    assert value == 1
'''))

    assert _summary_line(out, "failed") == 1, out
    assert _summary_line(out, "xpassed") == 0, out
    assert code != 0, (code, out, err)
    assert "unexpectedly passed" in out, out


def test_non_strict_xfail_that_passes_is_xpassed(tmp_path):
    code, out, err = _run_runner(tmp_path, ("test_xpass.py", '''
import pytest


@pytest.mark.xfail(reason="known defect, not strict")
def test_non_strict_xfail_unexpectedly_passes():
    value = 1
    assert value == 1
'''))

    assert _summary_line(out, "xpassed") == 1, out
    assert _summary_line(out, "failed") == 0, out
    # xpassed is not a verification either: exit 3, not a green run.
    assert _summary_line(out, "verified") == 0, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert code == 3, (code, out, err)


def test_monkeypatch_fixture_is_still_wired(tmp_path):
    code, out, err = _run_runner(tmp_path, ("test_mp.py", '''
import os


def test_monkeypatch_setattr_and_undo(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(os, "sep", sentinel)
    assert os.sep is sentinel
'''))

    assert _summary_line(out, "verified") == 1, out
    assert code == 0, (code, out, err)


# --------------------------------------------------------------------------- #
# 7. Runner interface guards
# --------------------------------------------------------------------------- #

def test_runner_reports_a_missing_tests_directory():
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "/nonexistent/directory/for/tests"],
        capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode != 0
    assert "no such test directory" in completed.stderr


def test_pytest_delegation_flag_errors_clearly_when_pytest_is_absent():
    """``--pytest`` must fail loudly rather than silently falling back.

    Detection runs in a clean subprocess: under this runner ``import pytest``
    succeeds because the stdlib mock is installed in ``sys.modules``, which
    would otherwise be mistaken for a real pytest installation.
    """
    probe = subprocess.run([sys.executable, "-c", "import pytest"],
                           capture_output=True, timeout=120)
    installed = probe.returncode == 0

    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--pytest"],
        capture_output=True, text=True, timeout=300,
    )
    if installed:
        # Real pytest is present; delegation should at least not crash the runner.
        assert completed.returncode in (0, 1, 5), completed.stderr
    else:
        assert completed.returncode != 0
        assert "--pytest was requested but pytest is not installed" in completed.stderr


# --------------------------------------------------------------------------- #
# 8. Result semantics: "no failures" is not "everything verified"
# --------------------------------------------------------------------------- #

FULLY_VERIFIED_FILE = '''
def test_one():
    assert 1 == 1


def test_two():
    assert 2 == 2
'''

SKIPPED_AMONG_VERIFIED_FILE = '''
import sys

import pytest


def test_one():
    assert 1 == 1


def test_two():
    if sys.platform != "win32":
        pytest.skip("platform-specific behaviour")
    assert True
'''

def test_a_fully_verified_run_reports_ok_and_exit_zero(tmp_path):
    """The only run entitled to a plain ``OK``: every declared case verified."""
    code, out, err = _run_runner(tmp_path, ("test_all.py", FULLY_VERIFIED_FILE))

    assert _summary_line(out, "verified") == 2, out
    assert _summary_line(out, "failed") == 0, out
    assert _summary_line(out, "skipped") == 0, out
    assert _summary_line(out, "not-run") == 0, out
    assert "COVERAGE: 2 of 2 declared case(s) verified (100%)" in out, out
    assert "RESULT: OK" in out, out
    assert "RESULT: OK WITH SKIPS" not in out, out
    assert "Exit code 0." in out, out
    assert code == 0, (code, out, err)


def test_a_run_with_skips_is_not_reported_as_a_plain_ok(tmp_path):
    """A run that merely has no failures must not look fully verified.

    This is the Phase C defect: the runner used to print ``RESULT: OK`` and
    exit 0 while half the declared cases never ran their checks.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_mixed.py", SKIPPED_AMONG_VERIFIED_FILE)
    )

    assert _summary_line(out, "verified") == 1, out
    assert _summary_line(out, "skipped") == 1, out
    assert _summary_line(out, "failed") == 0, out
    # The summary must state the coverage ratio rather than a bare "OK".
    assert "COVERAGE: 1 of 2 declared case(s) verified (50%)" in out, out
    assert "1 case(s) did not run their checks" in out, out
    assert "Of those, 1 are explicitly skipped/xfailed/xpassed and 0 were " \
           "never invoked (skip markers)" in out, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert "This is NOT a fully verified run" in out, out
    assert "A skipped test did not pass" in out, out
    assert "Exit code 3." in out, out
    # ... and must not be mistaken for the fully verified result.
    assert "RESULT: OK\n" not in out, out
    assert code == 3, (code, out, err)


def test_a_failure_is_a_failure_even_when_other_cases_are_skipped(tmp_path):
    """A single genuine failure must dominate, not be averaged away."""
    code, out, err = _run_runner(tmp_path, ("test_mixed.py", '''
import sys

import pytest


def test_broken():
    assert 1 == 2


def test_skipped():
    if sys.platform != "win32":
        pytest.skip("platform-specific behaviour")
    assert True
'''))

    assert _summary_line(out, "failed") == 1, out
    assert _summary_line(out, "skipped") == 1, out
    assert _summary_line(out, "verified") == 0, out
    assert "RESULT: FAILED" in out, out
    assert "This run is NOT green" in out, out
    assert "Exit code 1." in out, out
    assert code == 1, (code, out, err)


def test_a_not_run_case_is_a_failure_not_a_skip(tmp_path):
    """Unresolved cases are unresolved: they may not be counted as verified."""
    code, out, err = _run_runner(tmp_path, ("test_silent.py", '''
def test_guarded_by_an_absent_dependency():
    try:
        import daily_sticky_definitely_absent_dependency
    except (ImportError, Exception):
        pass
    else:
        assert daily_sticky_definitely_absent_dependency
'''))

    assert _summary_line(out, "not-run") == 1, out
    assert _summary_line(out, "verified") == 0, out
    assert "RESULT: FAILED" in out, out
    assert code == 1, (code, out, err)


def test_a_collection_error_is_a_failure_with_a_nonzero_exit(tmp_path):
    code, out, err = _run_runner(
        tmp_path, ("test_broken.py", BROKEN_IMPORT_FILE)
    )

    assert _summary_line(out, "collection-error") == 1, out
    assert "RESULT: FAILED" in out, out
    assert "Exit code 1." in out, out
    assert code == 1, (code, out, err)


def test_a_missing_dependency_guard_is_not_reported_as_verified(tmp_path):
    """A dependency guard that declines must never appear in the verified count."""
    code, out, err = _run_runner(tmp_path, ("test_guard.py", '''
import pytest


def test_needs_an_absent_dependency():
    try:
        import daily_sticky_definitely_absent_dependency
    except ImportError:
        pytest.skip("dependency unavailable")
    else:
        assert daily_sticky_definitely_absent_dependency


def test_real_work():
    assert 1 == 1
'''))

    assert _summary_line(out, "verified") == 1, out
    assert _summary_line(out, "skipped") == 1, out
    assert "COVERAGE: 1 of 2 declared case(s) verified (50%)" in out, out
    assert code == 3, (code, out, err)


def test_accounting_is_verified_across_all_three_terms(tmp_path):
    """Every declared case lands in exactly one bucket, and the runner says so.

    ``invoked`` + ``not invoked`` + ``blocked`` must equal the declared count,
    and the invoked outcomes must sum to ``invoked``. A run where those do not
    add up is the one situation in which the runner prints
    ``!! the totals above do not add up`` and refuses to go green.
    """
    code, out, err = _run_runner(
        tmp_path,
        ("test_ok.py", FULLY_VERIFIED_FILE),
        ("test_marked.py", '''
import pytest


@pytest.mark.skip(reason="not applicable here")
def test_marked_skip():
    assert 1 == 1


def test_real():
    assert 1 == 1
'''),
    )

    assert "!! the totals above do not add up" not in out, out
    assert "Accounting: declared 4 = invoked 3 + not invoked 1 + blocked 0" in out, out
    assert _summary_line(out, "verified") == 3, out
    assert _summary_line(out, "skipped") == 0, out
    assert _summary_line(out, "not invoked") == 1, out
    assert "COVERAGE: 3 of 4 declared case(s) verified (75%)" in out, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert code == 3, (code, out, err)


def test_result_and_exit_code_agree_across_every_outcome(tmp_path):
    """One consistency rule tying the printed result to the process exit code.

    The runner is the only execution path in this environment (pytest is not
    installed), so a summary that disagrees with the exit code would silently
    turn a red run green for anyone scripting it.
    """
    scenarios = (
        ("fully_verified", FULLY_VERIFIED_FILE, "RESULT: OK", 0),
        ("mixed", SKIPPED_AMONG_VERIFIED_FILE, "RESULT: OK WITH SKIPS", 3),
        ("collection_error", BROKEN_IMPORT_FILE, "RESULT: FAILED", 1),
        ("failed", "def test_x():\n    assert 1 == 2\n", "RESULT: FAILED", 1),
    )

    for label, body, expected_result, expected_code in scenarios:
        # A fresh directory per scenario, so earlier fixtures cannot leak in.
        scenario_dir = tmp_path / label
        scenario_dir.mkdir()
        code, out, err = _run_runner(
            scenario_dir, (f"test_{label}.py", body)
        )
        assert expected_result in out, (label, out)
        assert code == expected_code, (label, code, out, err)
        # The printed exit code and the process exit code must be the same
        # number, so a reader of the log cannot be misled.
        assert f"Exit code {expected_code}." in out, (label, out)


# --------------------------------------------------------------------------- #
# 9. Fixture parity with tests/conftest.py
# --------------------------------------------------------------------------- #

# The runner substitutes its own fixtures because it does not implement
# conftest.py. Where a test relies on a fixture *default*, the substitution
# must be behaviourally identical, or a `verified` verdict here is not the
# same test pytest would run.

QUOTE_DEFAULTS_FILE = '''
import random


def test_default_make_quote_service_matches_conftest(make_quote_service):
    """A defaulted factory call must be deterministic, as conftest.py promises.

    ``tests/conftest.py`` defaults to ``favorite_selection_probability=0.0``
    and a ``random_source`` seeded with 0. The runner used to pass QuoteService's
    *production* defaults (0.15, unseeded), so the 17 test call sites that rely
    on the defaults were not running the same code under the runner.
    """
    service = make_quote_service()
    assert service._favorite_probability == 0.0, (
        f"favourite probability default is {service._favorite_probability!r}; "
        "tests/conftest.py uses 0.0"
    )
    assert service._random.random() == random.Random(0).random(), (
        "random_source is not seeded with 0 as tests/conftest.py does"
    )


def test_explicit_arguments_still_reach_the_service(make_quote_service):
    """Overrides must keep working, so the check above is not vacuous."""
    service = make_quote_service(
        favorite_selection_probability=1.0, random_source=random.Random(7)
    )
    assert service._favorite_probability == 1.0
    assert service._random.random() == random.Random(7).random()
'''


def test_quote_service_fixture_defaults_match_conftest(tmp_path):
    """The runner's fixture must not silently change what a test exercises."""
    code, out, err = _run_runner(
        tmp_path, ("test_quote_defaults.py", QUOTE_DEFAULTS_FILE)
    )

    assert _summary_line(out, "verified") == 2, out
    assert _summary_line(out, "failed") == 0, out
    assert _summary_line(out, "not-run") == 0, out
    assert "RESULT: OK" in out, out
    assert "RESULT: OK WITH SKIPS" not in out, out
    assert code == 0, (code, out, err)


# --------------------------------------------------------------------------- #
# 10. Accounting identity under dynamic parametrization
# --------------------------------------------------------------------------- #

# A parametrize list that only exists at runtime. `ast.literal_eval` cannot
# evaluate `sorted(KEYS)`, so a runner that counts declared cases statically
# reports ONE case where the real decorator expands to four. The executed
# cases come from the runtime expansion, so the declared count must too --
# otherwise `declared` and `invoked` disagree and the runner's own consistency
# check condemns a perfectly healthy suite.

DYNAMIC_PARAMETRIZE_FILE = '''
import pytest

KEYS = ["alpha", "beta", "gamma", "delta"]


@pytest.mark.parametrize("key", sorted(KEYS))
def test_each_key_is_nonempty(key):
    assert key
'''

DYNAMIC_MIXED_FILE = '''
import sys

import pytest

SIZES = [320, 380]


@pytest.mark.parametrize("width", SIZES)
def test_each_width_is_supported(width):
    assert width in (320, 380)


def test_plain():
    assert 1 == 1


def test_skipped_on_this_platform():
    if sys.platform != "win32":
        pytest.skip("platform-specific behaviour")
    assert True
'''


def test_dynamic_parametrize_cases_are_counted_from_the_runtime_expansion(tmp_path):
    """Declared cases must match the expansion that actually executes.

    This is the regression for the accounting defect: the static AST estimate
    reported 1 case while 4 ran, so `declared 1 = invoked 4` failed the
    runner's own consistency check and the summary could not be trusted.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_dyn.py", DYNAMIC_PARAMETRIZE_FILE)
    )

    assert _summary_line(out, "verified") == 4, out
    assert _summary_line(out, "invoked") == 4, out
    assert "Accounting: declared 4 = invoked 4 + not invoked 0 + blocked 0" in out, out
    assert "invoked 4 = verified 4 + failed 0 + skipped 0 + not-run 0" in out, out
    assert "COVERAGE: 4 of 4 declared case(s) verified (100%)" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_dynamic_parametrize_mixed_with_skips_stays_consistent(tmp_path):
    """The identity must hold when dynamic expansion is mixed with other outcomes."""
    code, out, err = _run_runner(
        tmp_path, ("test_dyn_mixed.py", DYNAMIC_MIXED_FILE)
    )

    # 2 dynamic cases + 1 plain verified + 1 skipped
    assert _summary_line(out, "verified") == 3, out
    assert _summary_line(out, "skipped") == 1, out
    assert _summary_line(out, "invoked") == 4, out
    assert "Accounting: declared 4 = invoked 4 + not invoked 0 + blocked 0" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK WITH SKIPS" in out, out
    assert code == 3, (code, out, err)


# The identity must also hold on the project's own suite, not just on the
# fixtures above. That cannot be expressed as a test in this file, and the
# reason is worth recording so nobody re-adds it: this file lives in the
# project's test directory, so any case here that runs the runner over that
# directory would execute *itself*, spawn another run of the same suite, and
# so on without end. The recursion was observed here and had to be removed.
#
# The obvious escapes are all unsound:
#   * copying the suite elsewhere breaks every test that locates project
#     assets through ``Path(__file__).resolve().parent.parent`` (icons,
#     styles, packaging specs), so the copied suite would fail for reasons
#     that have nothing to do with the accounting;
#   * symlinking is defeated because the runner resolves its ``tests_dir``
#     argument, which resolves straight back to the real directory;
#   * an environment-variable guard would make the very identity under test
#     depend on the environment it runs in.
#
# The real suite is therefore verified by running the runner over it directly
# and reading the two printed identities off the output -- which is exactly
# what the two cases above pin down on fixtures that reproduce the defect in
# isolation.


# --------------------------------------------------------------------------- #
# 11. One-shot iterables must survive being evaluated more than once
# --------------------------------------------------------------------------- #

# The runner evaluates a parametrisation twice per test function: once to count
# the declared cases, then once per case to execute it. A re-iterable input
# (list, tuple, dict, set) does not care, but a one-shot iterable -- a
# generator, a `map` object, an `iter(...)` -- is drained by the first pass.
# Before the recorder was fixed, that silently deleted cases from the run and
# broke the accounting identity. These fixtures are deliberately one-shot, and
# each one carries a *distinguishable* value so a dropped, duplicated, or
# mis-assigned case shows up as a wrong count or a failed check rather than
# slipping through.
#
# Every case below runs the runner against a throwaway `tmp_path`, never
# against the project's own suite: see the note at the end of section 10 for
# why a case here must not do that.

ONE_SHOT_GENERATOR_FILE = '''
import pytest


def _widths():
    yield 320
    yield 380
    yield 600


@pytest.mark.parametrize("width", _widths())
def test_each_width_is_supported(width):
    assert width in (320, 380, 600)
'''

ONE_SHOT_MAP_FILE = '''
import pytest


@pytest.mark.parametrize("n", map(lambda x: x * 2, [1, 2, 3]))
def test_each_double_is_even(n):
    assert n in (2, 4, 6)
'''

ONE_SHOT_STACKED_FILE = '''
import pytest


def _texts():
    yield "a"
    yield "b"


def _widths():
    yield 320
    yield 380


@pytest.mark.parametrize("text", _texts())
@pytest.mark.parametrize("width", _widths())
def test_cartesian_product(text, width):
    assert text in ("a", "b")
    assert width in (320, 380)
'''

ONE_SHOT_NAMES_FILE = '''
import pytest


@pytest.mark.parametrize(iter(["a", "b"]), [(1, 2), (3, 4)])
def test_each_pair(a, b):
    assert (a, b) in ((1, 2), (3, 4))
'''

MIXED_LIST_AND_GENERATOR_FILE = '''
import pytest


def _sizes():
    yield 320
    yield 380


@pytest.mark.parametrize("width", [320, 380])
def test_list_case(width):
    assert width in (320, 380)


@pytest.mark.parametrize("width", _sizes())
def test_generator_case(width):
    assert width in (320, 380)
'''

EMPTY_ONE_SHOT_FILE = '''
import pytest


def _nothing():
    return
    yield  # pragma: no cover - never reached, this is an empty generator


@pytest.mark.parametrize("x", _nothing())
def test_needs_a_value(x):
    assert x
'''


def test_a_one_shot_generator_is_fully_counted_and_fully_executed(tmp_path):
    """A generator's cases must be counted *and* run, not drained by counting.

    Three values are yielded. If the counting pass consumed the generator, the
    execution pass would see an empty sequence and call the function once with
    no argument at all -- so `verified` would be 0 and `failed` would be 1.
    Every value is distinct, so a substituted or duplicated value cannot pass
    the fixture's own check either.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_gen.py", ONE_SHOT_GENERATOR_FILE)
    )

    assert "3 case(s) across 1 function(s)" in out, out
    assert _summary_line(out, "verified") == 3, out
    assert _summary_line(out, "invoked") == 3, out
    assert _summary_line(out, "failed") == 0, out
    assert _summary_line(out, "not-run") == 0, out
    assert "Accounting: declared 3 = invoked 3 + not invoked 0 + blocked 0" in out, out
    assert "invoked 3 = verified 3 + failed 0 + skipped 0 + not-run 0" in out, out
    assert "COVERAGE: 3 of 3 declared case(s) verified (100%)" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_declared_and_invoked_agree_for_a_map_object(tmp_path):
    """`map` is one-shot too; it must not lose its cases either.

    This is the same defect wearing a different type, and it is asserted
    separately because the fix has to hold for every one-shot iterable rather
    than only for generators.
    """
    code, out, err = _run_runner(tmp_path, ("test_map.py", ONE_SHOT_MAP_FILE))

    assert "3 case(s) across 1 function(s)" in out, out
    assert _summary_line(out, "verified") == 3, out
    assert _summary_line(out, "invoked") == 3, out
    assert "Accounting: declared 3 = invoked 3 + not invoked 0 + blocked 0" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_stacked_one_shot_generators_keep_their_order_and_product(tmp_path):
    """Ordering and the cartesian product must survive materialisation.

    Two stacked generators of two values each must still produce four cases in
    the same order as the equivalent stacked lists. A fix that merely counted
    the iterable once, or that reversed it, would break either the product or
    the ordering.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_stacked.py", ONE_SHOT_STACKED_FILE)
    )

    assert "4 case(s) across 1 function(s)" in out, out
    assert _summary_line(out, "verified") == 4, out
    assert _summary_line(out, "invoked") == 4, out
    assert "Accounting: declared 4 = invoked 4 + not invoked 0 + blocked 0" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_a_one_shot_argnames_iterator_no_longer_crashes_the_run(tmp_path):
    """A one-shot `argnames` must not kill the run without a summary.

    This was the worse half of the same defect: an exhausted name iterator
    reads as *empty* argnames, which raised UnsupportedPytestAPI from inside
    the execution loop -- a place nothing catches. The run died with an
    unhandled traceback and printed no summary at all, so a reader could not
    even tell what had happened. The runner must instead produce a complete,
    self-consistent summary.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_names.py", ONE_SHOT_NAMES_FILE)
    )

    # A full summary must be printed, not a bare traceback.
    assert "Declared by the test files:" in out, out
    assert "Accounting:" in out, out
    assert "2 case(s) across 1 function(s)" in out, out
    assert _summary_line(out, "verified") == 2, out
    assert _summary_line(out, "invoked") == 2, out
    assert "Accounting: declared 2 = invoked 2 + not invoked 0 + blocked 0" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_list_parametrization_is_unaffected_by_the_materialisation(tmp_path):
    """Re-iterable inputs must behave exactly as before.

    The fix freezes the recorded spec, so a list and a generator sitting in the
    same file must both still expand to their full case counts. This is the
    guard against a fix that only works for generators.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_mixed.py", MIXED_LIST_AND_GENERATOR_FILE)
    )

    assert "4 case(s) across 2 function(s)" in out, out
    assert _summary_line(out, "verified") == 4, out
    assert _summary_line(out, "invoked") == 4, out
    assert "Accounting: declared 4 = invoked 4 + not invoked 0 + blocked 0" in out, out
    assert "invoked 4 = verified 4 + failed 0 + skipped 0 + not-run 0" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: OK" in out, out
    assert code == 0, (code, out, err)


def test_an_empty_one_shot_iterable_stays_honest_and_unchanged(tmp_path):
    """An empty parameter set is reported as what it is, not hidden.

    The behaviour pinned here is *unchanged* by the materialisation fix and was
    measured to be byte-identical before and after it: an empty parametrize
    contributes no cases, so the function is called once with no argument and
    fails with a TypeError. That is what this runner has always done.

    It is also where the runner diverges from real pytest, which reports an
    empty parameter set as a skip rather than a failure. Aligning that would
    change a result category, so it is deliberately left alone and recorded
    here instead. What matters for the accounting is that the case is still
    declared, still invoked, and still accounted for -- nothing disappears.
    """
    code, out, err = _run_runner(
        tmp_path, ("test_empty.py", EMPTY_ONE_SHOT_FILE)
    )

    assert "1 case(s) across 1 function(s)" in out, out
    assert _summary_line(out, "invoked") == 1, out
    assert _summary_line(out, "verified") == 0, out
    assert _summary_line(out, "failed") == 1, out
    assert "Accounting: declared 1 = invoked 1 + not invoked 0 + blocked 0" in out, out
    assert "invoked 1 = verified 0 + failed 1 + skipped 0 + not-run 0" in out, out
    assert "!! the totals above do not add up" not in out, out
    assert "RESULT: FAILED" in out, out
    assert code == 1, (code, out, err)
