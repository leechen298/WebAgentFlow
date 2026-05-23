#!/usr/bin/env python3
"""Scan product runtime/prompts for eval target-specific forbidden tokens.

Exit codes:
  0: pass
  1: fail, matches found
  2: blocked, invalid manifest or scan precondition failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
    ".gz", ".tar", ".tgz", ".woff", ".woff2", ".ttf", ".otf", ".pyc",
    ".sqlite", ".db",
}

DEFAULT_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build", ".next",
    ".turbo", "__pycache__", ".pytest_cache", ".ruff_cache",
}


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report as blocked data issue
        raise ValueError(f"failed to read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def _as_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"manifest field {key!r} must be a list of strings")
    return value


def _iter_files(root: Path, scan_path: Path) -> list[Path]:
    if scan_path.is_file():
        return [scan_path]
    paths: list[Path] = []
    for current_root, dirs, filenames in os.walk(scan_path):
        dirs[:] = [name for name in dirs if name not in DEFAULT_SKIP_DIRS]
        for filename in filenames:
            path = Path(current_root) / filename
            if path.suffix.lower() in BINARY_EXTENSIONS:
                continue
            try:
                path.relative_to(root)
            except ValueError:
                continue
            paths.append(path)
    return paths


def _line_matches(text: str, tokens: list[str]) -> list[tuple[int, str, str]]:
    matches: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for token in tokens:
            if token and token in line:
                matches.append((line_no, token, line.strip()))
    return matches


def scan(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    forbidden_tokens = _as_str_list(manifest, "forbidden_tokens")
    forbidden_paths = _as_str_list(manifest, "forbidden_paths")
    allowed_paths = _as_str_list(manifest, "allowed_paths")

    if not forbidden_tokens:
        raise ValueError("manifest forbidden_tokens is empty")
    if not forbidden_paths:
        raise ValueError("manifest forbidden_paths is empty")

    allowed_resolved = [(root / path).resolve() for path in allowed_paths]
    matches: list[dict[str, Any]] = []
    missing_paths: list[str] = []

    for raw_scan_path in forbidden_paths:
        scan_path = (root / raw_scan_path).resolve()
        if not scan_path.exists():
            missing_paths.append(raw_scan_path)
            continue
        for file_path in _iter_files(root, scan_path):
            resolved = file_path.resolve()
            if any(resolved == allowed or resolved.is_relative_to(allowed) for allowed in allowed_resolved):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
            except Exception:
                continue
            for line_no, token, line in _line_matches(text, forbidden_tokens):
                matches.append(
                    {
                        "path": str(file_path.relative_to(root)),
                        "line": line_no,
                        "token": token,
                        "reason": "target-specific runtime/prompt constant",
                        "preview": line[:240],
                    }
                )

    status = "fail" if matches else "pass"
    return {
        "status": status,
        "target_name": manifest.get("target_name"),
        "matches": matches,
        "missing_forbidden_paths": missing_paths,
        "match_count": len(matches),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to target manifest JSON")
    parser.add_argument("--root", default=".", help="Repository root, default current directory")
    parser.add_argument("--json-output", help="Optional path to write JSON result")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve()

    try:
        manifest = _load_manifest(manifest_path)
        result = scan(root, manifest)
    except ValueError as exc:
        result = {"status": "blocked", "reason": str(exc), "matches": [], "match_count": 0}
        exit_code = 2
    else:
        exit_code = 1 if result["status"] == "fail" else 0

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
