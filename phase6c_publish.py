#!/usr/bin/env python3
"""TEMPORARY Phase 6C helper -- return CI output through api.github.com.

The driving sandbox cannot reach the Actions log host or the artifact blob
storage, and the Actions GITHUB_TOKEN is read-only here, so run output is
returned as check-run annotations, which ARE readable over api.github.com.

Each source file becomes one step worth of `::warning` annotations, chunked
to stay inside the per-annotation message limit.

Deleted together with the workflow once results have been collected.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CHUNK = 3000
MAX_CHUNKS = 8


def read_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"<missing file: {path}>"
    return p.read_text(encoding="utf-8", errors="replace")


def escape(message: str) -> str:
    return (
        message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    )


def chunk(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    parts: list[str] = []
    current = ""
    for line in lines:
        if len(current) + len(line) > CHUNK and current:
            parts.append(current)
            current = ""
        current += line
        if len(current) >= CHUNK:
            parts.append(current)
            current = ""
    if current:
        parts.append(current)
    return parts


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "phase6c-result"
    source = sys.argv[2] if len(sys.argv) > 2 else "artifacts/report.json"

    text = read_text(source)
    parts = chunk(text)
    truncated = ""
    if len(parts) > MAX_CHUNKS:
        kept = parts[:MAX_CHUNKS]
        dropped = sum(len(p) for p in parts[MAX_CHUNKS:])
        parts = kept
        truncated = f" ...truncated {dropped} characters"

    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in label)
    for index, part in enumerate(parts, start=1):
        title = f"phase6c-{safe}-part{index}of{len(parts)}"
        message = escape(part) + escape(truncated) if truncated else escape(part)
        print(f"::warning title={title}::{message}")

    # Backup channel: the run summary page.
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"\n## Phase 6C {label}\n\n```\n{text[:60000]}\n```\n")

    print(f"PHASE6C_PUBLISH {label} {len(text)} chars in {len(parts)} annotation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
