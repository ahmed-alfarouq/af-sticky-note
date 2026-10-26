#!/usr/bin/env python3
"""Standalone test runner for the Daily Sticky backend tests.

PURPOSE
    Runs every ``test_*.py`` module under ``tests/`` using only the standard
    library, so the suite works where installing ``pytest`` or ``PySide6`` is
    impossible (fresh sandboxes, the CI backend job, PEP 668 locked-down hosts).

    If real ``pytest`` *is* installed, prefer it: ``python -m pytest tests/``,
    or pass ``--pytest`` here. This script is the dependency-light fallback,
    not a replacement for pytest.

HONESTY CONTRACT
    This runner never reports success unless it can account for every test it
    intended to run:

    * A test file that fails to import is a **collection error**. It is named
      in the output, counted, and forces a non-zero exit status. It is never
      silently skipped.
    * A test that finishes **without executing a verifiable check** is never
      counted as a pass. It is classified as either ``skipped`` (it
      *deliberately* declined -- a dependency or platform guard that actually
      fired) or ``not-run`` (the outcome is unknown, for example because a
      broad ``except Exception: pass`` swallowed something).
    * An unsupported ``pytest`` API raises :class:`UnsupportedPytestAPI` at
      import time, so the file becomes a visible collection error instead of
      disappearing from the run.
    * The summary prints every count *with its own definition* and the two
      accounting identities that tie them together, and refuses to report
      success if they do not add up:

          declared = invoked + not invoked + blocked
          invoked  = verified + failed + skipped + not-run
                     + xfailed + xpassed

    * Exit status is 0 only when nothing failed, nothing failed to load, and
      every invoked case was verified or deliberately skipped.

OUTCOME VOCABULARY
    verified      invoked, and at least one check executed
    failed        invoked, and it raised
    skipped       invoked, and it deliberately declined (dependency or
                  platform guard, or an explicit ``pytest.skip()``)
    not-run       invoked, but no check could be verified -- outcome unknown
    xfailed       a declared expected failure (``@pytest.mark.xfail``)
    xpassed       an xfail-marked test that unexpectedly succeeded
    collection-error   a whole file that could not be parsed or imported

    ``invoked`` means the test function was actually called. A skip *marker*
    declines a test without calling it, so those cases are reported as
    ``not invoked`` instead of ``skipped`` -- the two categories never overlap.

    These words are deliberately narrow:

    * ``verified`` means the runner observed a recognised check execute without
      raising. It does **not** prove the check validates the intended
      application behaviour.
    * ``skipped`` means a test deliberately declined to execute its checks for
      a recorded reason. It does **not** mean the test passed.
    * ``not-run`` means the runner cannot establish a trustworthy outcome.

RESULT AND EXIT CODES
    A run with no failures is not the same as a run in which every declared
    case was verified, and the exit status must not let the two be confused.

    ``RESULT: OK``            every declared case was verified.  exit 0
    ``RESULT: OK WITH SKIPS`` no failures, but some cases did not run their
                              checks (skipped, xfailed, xpassed, not invoked).
                              This is NOT a fully verified run.  exit 3
    ``RESULT: FAILED``        failures, not-run cases, collection errors,
                              internal errors, or inconsistent accounting.
                              exit 1
    (bad arguments, a missing directory, or pytest absent for ``--pytest``
     exit 2 before any test runs)

WHAT COUNTS AS A CHECK
    ``assert`` statements the compiler kept (``assert True`` is optimised away
    and correctly counts as nothing), successful ``pytest.raises`` blocks, and
    ``unittest.mock`` assertion methods such as ``assert_called_once()``, which
    raise ``AssertionError`` when they fail. Only checks that live in the test
    files are credited to a test: without that restriction an ``import``
    performed inside a test would trace ``importlib`` and any ``assert`` buried
    there would be credited to the test.

LIMITATIONS OF THIS RUNNER
    * It is not pytest. It implements the subset listed below and raises
      :class:`UnsupportedPytestAPI` for anything else rather than guessing.
    * It cannot tell *why* a broad ``except Exception: pass`` fired, only that
      it did; such tests are reported as ``not-run`` with the handler quoted.
    * It cannot install PySide6, so Qt-dependent tests can only be reported as
      ``skipped`` here. That is an environment fact, not a verdict: 47 of the
      currently skipped cases import PySide6 at module level and decline when
      the import fails, and 1 (``test_real_windows_desktop_attachment``) is
      guarded on ``sys.platform == 'win32'`` and would be skipped even on a
      Linux host that has PySide6.
    * It does not read ``conftest.py``. It supplies its own fixtures instead,
      so it never sees fixture *scopes*, plugins, or ``-k``/``-m`` selection.
      Where any of those are needed, run real pytest. The substituted fixtures
      must stay behaviourally identical to ``tests/conftest.py`` -- see
      ``make_quote_service`` in :func:`main`, whose defaults deliberately match
      the conftest ones rather than ``QuoteService``'s production defaults.

RUNNING THE Qt TESTS
    The Qt half of the suite needs a host that has both PySide6 and a usable Qt
    platform. The runner does not set ``QT_QPA_PLATFORM``, so on a headless
    Linux host ``QApplication([])`` would fail even with PySide6 installed;
    export ``QT_QPA_PLATFORM=offscreen`` there. From a checkout with the
    project's own requirements installed:

        python -m venv .venv && . .venv/bin/activate      # Windows: .venv\\Scripts\\activate
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        QT_QPA_PLATFORM=offscreen python scripts/run_all_backend_tests.py

    On Windows a display is always available and no platform override is
    needed. ``python scripts/run_all_backend_tests.py --pytest`` delegates to
    real pytest once it is installed.

SUPPORTED PYTEST SUBSET
    ``pytest.raises``, ``pytest.fixture``, ``pytest.skip``, ``pytest.xfail``,
    ``pytest.fail``, ``pytest.mark.parametrize`` (stackable, cartesian
    product), ``pytest.mark.xfail`` (``strict`` honoured), ``pytest.mark.skip``
    and ``pytest.mark.skipif``. Anything else raises
    :class:`UnsupportedPytestAPI` naming the missing feature, rather than being
    silently ignored.

USAGE
    python3 scripts/run_all_backend_tests.py [TESTS_DIR] [--pytest]
"""
from __future__ import annotations

