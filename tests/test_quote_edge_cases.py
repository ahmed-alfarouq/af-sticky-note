import itertools

import pytest

from app.core.services.quote_service import NoAvailableQuotesError


def test_no_quotes_available_raises_controlled_error(make_quote_service):
    service = make_quote_service()
    with pytest.raises(NoAvailableQuotesError):
        service.get_or_assign_daily_quote("2026-09-21")


def test_single_normal_quote_behaves_correctly(quote_repo, make_quote_service):
    quote_repo.create("الوحيدة")
    service = make_quote_service()
    dates = ["2026-09-01", "2026-09-02", "2026-09-03"]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert texts == ["الوحيدة", "الوحيدة", "الوحيدة"]


def test_single_favorite_quote_behaves_correctly(quote_repo, make_quote_service):
    quote_repo.create("المفضلة الوحيدة", is_favorite=True)
    service = make_quote_service()  # no normal quotes exist -> unconditional fallback
    dates = ["2026-09-01", "2026-09-02"]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert texts == ["المفضلة الوحيدة", "المفضلة الوحيدة"]


def test_only_favorite_quotes_behave_correctly(quote_repo, make_quote_service):
    quote_repo.create("مفضلة أولى", is_favorite=True)
    quote_repo.create("مفضلة ثانية", is_favorite=True)
    service = make_quote_service()
    assignment = service.get_or_assign_daily_quote("2026-09-21")
    assert assignment.day.quote_text in {"مفضلة أولى", "مفضلة ثانية"}


class _AlternatingRandom:
    """Deterministic random source: alternates a value below and above
    the 0.5 threshold on each call to .random(), and always picks the
    first eligible item for .choice() — enough to fully control which
    branch QuoteService takes on each call, without relying on any
    particular stdlib random seed's statistical behavior."""

    def __init__(self):
        self._values = itertools.cycle([0.0, 0.9])

    def random(self) -> float:
        return next(self._values)

    def choice(self, seq):
        return seq[0]


def test_mixed_normal_and_favorite_quotes_respect_both_rules(db_connection, quote_repo, make_quote_service):
    quote_repo.create("عادية 1")
    quote_repo.create("عادية 2")
    quote_repo.create("عادية 3")
    quote_repo.create("مفضلة", is_favorite=True)

    service = make_quote_service(
        favorite_selection_probability=0.5, random_source=_AlternatingRandom()
    )
    dates = [f"2026-09-{i:02d}" for i in range(1, 13)]
    for d in dates:
        service.get_or_assign_daily_quote(d)

    rows = db_connection.execute(
        "SELECT cycle_number, quote_id, is_favorite_selection FROM quote_usage"
    ).fetchall()

    normal_by_cycle = {}
    favorite_count = 0
    for row in rows:
        if row["is_favorite_selection"]:
            favorite_count += 1
            continue
        normal_by_cycle.setdefault(row["cycle_number"], []).append(row["quote_id"])

    # No normal quote repeats within any single cycle, however the
    # favorite/normal draws were interleaved.
    for quote_ids in normal_by_cycle.values():
        assert len(quote_ids) == len(set(quote_ids))

    # Both kinds of selection actually happened (not a degenerate run).
    assert favorite_count == 6
    assert sum(len(ids) for ids in normal_by_cycle.values()) == 6