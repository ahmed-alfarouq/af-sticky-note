"""Shared pytest fixtures. All use pytest's tmp_path — never a real
application-data directory."""
import os
import random
import sys

import pytest

from app.core.services.quote_service import QuoteService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.task_repository import TaskRepository
from app.database.unit_of_work import UnitOfWork


def _gui_bootstrap_available() -> bool:
    """Whether a QApplication can be created safely in this environment."""
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        return False
    if QApplication.instance() is not None:
        return True
    # Explicit platform (e.g. QT_QPA_PLATFORM=offscreen), a display server,
    # or native Windows (QApplication creation is display-safe there).
    return bool(
        os.environ.get("QT_QPA_PLATFORM")
        or os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or sys.platform == "win32"
    )


_fonts_bootstrapped = False


@pytest.fixture(scope="session", autouse=True)
def _production_fonts():
    """Mirror production bootstrap: register bundled fonts before UI tests.

    ``app.main.bootstrap_application`` loads the Thmanyah bundle before any
    widget exists, so every shipped pixel is measured with real Arabic-capable
    fonts. Widget tests that measure text layout must see the same font
    environment; otherwise complex-script wrapping assertions measure a
    configuration that never ships (e.g. zero font families offscreen).
    Skips gracefully where no GUI platform is available.
    """
    global _fonts_bootstrapped
    if _fonts_bootstrapped or not _gui_bootstrap_available():
        return
    try:
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])
        from app.infrastructure.fonts import load_application_fonts
        from app.infrastructure.paths import get_fonts_dir

        load_application_fonts(get_fonts_dir())
        _fonts_bootstrapped = True
    except Exception:
        return


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_daily_sticky.db"


@pytest.fixture()
def db_connection(db_path):
    conn = create_connection(db_path)
    apply_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture()
def quote_repo(db_connection):
    return QuoteRepository(db_connection)


@pytest.fixture()
def day_repo(db_connection):
    return DayRepository(db_connection)


@pytest.fixture()
def task_repo(db_connection):
    return TaskRepository(db_connection)


@pytest.fixture()
def quote_usage_repo(db_connection):
    return QuoteUsageRepository(db_connection)


@pytest.fixture()
def rotation_state_repo(db_connection):
    return QuoteRotationStateRepository(db_connection)


@pytest.fixture()
def unit_of_work(db_connection):
    """A UnitOfWork bound to the same test connection every other
    fixture here uses. Tests that need to verify state via a raw
    query can use unit_of_work._conn for that — it is the same
    object as db_connection."""
    return UnitOfWork(db_connection)


@pytest.fixture()
def make_quote_service(db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo):
    def _make(favorite_selection_probability: float = 0.0, random_source=None):
        return QuoteService(
            conn=db_connection,
            quote_repo=quote_repo,
            day_repo=day_repo,
            quote_usage_repo=quote_usage_repo,
            rotation_state_repo=rotation_state_repo,
            favorite_selection_probability=favorite_selection_probability,
            random_source=random_source if random_source is not None else random.Random(0),
        )

    return _make