import argparse
import ast
import dis
import importlib.util
import inspect
import random
import subprocess
import sys
import tempfile
import traceback
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Make the application importable when the runner is invoked from anywhere.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --------------------------------------------------------------------------- #
# Outcome vocabulary
#
# Every count the runner prints is defined here, and the definitions are
# printed alongside the numbers so that a reader never has to guess whether a
# case was invoked, verified, or merely declared.
#
#   invoked    the test function was actually called
#   verified   invoked, and at least one check executed (see AssertionProbe)
#   failed     invoked, and it raised
#   skipped    invoked, and it deliberately declined (a dependency or platform
#              guard that actually fired, or an explicit pytest.skip())
#   not-run    invoked, it completed, but no check could be verified and no
#              deliberate guard explains it -- the outcome is UNKNOWN
#   xfailed    an expected failure, as declared by @pytest.mark.xfail
#   xpassed    an xfail-marked test that unexpectedly succeeded
#   collection-error   a whole file that could not be parsed or imported
#
# ``invoked`` and ``skipped`` are different things: a skip marker declines a
# test without ever calling it. Those cases are reported as ``not invoked`` so
# that the two totals never overlap.
# --------------------------------------------------------------------------- #

VERIFIED = "verified"
FAILED = "failed"
SKIPPED = "skipped"
XFAILED = "xfailed"
XPASSED = "xpassed"
NOT_RUN = "not-run"
COLLECTION_ERROR = "collection-error"

#: Outcomes that mean "this test proved nothing".
UNPROVEN = (NOT_RUN, COLLECTION_ERROR)

#: Explicit, explained exclusions. They are reported but do not by themselves
#: make the run red. ``not-run`` is deliberately absent: a silent early return
#: is not an explanation.
EXPLAINED_EXCLUSIONS = (SKIPPED, XFAILED, XPASSED)

#: Outcomes that partition the *invoked* cases.
_INVOKED_OUTCOMES = (VERIFIED, FAILED, SKIPPED, NOT_RUN, XFAILED, XPASSED)

#: Exit statuses. The distinction that matters most is between a run in which
#: every declared case was verified, and one that merely has no failures.
EXIT_VERIFIED = 0        # every declared case was verified
EXIT_FAILED = 1          # failures, not-run, collection errors, bad accounting
EXIT_USAGE = 2           # bad arguments, missing directory, pytest absent
EXIT_INCOMPLETE = 3      # no failures, but some cases did not run

_OUTCOME_ORDER = (VERIFIED, FAILED, SKIPPED, XFAILED, XPASSED, NOT_RUN)
_PROGRESS = {
    VERIFIED: ".", FAILED: "F", SKIPPED: "s", XFAILED: "x",
    XPASSED: "X", NOT_RUN: "n", COLLECTION_ERROR: "E",
}


# --------------------------------------------------------------------------- #
# Control-flow exceptions mirroring the supported pytest API
# --------------------------------------------------------------------------- #

class UnsupportedPytestAPI(Exception):
    """A test file used a pytest feature this runner cannot honour."""


class Skipped(Exception):
    """``pytest.skip()`` or ``@pytest.mark.skip``."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(reason)
        self.reason = reason


class XFailed(Exception):
    """``pytest.xfail()``."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(reason)
        self.reason = reason


class UnsupportedFixture(Exception):
    """A test asks for a fixture this runner does not provide."""


# --------------------------------------------------------------------------- #
# Assertion execution probe
# --------------------------------------------------------------------------- #

