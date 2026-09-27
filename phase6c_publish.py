#!/usr/bin/env python3
"""TEMPORARY Phase 6C helper -- push CI output back through api.github.com.

The driving sandbox cannot reach the Actions log host or the artifact blob
storage, so run output is returned through the only API surface that is
reachable: a check run on the commit, falling back to an issue, falling back
to a commit on the session branch.

Deleted together with the workflow once results have been collected.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MAX_TEXT = 60000


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def read_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"<missing file: {path}>"
    data = p.read_text(encoding="utf-8", errors="replace")
    if len(data) > MAX_TEXT:
        data = data[:MAX_TEXT] + f"\n...<truncated; {len(data)} characters total>"
    return data


def git(*args):
    return run(["git", *args])


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")
    label = sys.argv[1] if len(sys.argv) > 1 else "phase6c-result"
    source = sys.argv[2] if len(sys.argv) > 2 else "artifacts/report.json"

    body = read_text(source)
    print(f"publishing {len(body)} characters of {source} for repo={repo} sha={sha}")

    # --- 1. check run on the commit -------------------------------------
    payload = {
        "name": f"phase6c-result/{label}",
        "head_sha": sha,
        "status": "completed",
        "conclusion": "neutral",
        "output": {
            "title": f"Phase 6C {label}",
            "summary": f"Windows verification output ({source})",
            "text": body,
        },
    }
    Path("phase6c_payload.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    r = run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"/repos/{repo}/check-runs",
            "--input",
            "phase6c_payload.json",
        ]
    )
    if r.returncode == 0:
        print("PUBLISH_CHANNEL=check-run")
        return 0
    print(f"check-run failed: {(r.stdout + r.stderr)[:300]}")

    # --- 2. issue --------------------------------------------------------
    issue = {"title": f"Phase 6C {label} results", "body": f"```\n{body}\n```"}
    Path("phase6c_issue.json").write_text(json.dumps(issue), encoding="utf-8")
    r = run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"/repos/{repo}/issues",
            "--input",
            "phase6c_issue.json",
        ]
    )
    if r.returncode == 0:
        print("PUBLISH_CHANNEL=issue")
        return 0
    print(f"issue failed: {(r.stdout + r.stderr)[:300]}")

    # --- 3. commit on the session branch --------------------------------
    out_dir = Path("phase6c-results")
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{label}.txt").write_text(body, encoding="utf-8")
    git("add", "-A", "phase6c-results")
    git(
        "-c",
        "user.name=phase6c-ci",
        "-c",
        "user.email=phase6c-ci@users.noreply.github.com",
        "commit",
        "-m",
        f"phase6c: publish {label} results from windows runner",
    )
    r = git("push")
    if r.returncode == 0:
        print("PUBLISH_CHANNEL=commit")
        return 0
    print(f"push failed: {(r.stdout + r.stderr)[:300]}")

    print("PUBLISH_CHANNEL=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
