#!/usr/bin/env python3
"""Remove deterministic E2E LearnedPath fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import delete

REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.models.learned_path import LearnedPath  # noqa: E402

DEDUP_PREFIX = "e2e:replay:"


def main() -> None:
    with SessionLocal() as session:
        result = session.execute(
            delete(LearnedPath).where(LearnedPath.dedup_key.like(f"{DEDUP_PREFIX}%"))
        )
        session.commit()
        print(f"Deleted {result.rowcount or 0} E2E replay LearnedPath fixture(s).")


if __name__ == "__main__":
    main()