class AssertionProbe:
    """Counts ``assert`` statements actually executed during a test call.

    ``sys.settrace`` reports line events but cannot tell an executed assert
    from any other line. The compiler, however, emits a ``LOAD_ASSERTION_ERROR``
    opcode for every real check (``assert True`` is optimised away entirely, so
    it correctly counts as *no* assertion). Recording those line numbers per
    code object and matching them against ``line`` events gives an exact count.

    Frames below the test function are traced too, so asserts delegated to a
    helper still count. Only the calling thread is traced, which is sufficient:
    a test body always runs on the thread that called it.

    ``allowed`` restricts counting to code objects that live in the test files.
    Without it, an ``import`` performed inside a test would trace the whole
    import machinery and any ``assert`` buried in ``importlib`` would be
    credited to the test — exactly the kind of false pass this runner exists
    to prevent.

    ``mock_checks`` counts calls to ``unittest.mock``'s assertion methods.
    ``mock.assert_called_once()`` raises ``AssertionError`` when it fails, so a
    test that verifies its result that way *has* asserted something and must
    not be reported as not-run.

    Two further pieces of evidence are collected so that a test which proves
    nothing can be *explained* rather than merely counted:

    ``exit_line``
        the source line the test function returned from. A return from inside
        a dependency or platform guard is a deliberate decline; a return from
        anywhere else is not.
    ``guard_triggered``
        True when a helper named ``_skip*``/``_require*``/``_needs*`` defined in
        the test files returned a truthy value during the call. That is direct
        runtime evidence that the test chose not to run, as opposed to a guess
        based on the shape of the code.
    """

    #: Assertion helpers provided by ``unittest.mock``.
    MOCK_ASSERT_NAMES = frozenset({
        "assert_called_with", "assert_called_once_with", "assert_called_once",
        "assert_called", "assert_any_call", "assert_has_calls",
        "assert_not_called",
    })

    #: Helpers a test file may use to decline when a dependency is missing.
    GUARD_NAME_PREFIXES = ("_skip", "_require", "_needs")

    def __init__(self, allowed=(), target_code=None) -> None:
        self._assert_lines: dict = {}
        self._depth = 0
        self.executed = 0
        self.mock_checks = 0
        self.exit_line = None
        self.guard_triggered = False
        self._allowed = frozenset(allowed)
        self._target_code = target_code

    def _lines_for(self, code) -> frozenset:
        cached = self._assert_lines.get(code)
        if cached is None:
            cached = frozenset(
                ins.positions.lineno
                for ins in dis.get_instructions(code)
                if ins.opname == "LOAD_ASSERTION_ERROR"
            )
            self._assert_lines[code] = cached
        return cached

    def __call__(self, frame, event, arg):
        code = frame.f_code
        if event == "call":
            self._depth += 1
            name = code.co_name
            if name in self.MOCK_ASSERT_NAMES or (
                name.startswith("assert_")
                and code.co_filename in self._allowed
            ):
                self.mock_checks += 1
            return self
        if event == "return":
            self._depth -= 1
            if code is self._target_code:
                self.exit_line = frame.f_lineno
            # `arg` is the return value. Some code returns NotImplemented,
            # which must never be used in a boolean context.
            if (code.co_filename in self._allowed
                    and code.co_name.startswith(self.GUARD_NAME_PREFIXES)
                    and arg is not None and arg is not NotImplemented
                    and bool(arg)):
                self.guard_triggered = True
            return self
        if event == "line" and self._depth >= 1:
            if code.co_filename in self._allowed:
                if frame.f_lineno in self._lines_for(code):
                    self.executed += 1
        return self


# --------------------------------------------------------------------------- #
# Minimal pytest stand-in
# --------------------------------------------------------------------------- #

class Raises:
    """``pytest.raises`` context manager.

    A successful ``pytest.raises`` block *is* an assertion, even though it
    contains no ``assert`` statement. Each one that actually catches the
    expected exception increments :attr:`successful_checks` so the assertion
    probe does not misreport such a test as having proved nothing.
    """

    #: Running total of ``pytest.raises`` blocks that caught what they expected.
    successful_checks = 0

    def __init__(self, expected_exc) -> None:
        self.expected_exc = expected_exc

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(
                f"Expected {self.expected_exc.__name__} but no exception was raised"
            )
        if issubclass(exc_type, self.expected_exc):
            Raises.successful_checks += 1
            return True
        return False


class Mark:
    """``pytest.mark``: the documented subset, loud failure on everything else."""

    @staticmethod
    def parametrize(argnames, argvalues, **_kwargs):
        """Record a parametrisation; the runner expands it after import."""
        def decorator(fn):
            specs = getattr(fn, "_runner_parametrize", [])
            specs.append((argnames, argvalues))
            fn._runner_parametrize = specs
            return fn
        return decorator

    @staticmethod
    def xfail(reason: str = "", strict: bool = False, **_kwargs):
        def decorator(fn):
            fn._runner_xfail = (reason, bool(strict))
            return fn
        return decorator

    @staticmethod
    def skip(reason: str = "", **_kwargs):
        def decorator(fn):
            fn._runner_skip = reason
            return fn
        return decorator

    @staticmethod
    def skipif(condition, reason: str = "", **_kwargs):
        def decorator(fn):
            if condition:
                fn._runner_skip = reason or "skipif condition was true"
            return fn
        return decorator

    def __getattr__(self, name):
        raise UnsupportedPytestAPI(
            f"pytest.mark.{name} is not supported by scripts/run_all_backend_tests.py. "
            "Add it to the documented subset in that file's docstring, or run the "
            "suite with real pytest (python -m pytest tests/)."
        )


class PytestMock(types.ModuleType):
    """The subset of ``pytest`` this runner implements."""

    def __init__(self) -> None:
        super().__init__("pytest")
        self.raises = Raises
        self.mark = Mark()

    @staticmethod
    def fixture(func=None, *_args, **_kwargs):
        return func if func else (lambda f: f)

    @staticmethod
    def skip(reason: str = ""):
        raise Skipped(reason)

    @staticmethod
    def xfail(reason: str = ""):
        raise XFailed(reason)

    @staticmethod
    def fail(reason: str = ""):
        raise AssertionError(reason)

    def __getattr__(self, name):
        raise UnsupportedPytestAPI(
            f"pytest.{name} is not supported by scripts/run_all_backend_tests.py. "
            "Add it to the documented subset in that file's docstring, or run the "
            "suite with real pytest (python -m pytest tests/)."
        )


