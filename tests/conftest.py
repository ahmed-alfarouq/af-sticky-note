"""Shared pytest fixtures.

Both fixtures use pytest's tmp_path, never the real application-data
directory — tests never touch a real user's database.
"""
import pytest

from app.database.connection import create_connection
from app.database.migrations import apply_migrations


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test_daily_sticky.db"


@pytest.fixture()
def db_connection(db_path):
    conn = create_connection(db_path)
    apply_migrations(conn)
    yield conn
    conn.close()