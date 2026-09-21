"""Reading the plain-text quotes source file.

Pure I/O boundary: reads and applies only safe, non-destructive
normalization (line splitting, outer whitespace strip, blank-line
removal). Deduplication and database decisions are QuoteImportService's
job, not this module's.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


def read_quote_lines(path: Path) -> List[str]:
    """Read quotes.txt and return non-blank, whitespace-trimmed lines.

    Raises FileNotFoundError if the file does not exist, and
    UnicodeDecodeError if it cannot be decoded as UTF-8. Both are
    caught by the caller (QuoteImportService) and turned into a
    controlled result rather than propagating into a crash.
    """
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line]