class MonkeyPatch:
    def __init__(self):
        self._undo = []

    def setattr(self, target, name, value):
        old_val = getattr(target, name)
        self._undo.append((target, name, old_val))
        setattr(target, name, value)

    def finish(self):
        for target, name, old_val in reversed(self._undo):
            setattr(target, name, old_val)
        self._undo.clear()


def install_pytest_mock() -> None:
    sys.modules["pytest"] = PytestMock()


# --------------------------------------------------------------------------- #
# Static intent: what the test files say they contain
# --------------------------------------------------------------------------- #

def _parametrize_size(dec: ast.Call) -> int:
    """Number of cases a ``pytest.mark.parametrize`` decorator contributes.

    This is only a *fallback* estimate. ``ast.literal_eval`` cannot evaluate an
    argument list that is computed at runtime -- ``sorted(GLYPHS)``, a
    module-level constant, a comprehension -- so for those it returns 1 and
    under-counts. The authoritative count comes from :func:`_expand_parametrised`
    on the loaded module, which sees the real decorator; see the correction in
    :func:`main`. Keeping this estimate is what lets a file that cannot be
    imported still be accounted for.
    """
    if len(dec.args) < 2:
        return 1
    try:
        value = ast.literal_eval(dec.args[1])
    except Exception:
        return 1  # computed at runtime; the loaded module gives the real count
    return max(1, len(value))


def _is_parametrize(dec: ast.AST) -> bool:
    if not isinstance(dec, ast.Call):
        return False
    func = dec.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "parametrize"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "mark"
    )


def _declared_test_functions(tree: ast.Module):
    """Test functions pytest would collect: module level, or methods of a class.

    Closures and helper functions named ``test_*`` are deliberately excluded,
    so the count matches what a real collector would see.
    """
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            yield node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name.startswith("test_"):
                    yield sub


def _function_nodes(path: Path) -> dict:
    """Map test-function name -> ``ast.FunctionDef`` for one test file.

    Used only to *explain* an early exit. The outcome of a case always comes
    from running it, never from reading its source.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return {}
    return {node.name: node for node in _declared_test_functions(tree)}


def static_intent(path: Path):
    """``(declared_test_functions, declared_parametrised_cases)`` for one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    funcs = 0
    cases = 0
    for node in _declared_test_functions(tree):
        funcs += 1
        product = 1
        for dec in node.decorator_list:
            if _is_parametrize(dec):
                product *= _parametrize_size(dec)
        cases += product
    return funcs, cases


# --------------------------------------------------------------------------- #
# Loading, discovery, parametrisation
# --------------------------------------------------------------------------- #

def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create an import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_test_functions(module):
    """Module-level ``test_*`` functions, sorted for a stable run order."""
    return sorted(
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_")
    )


def _expand_parametrised(fn):
    """One ``(args, kwargs)`` pair per parametrised case.

    Stacked ``@pytest.mark.parametrize`` decorators produce the cartesian
    product, matching pytest's own behaviour.
    """
    specs = getattr(fn, "_runner_parametrize", None)
    if not specs:
        return [((), {})]

    combos = [{}]
    for argnames, argvalues in specs:
        if isinstance(argnames, str):
            names = [n.strip() for n in argnames.split(",") if n.strip()]
        else:
            names = [str(n).strip() for n in argnames]
        if not names:
            raise UnsupportedPytestAPI("pytest.mark.parametrize with empty argnames")
        values = list(argvalues)
        if not values:
            continue
        expanded = []
        for base in combos:
            for value in values:
                case = dict(base)
                if len(names) == 1:
                    case[names[0]] = value
                else:
                    if len(value) != len(names):
                        raise UnsupportedPytestAPI(
                            f"parametrize arity mismatch: {len(names)} name(s) for a "
                            f"{len(value)}-element value"
                        )
                    case.update(zip(names, value))
                expanded.append(case)
        combos = expanded
    return [((), case) for case in combos]


def _case_label(name: str, extra: dict) -> str:
    if not extra:
        return name
    return name + "[" + ",".join(f"{k}={v!r}" for k, v in extra.items()) + "]"


# --------------------------------------------------------------------------- #
# Fixture wiring
# --------------------------------------------------------------------------- #

def _build_fixtures(conn, tmp_path, db_path, make_quote_service, monkeypatch):
    from app.database.day_repository import DayRepository
    from app.database.quote_repository import QuoteRepository
    from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
    from app.database.quote_usage_repository import QuoteUsageRepository
    from app.database.task_repository import TaskRepository

    return {
        "db_connection": conn,
        "tmp_path": tmp_path,
        "db_path": db_path,
        "quote_service": make_quote_service(),
        "make_quote_service": make_quote_service,
        "day_repo": DayRepository(conn),
        "task_repo": TaskRepository(conn),
        "quote_repo": QuoteRepository(conn),
        "quote_usage_repo": QuoteUsageRepository(conn),
        "rotation_state_repo": QuoteRotationStateRepository(conn),
        "monkeypatch": monkeypatch,
    }


