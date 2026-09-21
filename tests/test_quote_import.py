from pathlib import Path

from app.core.services.quote_import_service import QuoteImportService


def _write_quotes_file(tmp_path: Path, lines) -> Path:
    file_path = tmp_path / "quotes.txt"
    file_path.write_text("\n".join(lines), encoding="utf-8")
    return file_path


def test_missing_file_is_handled_without_crash(tmp_path, quote_repo):
    service = QuoteImportService(quote_repo)
    result = service.import_quotes(tmp_path / "does_not_exist.txt")
    assert result.file_found is False
    assert result.imported_count == 0
    assert result.error is not None
    assert quote_repo.list_all() == []


def test_empty_file_imports_nothing(tmp_path, quote_repo):
    file_path = _write_quotes_file(tmp_path, [])
    result = QuoteImportService(quote_repo).import_quotes(file_path)
    assert result.file_found is True
    assert result.imported_count == 0
    assert result.error is None


def test_blank_lines_are_ignored(tmp_path, quote_repo):
    file_path = _write_quotes_file(
        tmp_path, ["ابدأ بما تستطيع.", "", "   ", "خطوة صغيرة كل يوم."]
    )
    result = QuoteImportService(quote_repo).import_quotes(file_path)
    assert result.imported_count == 2
    assert len(quote_repo.list_all()) == 2


def test_whitespace_is_trimmed_safely(tmp_path, quote_repo):
    file_path = _write_quotes_file(tmp_path, ["   ابدأ بما تستطيع.   "])
    QuoteImportService(quote_repo).import_quotes(file_path)
    assert quote_repo.list_all()[0].text == "ابدأ بما تستطيع."


def test_duplicate_lines_create_only_one_quote(tmp_path, quote_repo):
    file_path = _write_quotes_file(tmp_path, ["خطوة صغيرة كل يوم.", "خطوة صغيرة كل يوم."])
    result = QuoteImportService(quote_repo).import_quotes(file_path)
    assert result.imported_count == 1
    assert len(quote_repo.list_all()) == 1


def test_reimport_preserves_existing_metadata(tmp_path, quote_repo):
    file_path = _write_quotes_file(tmp_path, ["ابدأ بما تستطيع."])
    importer = QuoteImportService(quote_repo)
    importer.import_quotes(file_path)

    quote = quote_repo.list_all()[0]
    quote_repo.set_favorite(quote.id, True)  # simulate a future favoriting feature

    result = importer.import_quotes(file_path)
    assert result.imported_count == 0
    assert result.skipped_duplicate_count == 1
    assert quote_repo.get_by_id(quote.id).is_favorite is True


def test_reimport_does_not_delete_user_created_quotes(tmp_path, quote_repo):
    quote_repo.create("اقتباس أضافه المستخدم", is_user_created=True)
    file_path = _write_quotes_file(tmp_path, ["ابدأ بما تستطيع."])
    QuoteImportService(quote_repo).import_quotes(file_path)

    texts = {q.text for q in quote_repo.list_all()}
    assert "اقتباس أضافه المستخدم" in texts


def test_imported_quotes_are_not_user_created(tmp_path, quote_repo):
    file_path = _write_quotes_file(tmp_path, ["ابدأ بما تستطيع."])
    QuoteImportService(quote_repo).import_quotes(file_path)
    assert quote_repo.list_all()[0].is_user_created is False


def test_user_created_quote_is_distinguishable_from_imported(tmp_path, quote_repo):
    file_path = _write_quotes_file(tmp_path, ["ابدأ بما تستطيع."])
    QuoteImportService(quote_repo).import_quotes(file_path)
    user_quote = quote_repo.create("اقتباس من المستخدم", is_user_created=True)

    imported_quote = next(q for q in quote_repo.list_all() if q.text == "ابدأ بما تستطيع.")
    assert imported_quote.is_user_created is False
    assert user_quote.is_user_created is True