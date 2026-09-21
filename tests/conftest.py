"""Shared pytest fixtures. All use pytest's tmp_path — never a real
application-data directory."""
import random

import pytest

from app.core.services.quote_service import QuoteService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.unit_of_work import UnitOfWork


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