def _resolve_kwargs(fn, fixtures, supplied=()):
    """Map a test's parameters onto available fixtures, loudly if we cannot.

    ``supplied`` names the parameters that come from ``@pytest.mark.parametrize``
    rather than from a fixture, so they are not mistaken for missing fixtures.
    """
    kwargs = {}
    for name, param in inspect.signature(fn).parameters.items():
        if param.default is not inspect.Parameter.empty:
            continue  # optional: the test supplies it itself
        if name in supplied:
            continue  # provided by parametrise
        if name not in fixtures:
            raise UnsupportedFixture(
                f"fixture {name!r} is not provided by this runner; add it to "
                "_build_fixtures() in scripts/run_all_backend_tests.py"
            )
        kwargs[name] = fixtures[name]
    return kwargs


# --------------------------------------------------------------------------- #
# Explaining an early exit
#
# A test that executes no check is not automatically a broken test: it may have
# deliberately declined because an optional dependency is missing. The runner
# must tell those two situations apart, and it must do so on evidence rather
# than on the shape of the code.
# --------------------------------------------------------------------------- #

def _spans(node: ast.AST, line: int) -> bool:
    """True when ``line`` falls inside the statement ``node``."""
    return (getattr(node, "lineno", None) is not None
            and node.lineno <= line <= (node.end_lineno or node.lineno))


def _handler_names(handler: ast.ExceptHandler) -> set:
    names = set()
    if handler.type is None:
        return {"<bare>"}
    for sub in ast.walk(handler.type):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
    return names


def _platform_condition_value(node: ast.AST):
    """Evaluate a simple ``sys.platform`` / ``os.name`` comparison.

    Returns ``True``/``False``, or ``None`` when the expression is anything
    else. This is deliberately tiny: it exists so that a platform guard can be
    classified on evidence rather than on a pattern match.
    """
    import os
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return None
    left = node.left
    if not (isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name)
            and left.value.id in ("sys", "os")
            and left.attr in ("platform", "name")):
        return None
    actual = sys.platform if left.value.id == "sys" else os.name
    comparator = node.comparators[0]
    if not isinstance(comparator, ast.Constant):
        return None
    if not isinstance(comparator.value, str):
        return None
    op = node.ops[0]
    if isinstance(op, ast.Eq):
        return actual == comparator.value
    if isinstance(op, ast.NotEq):
        return actual != comparator.value
    return None


def explain_early_exit(fn_node, exit_line, guard_triggered, assert_lines=()):
    """Classify a test that completed without executing a verifiable check.

    ``fn_node`` is the test's ``ast.FunctionDef`` and ``assert_lines`` the set
    of line numbers on which the compiler emitted a real ``assert`` check.

    Returns ``(outcome, detail)``. Only a *deliberate* decline -- a dependency
    or platform guard that actually fired -- is reported as ``skipped``.
    Everything else is ``not-run``: the runner cannot tell whether the test
    would have passed, so it must not be counted as a pass.
    """
    if guard_triggered:
        return SKIPPED, (
            "declined by its own dependency guard, which returned True in "
            "this environment (optional dependency unavailable)")

    if exit_line is None or fn_node is None:
        return NOT_RUN, "completed without executing a verifiable check"

    for node in ast.walk(fn_node):
        if isinstance(node, ast.If) and _spans(node, exit_line):
            value = _platform_condition_value(node.test)
            if value is True:
                return SKIPPED, (
                    f"declined by its own platform guard "
                    f"`{ast.unparse(node.test)}` (line {exit_line})")
            call = node.test if isinstance(node.test, ast.Call) else None
            if (call and isinstance(call.func, ast.Name)
                    and call.func.id.startswith(AssertionProbe.GUARD_NAME_PREFIXES)):
                return SKIPPED, (
                    f"declined by its own dependency guard "
                    f"`{ast.unparse(node.test)}` (line {exit_line})")
        if isinstance(node, ast.Try) and _spans(node, exit_line):
            for handler in node.handlers:
                if _spans(handler, exit_line):
                    names = _handler_names(handler)
                    if names & {"Exception", "BaseException", "<bare>"}:
                        return NOT_RUN, (
                            f"an exception was swallowed by "
                            f"`except {', '.join(sorted(names))}: pass` at "
                            f"line {exit_line}; the outcome is unknown")

    # An `assert` the compiler deleted is a different defect from a test that
    # simply ran no check: `assert x or True` can never fail.
    vacuous = sorted(
        node.lineno for node in ast.walk(fn_node)
        if isinstance(node, ast.Assert) and node.lineno not in assert_lines
    )
    if vacuous:
        return NOT_RUN, (
            f"the `assert` on line(s) {vacuous} is vacuous: the compiler "
            "removed it (for example `assert x or True`), so it can never fail")

    return NOT_RUN, (
        f"returned at line {exit_line} without executing a verifiable check")


# --------------------------------------------------------------------------- #
# Running one case
# --------------------------------------------------------------------------- #

class CaseResult:
    __slots__ = ("label", "outcome", "detail")

    def __init__(self, label: str, outcome: str, detail: str = "") -> None:
        self.label = label
        self.outcome = outcome
        self.detail = detail


