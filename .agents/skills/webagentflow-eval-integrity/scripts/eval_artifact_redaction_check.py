#!/usr/bin/env python3
"""Scan public eval artifacts for private payloads and secret-like content.

Exit codes:
  0: pass
  1: fail, redaction issues found
  2: blocked, no readable inputs or invalid invocation
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Pattern

DEFAULT_TERMS = [
    "pending_choice_private_map",
    "private_choice_map",
    "private_retry_payload",
    "slot_overrides",
    "evidence_targets",
    "ReplayAction",
    "execution_payload",
    "selector",
    "xpath",
    "learned_path_id",
    "path_id",
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "credential",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
]

DEFAULT_REGEXES = [
    r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    r"(?i)(authorization|cookie|set-cookie)\s*[:=]",
    r"(?i)(password|secret|token|api[_-]?key|credential)\s*[:=]\s*[^\s,;{}\]]+",
]

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
    ".gz", ".tar", ".tgz", ".woff", ".woff2", ".ttf", ".otf", ".pyc",
    ".sqlite", ".db",
}

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}


def _iter_input_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            for current_root, dirs, filenames in os.walk(path):
                dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
                for filename in filenames:
                    file_path = Path(current_root) / filename
                    if file_path.suffix.lower() not in BINARY_EXTENSIONS:
                        files.append(file_path)
    return files


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None
    except Exception:
        return None


def _compile_regexes(patterns: list[str]) -> list[Pattern[str]]:
    return [re.compile(pattern) for pattern in patterns]


def scan(paths: list[Path], extra_terms: list[str], extra_regexes: list[str]) -> dict[str, Any]:
    terms = DEFAULT_TERMS + extra_terms
    regexes = _compile_regexes(DEFAULT_REGEXES + extra_regexes)
    files = _iter_input_files(paths)
    if not files:
        return {"status": "blocked", "reason": "no readable input files", "matches": [], "match_count": 0}

    matches: list[dict[str, Any]] = []
    for file_path in files:
        text = _read(file_path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            for term in terms:
                if term.lower() in lower:
                    matches.append(
                        {
                            "path": str(file_path),
                            "line": line_no,
                            "kind": "term",
                            "token": term,
                            "preview": line.strip()[:240],
                        }
                    )
            for regex in regexes:
                if regex.search(line):
                    matches.append(
                        {
                            "path": str(file_path),
                            "line": line_no,
                            "kind": "regex",
                            "token": regex.pattern,
                            "preview": line.strip()[:240],
                        }
                    )

    return {
        "status": "fail" if matches else "pass",
        "matches": matches,
        "match_count": len(matches),
        "files_scanned": len(files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument("--extra-term", action="append", default=[], help="Additional literal term to block")
    parser.add_argument("--extra-regex", action="append", default=[], help="Additional regex to block")
    parser.add_argument("--json-output", help="Optional path to write JSON result")
    args = parser.parse_args()

    result = scan([Path(path).resolve() for path in args.paths], args.extra_term, args.extra_regex)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(output + "\n", encoding="utf-8")
    print(output)

    if result["status"] == "pass":
        return 0
    if result["status"] == "blocked":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
