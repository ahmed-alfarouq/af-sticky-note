from app.database.quote_repository import QuoteRepository


def test_create_quote(db_connection):
    repo = QuoteRepository(db_connection)
    quote = repo.create("ابدأ بما تستطيع.")
    assert quote.id is not None
    assert quote.is_favorite is False
    assert quote.is_user_created is False


def test_retrieve_quote(db_connection):
    repo = QuoteRepository(db_connection)
    created = repo.create("خطوة صغيرة كل يوم.")
    assert repo.get_by_id(created.id) == created


def test_favorite_status_persists(db_connection):
    repo = QuoteRepository(db_connection)
    quote = repo.create("لا تنتظر الوقت المثالي.", is_favorite=True)
    assert repo.get_by_id(quote.id).is_favorite is True


def test_user_created_status_persists(db_connection):
    repo = QuoteRepository(db_connection)
    quote = repo.create("اقتباس من المستخدم", is_user_created=True)
    assert repo.get_by_id(quote.id).is_user_created is True