def run_case(fn, fn_node, args, extra, fixtures, xfail, allowed=()) -> CaseResult:
    """Execute a single test case and classify the outcome honestly.

    ``fn_node`` is the test's ``ast.FunctionDef``; it is used only to explain an
    early exit, never to decide the outcome.

    ``xfail`` is ``None``, or ``(reason, strict)`` as recorded by
    ``@pytest.mark.xfail``. An xfail-marked test that raises is ``xfailed``;
    one that unexpectedly passes is ``xpassed``, or ``failed`` when strict.
    """
    label = _case_label(fn.__name__, extra)
    try:
        call_kwargs = _resolve_kwargs(fn, fixtures, supplied=extra)
    except UnsupportedFixture as exc:
        return CaseResult(label, FAILED, str(exc))
    call_kwargs.update(extra)

    xfail_strict = bool(xfail[1]) if xfail else False
    probe = AssertionProbe(allowed, fn.__code__)
    raises_before = Raises.successful_checks
    previous_trace = sys.gettrace()
    outcome, detail = VERIFIED, ""
    sys.settrace(probe)
    try:
        fn(*args, **call_kwargs)
    except Skipped as exc:
        outcome, detail = SKIPPED, exc.reason
    except XFailed as exc:
        outcome, detail = XFAILED, exc.reason
    except BaseException:
        if xfail:
            # A declared expected failure is a result, not a defect.
            outcome, detail = XFAILED, traceback.format_exc(limit=3)
        else:
            outcome, detail = FAILED, traceback.format_exc(limit=6)
    finally:
        sys.settrace(previous_trace)

    if outcome == VERIFIED:
        proved_something = (
            probe.executed > 0
            or probe.mock_checks > 0
            or Raises.successful_checks > raises_before
        )
        if not proved_something:
            outcome, detail = explain_early_exit(
                fn_node, probe.exit_line, probe.guard_triggered,
                probe._lines_for(fn.__code__),
            )
        elif xfail:
            outcome = XPASSED

    if outcome == XPASSED and xfail_strict:
        outcome = FAILED
        detail = "strict xfail test unexpectedly passed\n" + detail

    return CaseResult(label, outcome, detail)


# --------------------------------------------------------------------------- #
# Delegation to real pytest
# --------------------------------------------------------------------------- #

