"""Standalone test runner for all backend tests using the standard library.

Exercises all test functions across all test_*.py modules without
requiring external pytest or PySide6 packages to be installed.
"""
from __future__ import annotations

import inspect
import sys
import tempfile
import traceback
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Install a minimal pytest mock in sys.modules so modules importing pytest won't fail
import types
class _PytestMock(types.ModuleType):
    class raises:
        def __init__(self, expected_exc):
            self.expected_exc = expected_exc
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                raise AssertionError(f"Expected {self.expected_exc.__name__} but no exception was raised")
            if issubclass(exc_type, self.expected_exc):
                return True
            return False

    @staticmethod
    def fixture(func=None, *args, **kwargs):
        if func:
            return func
        return lambda f: f

class _MonkeyPatch:
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

sys.modules['pytest'] = _PytestMock('pytest')

from app.database.connection import create_connection
from app.database.migrations import apply_migrations
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository
from app.database.quote_repository import QuoteRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.core.services.quote_service import QuoteService


def run_tests() -> int:
    tests_dir = PROJECT_ROOT / "tests"
    test_files = sorted(tests_dir.glob("test_*.py"))

    total_passed = 0
    total_failed = 0
    failures = []

    print(f"Discovered {len(test_files)} test files in {tests_dir}")

    for file_path in test_files:
        module_name = file_path.stem
        # Dynamically import module
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:
            print(f"Error loading {file_path.name}: {exc}")
            total_failed += 1
            failures.append((file_path.name, "<module>", traceback.format_exc()))
            continue

        test_funcs = [
            (name, obj)
            for name, obj in inspect.getmembers(mod, inspect.isfunction)
            if name.startswith("test_")
        ]

        for func_name, func in test_funcs:
            sig = inspect.signature(func)
            params = sig.parameters

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                db_path = tmp_path / "test.db"
                conn = create_connection(db_path)
                apply_migrations(conn)

                day_repo = DayRepository(conn)
                task_repo = TaskRepository(conn)
                quote_repo = QuoteRepository(conn)
                quote_usage_repo = QuoteUsageRepository(conn)
                rotation_repo = QuoteRotationStateRepository(conn)

                def make_quote_service(
                    favorite_selection_probability=0.15,
                    random_source=None,
                ):
                    return QuoteService(
                        conn=conn,
                        quote_repo=quote_repo,
                        day_repo=day_repo,
                        quote_usage_repo=quote_usage_repo,
                        rotation_state_repo=rotation_repo,
                        favorite_selection_probability=favorite_selection_probability,
                        random_source=random_source,
                    )

                mp = _MonkeyPatch()

                kwargs = {}
                if "db_connection" in params:
                    kwargs["db_connection"] = conn
                if "tmp_path" in params:
                    kwargs["tmp_path"] = tmp_path
                if "quote_service" in params:
                    kwargs["quote_service"] = make_quote_service()
                if "make_quote_service" in params:
                    kwargs["make_quote_service"] = make_quote_service
                if "db_path" in params:
                    kwargs["db_path"] = db_path
                if "day_repo" in params:
                    kwargs["day_repo"] = day_repo
                if "task_repo" in params:
                    kwargs["task_repo"] = task_repo
                if "quote_repo" in params:
                    kwargs["quote_repo"] = quote_repo
                if "quote_usage_repo" in params:
                    kwargs["quote_usage_repo"] = quote_usage_repo
                if "rotation_state_repo" in params:
                    kwargs["rotation_state_repo"] = rotation_repo
                if "monkeypatch" in params:
                    kwargs["monkeypatch"] = mp

                try:
                    func(**kwargs)
                    total_passed += 1
                    print(".", end="", flush=True)
                except Exception as exc:
                    total_failed += 1
                    print("F", end="", flush=True)
                    failures.append((file_path.name, func_name, traceback.format_exc()))
                finally:
                    mp.finish()
                    conn.close()

    print("\n" + "=" * 60)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if failures:
        print("\nFailures:")
        for file_name, func_name, tb in failures:
            print(f"--- {file_name} :: {func_name} ---")
            print(tb)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
