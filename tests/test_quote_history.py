from app.core.services.quote_import_service import QuoteImportService


def test_daily_quote_stays_attached_to_its_day(quote_repo, make_quote_service):
    quote_repo.create("اقتباس اليوم")
    service = make_quote_service()
    assignment = service.get_or_assign_daily_quote("2026-09-21")
    assert assignment.day.quote_text == "اقتباس اليوم"


def test_changing_quotes_file_later_does_not_change_assigned_day(
    tmp_path, quote_repo, day_repo, make_quote_service
):
    quotes_file = tmp_path / "quotes.txt"
    quotes_file.write_text("اقتباس أول", encoding="utf-8")
    QuoteImportService(quote_repo).import_quotes(quotes_file)

    service = make_quote_service()
    service.get_or_assign_daily_quote("2026-09-21")

    quotes_file.write_text("اقتباس أول\nاقتباس جديد كلياً", encoding="utf-8")
    QuoteImportService(quote_repo).import_quotes(quotes_file)

    reloaded_day = day_repo.get_by_date("2026-09-21")
    assert reloaded_day.quote_text == "اقتباس أول"


def test_reimport_does_not_rewrite_existing_daily_quotes(
    tmp_path, quote_repo, day_repo, make_quote_service
):
    quotes_file = tmp_path / "quotes.txt"
    quotes_file.write_text("اقتباس ثابت", encoding="utf-8")
    importer = QuoteImportService(quote_repo)
    importer.import_quotes(quotes_file)

    service = make_quote_service()
    service.get_or_assign_daily_quote("2026-09-21")

    importer.import_quotes(quotes_file)  # re-import, same content

    day = day_repo.get_by_date("2026-09-21")
    assert day.quote_text == "اقتباس ثابت"