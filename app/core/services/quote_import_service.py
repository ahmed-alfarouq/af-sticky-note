"""Synchronizes data/quotes.txt into the quotes table.

Import is additive and non-destructive: a quote already in the
database is never deleted or overwritten, even if its line
disappears from the text file. This protects future user-created
quotes, and any favorite status a user has set, from being wiped out
by re-running the import.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.database.quote_repository import QuoteRepository
from app.infrastructure.quotes_file import read_quote_lines

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuoteImportResult:
    file_found: bool
    total_lines_read: int
    imported_count: int
    skipped_duplicate_count: int
    error: Optional[str] = None


class QuoteImportService:
    def __init__(self, quote_repo: QuoteRepository) -> None:
        self._quote_repo = quote_repo

    def import_quotes(self, file_path: Path) -> QuoteImportResult:
        try:
            lines = read_quote_lines(file_path)
        except FileNotFoundError:
            logger.warning("Quotes file not found: %s", file_path)
            return QuoteImportResult(
                file_found=False,
                total_lines_read=0,
                imported_count=0,
                skipped_duplicate_count=0,
                error=f"Quotes file not found: {file_path}",
            )
        except (UnicodeDecodeError, OSError) as exc:
            logger.error("Failed to read quotes file %s: %s", file_path, exc)
            return QuoteImportResult(
                file_found=True,
                total_lines_read=0,
                imported_count=0,
                skipped_duplicate_count=0,
                error=f"Failed to read quotes file: {exc}",
            )

        # De-duplicate exact-text repeats within the file itself before
        # touching the database, preserving first-seen order.
        seen = set()
        unique_texts = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_texts.append(line)

        imported = 0
        skipped = 0
        for text in unique_texts:
            if self._quote_repo.get_by_text(text) is not None:
                skipped += 1
                continue
            self._quote_repo.create(text, is_favorite=False, is_user_created=False)
            imported += 1

        return QuoteImportResult(
            file_found=True,
            total_lines_read=len(lines),
            imported_count=imported,
            skipped_duplicate_count=skipped,
        )