from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.core.services.quote_service import QuoteService


def test_first_request_assigns_a_quote(quote_repo, make_quote_service):
    quote_repo.create("ابدأ بما تستطيع.")
    service = make_quote_service()
    assignment = service.get_or_assign_daily_quote("2026-09-21")
    assert assignment.day.quote_text == "ابدأ بما تستطيع."
    assert assignment.was_newly_assigned is True


def test_second_request_same_day_returns_same_quote(quote_repo, make_quote_service):
    quote_repo.create("ابدأ بما تستطيع.")
    quote_repo.create("خطوة صغيرة كل يوم.")
    service = make_quote_service()
    first = service.get_or_assign_daily_quote("2026-09-21")
    second = service.get_or_assign_daily_quote("2026-09-21")
    assert second.day.quote_text == first.day.quote_text
    assert second.was_newly_assigned is False


def test_restart_simulation_returns_same_quote(db_path):
    conn1 = create_connection(db_path)
    apply_migrations(conn1)
    QuoteRepository(conn1).create("ابدأ بما تستطيع.")
    service1 = QuoteService(
        QuoteRepository(conn1), DayRepository(conn1),
        QuoteUsageRepository(conn1), QuoteRotationStateRepository(conn1),
    )
    first = service1.get_or_assign_daily_quote("2026-09-21")
    conn1.close()

    conn2 = create_connection(db_path)
    apply_migrations(conn2)  # already-applied migrations are a no-op
    service2 = QuoteService(
        QuoteRepository(conn2), DayRepository(conn2),
        QuoteUsageRepository(conn2), QuoteRotationStateRepository(conn2),
    )
    second = service2.get_or_assign_daily_quote("2026-09-21")
    conn2.close()

    assert second.day.quote_text == first.day.quote_text
    assert second.was_newly_assigned is False


def test_different_days_can_receive_different_quotes(quote_repo, make_quote_service):
    quote_repo.create("ابدأ بما تستطيع.")
    quote_repo.create("خطوة صغيرة كل يوم.")
    service = make_quote_service()
    day1 = service.get_or_assign_daily_quote("2026-09-20")
    day2 = service.get_or_assign_daily_quote("2026-09-21")
    assert day1.day.quote_text != day2.day.quote_text