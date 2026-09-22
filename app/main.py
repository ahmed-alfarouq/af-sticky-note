"""Application entry point and composition root.

Wires together the real application flow for Phase 4A:
1. Construct QApplication with RTL direction.
2. Resolve database path and open SQLite connection.
3. Apply schema migrations.
4. Instantiate repositories.
5. Instantiate services (TaskService, QuoteImportService, QuoteService).
6. Run additive seed quote import from data/quotes.txt.
7. Resolve today's date, Day, and Quote.
8. Load today's tasks.
9. Instantiate and show MainWindow.
10. Cleanly close database connection upon exit.
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config.settings import APP_NAME, ORG_NAME
from app.core.services.quote_import_service import QuoteImportService
from app.core.services.quote_service import NoAvailableQuotesError, QuoteService
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import MigrationError, apply_migrations
from app.database.quote_repository import QuoteRepository
from app.database.quote_rotation_state_repository import QuoteRotationStateRepository
from app.database.quote_usage_repository import QuoteUsageRepository
from app.database.task_repository import TaskRepository
from app.infrastructure.clock import local_today_iso
from app.infrastructure.fonts import load_application_fonts
from app.infrastructure.paths import get_database_path, get_fonts_dir, get_quotes_path
from app.ui.windows.main_window import MainWindow

logger = logging.getLogger(__name__)


def bootstrap_application(app: QApplication) -> MainWindow:
    """Initialize persistence, domain services, and construct MainWindow."""
    # Register bundled Thmanyah fonts safely before creating widgets
    fonts_dir = get_fonts_dir()
    load_application_fonts(fonts_dir)

    db_path = get_database_path()
    conn = create_connection(db_path)

    try:
        apply_migrations(conn)
    except MigrationError as exc:
        conn.close()
        raise RuntimeError(f"Database migration failed: {exc}") from exc

    # Repositories
    day_repo = DayRepository(conn)
    task_repo = TaskRepository(conn)
    quote_repo = QuoteRepository(conn)
    quote_usage_repo = QuoteUsageRepository(conn)
    rotation_repo = QuoteRotationStateRepository(conn)

    # Services
    task_service = TaskService(task_repo=task_repo)
    quote_import_service = QuoteImportService(quote_repo=quote_repo)
    quote_service = QuoteService(
        conn=conn,
        quote_repo=quote_repo,
        day_repo=day_repo,
        quote_usage_repo=quote_usage_repo,
        rotation_state_repo=rotation_repo,
    )

    # 1. Additive quote import from data/quotes.txt
    quotes_path = get_quotes_path()
    import_result = quote_import_service.import_quotes(quotes_path)
    if import_result.imported_count > 0:
        logger.info("Imported %d new quotes from %s", import_result.imported_count, quotes_path)

    # 2. Resolve today's date, Day record, and daily Quote
    today_str = local_today_iso()
    try:
        assignment = quote_service.get_or_assign_daily_quote(today_str)
        day = assignment.day
        quote_text = assignment.day.quote_text
    except NoAvailableQuotesError:
        logger.warning("No quotes available in database for date %s", today_str)
        day = day_repo.get_or_create(today_str)
        quote_text = "لا توجد حكمة متاحة لهذا اليوم"

    # 3. Load today's initial tasks
    assert day.id is not None, "Day id is always populated after database retrieval/creation"
    initial_tasks = task_service.get_today_tasks(day.id)

    # 4. Create MainWindow
    window = MainWindow(
        day=day,
        quote_text=quote_text,
        task_service=task_service,
        initial_tasks=initial_tasks,
    )

    # Hook database connection close to Qt application quit
    app.aboutToQuit.connect(conn.close)

    return window


def main() -> int:
    """Main application entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    try:
        window = bootstrap_application(app)
        window.show()
    except Exception as exc:
        logger.critical("Fatal application startup error: %s", exc, exc_info=True)
        QMessageBox.critical(
            None,
            "خطأ في التشغيل",
            f"حدث خطأ غير متوقع أثناء تشغيل التطبيق:\n{exc}",
        )
        return 1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
