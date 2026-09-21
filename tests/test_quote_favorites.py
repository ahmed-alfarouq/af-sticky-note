import random


def test_favorite_can_repeat_before_normal_cycle_exhausted(quote_repo, make_quote_service):
    quote_repo.create("عادية 1")
    quote_repo.create("عادية 2")
    quote_repo.create("مفضلة", is_favorite=True)

    service = make_quote_service(favorite_selection_probability=1.0, random_source=random.Random(1))
    dates = ["2026-09-01", "2026-09-02", "2026-09-03"]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert texts == ["مفضلة", "مفضلة", "مفضلة"]


def test_selecting_favorite_does_not_consume_normal_cycle(
    quote_repo, day_repo, quote_usage_repo, rotation_state_repo
):
    from app.core.services.quote_service import QuoteService

    quote_repo.create("عادية 1")
    quote_repo.create("عادية 2")
    quote_repo.create("مفضلة", is_favorite=True)

    service_fav = QuoteService(
        quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=1.0, random_source=random.Random(1),
    )
    service_fav.get_or_assign_daily_quote("2026-09-01")

    service_normal = QuoteService(
        quote_repo, day_repo, quote_usage_repo, rotation_state_repo,
        favorite_selection_probability=0.0, random_source=random.Random(2),
    )
    texts = [
        service_normal.get_or_assign_daily_quote(d).day.quote_text
        for d in ["2026-09-02", "2026-09-03"]
    ]
    assert set(texts) == {"عادية 1", "عادية 2"}


def test_normal_quotes_still_cannot_repeat_within_cycle_when_favorites_present(
    quote_repo, make_quote_service
):
    quote_repo.create("عادية 1")
    quote_repo.create("عادية 2")
    quote_repo.create("مفضلة", is_favorite=True)

    service = make_quote_service(favorite_selection_probability=0.0, random_source=random.Random(11))
    dates = ["2026-09-01", "2026-09-02"]
    texts = [service.get_or_assign_daily_quote(d).day.quote_text for d in dates]
    assert set(texts) == {"عادية 1", "عادية 2"}


def test_favorite_status_persists(quote_repo):
    quote = quote_repo.create("مفضلة", is_favorite=True)
    assert quote_repo.get_by_id(quote.id).is_favorite is True