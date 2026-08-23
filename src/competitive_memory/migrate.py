"""Applies migrations/0001_create_competitor_ads.sql. Not a migration
framework - one plain SQL file, one small script, safe to re-run
(CREATE TABLE IF NOT EXISTS), never destructive (no drops, no deletes).

Run: cd src && python -m competitive_memory.migrate
"""
import sys
from pathlib import Path

import psycopg

from . import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATION_PATH = PROJECT_ROOT / "migrations" / "0001_create_competitor_ads.sql"


def apply_migration() -> None:
    sql = MIGRATION_PATH.read_text()
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except psycopg.Error as exc:
        conn.rollback()
        raise db.PersistenceError(
            f"Migration failed and was rolled back ({exc.__class__.__name__})."
        ) from exc
    finally:
        conn.close()


def main() -> int:
    try:
        apply_migration()
    except db.PersistenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("migration applied: competitor_ads table is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
