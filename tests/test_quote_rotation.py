import random


def _add_normal_quotes(quote_repo, texts):
    return [quote_repo.create(text) for text in texts]


def test_four_quotes_first_four_selections_cover_all_exactly_once(quote_repo, make_quote_service):
    _add_normal_quotes(quote_repo, ["A", "B", "C", "D"])
    service = make_quote_service(random_source=random.Random(7))
    dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert set(texts) == {"A", "B", "C", "D"}
    assert len(texts) == len(set(texts))


def test_fifth_selection_starts_new_cycle(quote_repo, make_quote_service):
    _add_normal_quotes(quote_repo, ["A", "B", "C", "D"])
    service = make_quote_service(random_source=random.Random(3))
    dates = [f"2026-09-{i:02d}" for i in range(1, 6)]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert len(set(texts[:4])) == 4
    assert texts[4] in texts[:4]


def test_reopening_mid_cycle_does_not_reset_it(
    db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo
):
    from app.core.services.quote_service import QuoteService

    _add_normal_quotes(quote_repo, ["A", "B", "C", "D"])

    service1 = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(1),
    )
    used = [
        service1.get_or_assign_daily_quote(d).day.quote_text
        for d in ["2026-09-01", "2026-09-02"]
    ]

    # A brand new QuoteService instance, simulating the app reopening.
    service2 = QuoteService(
        db_connection, quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(99),
    )
    remaining = [
        service2.get_or_assign_daily_quote(d).day.quote_text
        for d in ["2026-09-03", "2026-09-04"]
    ]

    all_selected = used + remaining
    assert set(all_selected) == {"A", "B", "C", "D"}
    assert len(all_selected) == len(set(all_selected))


def test_quote_cannot_repeat_within_same_cycle(quote_repo, make_quote_service):
    _add_normal_quotes(quote_repo, ["A", "B", "C"])
    service = make_quote_service(random_source=random.Random(5))
    dates = ["2026-09-01", "2026-09-02", "2026-09-03"]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert len(set(texts)) == 3