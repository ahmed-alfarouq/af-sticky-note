"""Shared pytest fixtures.

All fixtures use pytest's tmp_path (via db_path), never the real
application-data directory — tests never touch a real user's database.
"""
import random

import pytest

from app.core.services.quote_service import QuoteService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository


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
def quote_usage_repo(db_connection):
    return QuoteUsageRepository(db_connection)


@pytest.fixture()
def rotation_state_repo(db_connection):
    return QuoteRotationStateRepository(db_connection)


@pytest.fixture()
def make_quote_service(quote_repo, day_repo, quote_usage_repo, rotation_state_repo):
    """Factory fixture: build a QuoteService with test-controlled randomness.

    Defaults to favorite_selection_probability=0.0 (never pick a
    favorite) so tests that don't care about favorites get plain,
    deterministic rotation behavior without extra setup.
    """

    def _make(favorite_selection_probability: float = 0.0, random_source=None):
        return QuoteService(
            quote_repo=quote_repo,
            day_repo=day_repo,
            quote_usage_repo=quote_usage_repo,
            rotation_state_repo=rotation_state_repo,
            favorite_selection_probability=favorite_selection_probability,
            random_source=random_source if random_source is not None else random.Random(0),
        )

    return _make