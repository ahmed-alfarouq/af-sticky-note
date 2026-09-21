"""Centralized time utilities.

All timestamp/date generation goes through this module so it is not
duplicated across repositories, and so a future test can monkeypatch
one place if it ever needs to control "now".
"""
from __future__ import annotations

from datetime import date, datetime, timezone


def utc_now_iso() -> str:
    """Current UTC instant as an ISO-8601 string. Used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


def local_today_iso() -> str:
    """Current local calendar date as YYYY-MM-DD.

    Deliberately separate from utc_now_iso: a Day's date must reflect
    the user's local calendar day. Near midnight, the local date and
    the UTC date can legitimately differ, and mixing the two would
    assign tasks to the wrong day.
    """
    return date.today().isoformat()