def delegate_to_pytest(tests_dir: Path) -> int:
    try:
        import pytest  # noqa: F401
    except ImportError:
        print("ERROR: --pytest was requested but pytest is not installed.",
              file=sys.stderr)
        print("       Install it from requirements-dev.txt, or run without --pytest.",
              file=sys.stderr)
        return EXIT_USAGE
    print(f"Delegating to real pytest in {tests_dir}")
    return subprocess.run([sys.executable, "-m", "pytest", str(tests_dir), "-q"]).returncode


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Daily Sticky backend test runner")
    parser.add_argument("tests_dir", nargs="?", default=None,
                        help="directory of test_*.py files (default: <repo>/tests)")
    parser.add_argument("--pytest", action="store_true",
                        help="delegate to real pytest instead of the stdlib runner")
    args = parser.parse_args(argv)

    tests_dir = (Path(args.tests_dir).resolve() if args.tests_dir
                 else (PROJECT_ROOT / "tests"))
    if not tests_dir.is_dir():
        print(f"ERROR: no such test directory: {tests_dir}", file=sys.stderr)
        return EXIT_USAGE

    if args.pytest:
        return delegate_to_pytest(tests_dir)

    # Importing the application layer is an environment concern, not a test
    # result: report it separately and clearly rather than as test failures.
    try:
        from app.core.services.quote_service import QuoteService
        from app.database.connection import create_connection
        from app.database.migrations import apply_migrations
    except Exception as exc:
        print("ERROR: the runner could not import the application layer.",
              file=sys.stderr)
        print(f"       {type(exc).__name__}: {exc}", file=sys.stderr)
        print("       This is an environment problem; no tests were executed.",
              file=sys.stderr)
        return EXIT_USAGE

    install_pytest_mock()

    test_files = sorted(tests_dir.glob("test_*.py"))
    if not test_files:
        print(f"ERROR: no test_*.py files found in {tests_dir}", file=sys.stderr)
        return EXIT_USAGE

    print(f"Discovered {len(test_files)} test files in {tests_dir}")

    # Only asserts that live in the test files count as the test proving
    # something. Without this, an `import` inside a test traces importlib and
    # any assert buried there would be credited to the test.
    allowed_filenames = frozenset(str(p) for p in tests_dir.rglob("*.py"))

    counts = {k: 0 for k in _OUTCOME_ORDER}
    counts[COLLECTION_ERROR] = 0
    declared_funcs_total = 0
    declared_cases_total = 0
    invoked_total = 0
    declined_total = 0
    blocked_total = 0
    problems = []

    for file_path in test_files:
        # --- static intent (an unparseable file is itself a collection error) ---
        # `static_cases` is only an estimate. It is what a file that cannot be
        # imported gets charged with, and it is corrected against the real
        # expansion below once the module has loaded.
        try:
            declared_funcs, static_cases = static_intent(file_path)
        except SyntaxError as exc:
            counts[COLLECTION_ERROR] += 1
            problems.append((file_path.name, "<module>", f"SyntaxError: {exc}"))
            print("E", end="", flush=True)
            continue  # nothing was parsed, so nothing is declared
        except ValueError as exc:
            # ast.parse raises ValueError (not SyntaxError) for a source file
            # that is not decodable text at all -- null bytes, bad encoding.
            counts[COLLECTION_ERROR] += 1
            problems.append((file_path.name, "<module>",
                             f"{type(exc).__name__}: {exc}"))
            print("E", end="", flush=True)
            continue  # nothing was parsed, so nothing is declared

        declared_funcs_total += declared_funcs
        declared_cases_total += static_cases

        # --- load: a file that cannot be imported must never vanish silently ---
        try:
            module = load_module(file_path)
        except UnsupportedPytestAPI as exc:
            counts[COLLECTION_ERROR] += 1
            blocked_total += static_cases
            problems.append((file_path.name, "<module>", str(exc)))
            print("E", end="", flush=True)
            continue
        except BaseException:
            counts[COLLECTION_ERROR] += 1
            blocked_total += static_cases
            problems.append((file_path.name, "<module>", traceback.format_exc()))
            print("E", end="", flush=True)
            continue

        test_funcs = discover_test_functions(module)
        if len(test_funcs) != declared_funcs:
            counts[COLLECTION_ERROR] += 1
            problems.append((
                file_path.name, "<module>",
                f"the file declares {declared_funcs} test function(s) but this runner "
                f"collected {len(test_funcs)}; it only collects module-level test "
                "functions, so class-based tests are invisible to it"))
            blocked_total += static_cases
            print("E", end="", flush=True)
            continue

        # The parsed tree is needed only to explain an early exit; the outcome
        # itself always comes from running the test.
        fn_nodes = _function_nodes(file_path)

        # --- authoritative case count -------------------------------------- #
        # The cases that actually execute are produced by _expand_parametrised,
        # which reads the *runtime* decorator. `static_cases` above could only
        # guess, because ast.literal_eval cannot evaluate a parametrize list
        # built at runtime (sorted(GLYPHS), a module constant, a comprehension)
        # and silently reported 1 case where the real decorator expands to many.
        # Counting declared cases anywhere other than here makes the two
        # accounting identities disagree on a perfectly healthy suite, so the
        # estimate is corrected against the same expansion that drives execution.
        try:
            declared_cases = sum(len(_expand_parametrised(fn))
                                 for _name, fn in test_funcs)
        except UnsupportedPytestAPI as exc:
            counts[COLLECTION_ERROR] += 1
            blocked_total += static_cases
            problems.append((file_path.name, "<module>", str(exc)))
            print("E", end="", flush=True)
            continue
        declared_cases_total += declared_cases - static_cases

        # --- execute every declared case of every test function ---
        for name, fn in test_funcs:
            if getattr(fn, "_runner_skip", None) is not None:
                reason = fn._runner_skip or "marked skip"
                for _args, extra in _expand_parametrised(fn):
                    # A skip marker declines the test without calling it, so it
                    # is *not* an invoked case. Keeping it out of `skipped`
                    # (which means "invoked and deliberately declined") is what
                    # makes the two accounting identities add up.
                    declined_total += 1
                    print("s", end="", flush=True)
                    problems.append((file_path.name, _case_label(name, extra),
                                     f"skipped: {reason}"))
                continue

            xfail_spec = getattr(fn, "_runner_xfail", None)

            for args, extra in _expand_parametrised(fn):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = Path(tmp_dir)
                    db_path = tmp_path / "test.db"
                    conn = create_connection(db_path)
                    try:
                        apply_migrations(conn)

                        from app.database.day_repository import DayRepository
                        from app.database.quote_repository import QuoteRepository
                        from app.database.quote_rotation_state_repository import (
                            QuoteRotationStateRepository,
                        )
                        from app.database.quote_usage_repository import QuoteUsageRepository
                        from app.database.task_repository import TaskRepository

                        day_repo = DayRepository(conn)
                        task_repo = TaskRepository(conn)
                        quote_repo = QuoteRepository(conn)
                        quote_usage_repo = QuoteUsageRepository(conn)
                        rotation_repo = QuoteRotationStateRepository(conn)

                        # These defaults mirror tests/conftest.py exactly, not
                        # QuoteService's own production defaults. A test that
                        # calls make_quote_service() without arguments must
                        # receive the same deterministic service under this
                        # runner that it would receive under real pytest.
                        def make_quote_service(
                            favorite_selection_probability=0.0,
                            random_source=None,
                        ):
                            return QuoteService(
                                conn=conn,
                                quote_repo=quote_repo,
                                day_repo=day_repo,
                                quote_usage_repo=quote_usage_repo,
                                rotation_state_repo=rotation_repo,
                                favorite_selection_probability=(
                                    favorite_selection_probability),
                                random_source=(random_source
                                               if random_source is not None
                                               else random.Random(0)),
                            )

                        fixtures = _build_fixtures(
                            conn, tmp_path, db_path, make_quote_service, MonkeyPatch()
                        )
                    except BaseException as exc:
                        counts[FAILED] += 1
                        invoked_total += 1
                        problems.append((file_path.name, _case_label(name, extra),
                                         f"fixture setup failed: {exc}"))
                        print("F", end="", flush=True)
                        conn.close()
                        continue

                    result = run_case(
                        fn, fn_nodes.get(name), args, extra, fixtures,
                        xfail_spec, allowed_filenames
                    )
                    counts[result.outcome] += 1
                    invoked_total += 1
                    print(_PROGRESS[result.outcome], end="", flush=True)
                    if result.outcome != VERIFIED:
                        problems.append((file_path.name, result.label, result.detail))
                    conn.close()

    # ------------------------------------------------------------------ #
    # Honest summary: never claim success we cannot account for
    #
    # Every number below carries its own definition, and the two accounting
    # identities are printed and checked. A reader must never be left to guess
    # whether a case was declared, invoked, or actually verified.
    # ------------------------------------------------------------------ #
    print()
    print("=" * 72)
    print(f"Declared by the test files: {declared_cases_total} case(s) across "
          f"{declared_funcs_total} function(s)")
    print("  A 'case' is one execution of a test function. A function carrying")
    print("  @pytest.mark.parametrize contributes one case per parameter set.")

    # --- coverage, stated before anything else can be misread ------------- #
    # "No failures" and "everything was verified" are different claims. This
    # line puts the verified/declared ratio where it cannot be missed.
    unverified = declared_cases_total - counts[VERIFIED]
    pct = (100.0 * counts[VERIFIED] / declared_cases_total
           if declared_cases_total else 100.0)
    print()
    print(f"COVERAGE: {counts[VERIFIED]} of {declared_cases_total} declared "
          f"case(s) verified ({pct:.0f}%)")
    if unverified:
        print(f"          {unverified} case(s) did not run their checks "
              f"(skipped, xfailed, xpassed, not invoked or blocked)")

    _DEFINITIONS = (
        (VERIFIED, "invoked, and at least one check executed"),
        (FAILED, "invoked, and it raised"),
        (SKIPPED, "invoked, and it deliberately declined"),
        (NOT_RUN, "invoked, but no check could be verified"),
        (XFAILED, "declared expected failure"),
        (XPASSED, "xfail-marked, but unexpectedly succeeded"),
    )
    # `not invoked` is defined next to the outcomes so that no two printed
    # numbers can be read as covering the same case.
    for outcome, meaning in _DEFINITIONS:
        print(f"  {outcome:<16} {counts[outcome]:>5}   {meaning}")
    print(f"  {COLLECTION_ERROR:<16} {counts[COLLECTION_ERROR]:>5}   "
          "test file(s) that failed to load")
    print(f"  {'invoked':<16} {invoked_total:>5}   the test function was "
          "actually called")
    print(f"  {'not invoked':<16} {declined_total:>5}   declared case(s) never "
          "called (skip markers)")
    print(f"  {'blocked':<16} {blocked_total:>5}   declared case(s) in a file "
          "that failed to load")

    # --- the two accounting identities, checked rather than asserted ------- #
    # `skipped` counts only cases that were invoked and then declined, so it
    # belongs in the invoked sum. Skip markers are reported as `not invoked`.
    invoked_sum = sum(counts[k] for k in _INVOKED_OUTCOMES)
    accounted = invoked_total + declined_total + blocked_total
    accounting_ok = (invoked_sum == invoked_total
                     and accounted == declared_cases_total)
    print("-" * 72)
    print(f"Accounting: declared {declared_cases_total} = invoked "
          f"{invoked_total} + not invoked {declined_total} + blocked "
          f"{blocked_total}")
    print(f"            invoked {invoked_total} = verified {counts[VERIFIED]} "
          f"+ failed {counts[FAILED]} + skipped {counts[SKIPPED]} "
          f"+ not-run {counts[NOT_RUN]} + xfailed {counts[XFAILED]} "
          f"+ xpassed {counts[XPASSED]}")
    if not accounting_ok:
        print("  !! the totals above do not add up; this is a runner defect")

    blocking = []
    if counts[FAILED]:
        blocking.append(f"{counts[FAILED]} test(s) failed")
    if counts[NOT_RUN]:
        blocking.append(
            f"{counts[NOT_RUN]} test(s) completed without a verifiable check")
    if counts[COLLECTION_ERROR]:
        blocking.append(f"{counts[COLLECTION_ERROR]} file(s) failed to load")
    if not accounting_ok:
        blocking.append("the summary totals are inconsistent")
    if accounted != declared_cases_total:
        blocking.append(
            f"only {accounted} of {declared_cases_total} declared case(s) "
            "were accounted for")

    print("-" * 72)
    if blocking:
        print("RESULT: FAILED")
        for reason in blocking:
            print(f"  - {reason}")
        print("  This run is NOT green.")
        print(f"  Exit code {EXIT_FAILED}.")
        exit_code = EXIT_FAILED
    elif counts[VERIFIED] == declared_cases_total:
        print("RESULT: OK")
        print(f"  Every one of the {declared_cases_total} declared case(s) was "
              "verified.")
        print(f"  Exit code {EXIT_VERIFIED}.")
        exit_code = EXIT_VERIFIED
    else:
        # No failures, but not everything ran. This is NOT a fully verified
        # suite, and the exit code must not look like one.
        not_verified = declared_cases_total - counts[VERIFIED]
        print("RESULT: OK WITH SKIPS")
        print(f"  {counts[VERIFIED]} of {declared_cases_total} declared case(s) "
              f"were verified; {not_verified} did not run their checks.")
        explained = sum(counts[k] for k in EXPLAINED_EXCLUSIONS)
        print(f"  Of those, {explained} are explicitly skipped/xfailed/xpassed "
              f"and {not_verified - explained} were never invoked (skip "
              "markers).")
        print("  A skipped test did not pass -- it deliberately declined to run "
              "for the reason listed under Details.")
        print("  This is NOT a fully verified run.")
        print(f"  Exit code {EXIT_INCOMPLETE}.")
        exit_code = EXIT_INCOMPLETE

    if problems:
        print("=" * 72)
        print("Details:")
        for file_name, label, detail in problems:
            print(f"--- {file_name} :: {label} ---")
            print(detail.rstrip())

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
