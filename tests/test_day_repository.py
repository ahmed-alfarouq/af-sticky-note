import sqlite3

import pytest

from app.database.day_repository import DayRepository


def test_create_day(db_connection):
    repo = DayRepository(db_connection)
    day = repo.create("2026-09-21")
    assert day.id is not None
    assert day.date == "2026-09-21"
    assert day.quote_text is None


def test_retrieve_day_by_id(db_connection):
    repo = DayRepository(db_connection)
    created = repo.create("2026-09-21")
    assert repo.get_by_id(created.id) == created


def test_retrieve_day_by_date(db_connection):
    repo = DayRepository(db_connection)
    repo.create("2026-09-21")
    fetched = repo.get_by_date("2026-09-21")
    assert fetched is not None
    assert fetched.date == "2026-09-21"


def test_get_by_date_returns_none_when_missing(db_connection):
    repo = DayRepository(db_connection)
    assert repo.get_by_date("2026-01-01") is None


def test_duplicate_date_is_rejected(db_connection):
    repo = DayRepository(db_connection)
    repo.create("2026-09-21")
    with pytest.raises(sqlite3.IntegrityError):
        repo.create("2026-09-21")


def test_get_or_create_does_not_duplicate(db_connection):
    repo = DayRepository(db_connection)
    first = repo.get_or_create("2026-09-21")
    second = repo.get_or_create("2026-09-21")
    assert first.id == second.id