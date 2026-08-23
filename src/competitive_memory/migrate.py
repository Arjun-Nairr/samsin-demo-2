"""Applies every migrations/*.sql file, in sorted (numeric-prefix) order.
Not a migration framework - no tracking table, no versioning state, just
plain idempotent SQL files (CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT
EXISTS throughout) - safe to re-run, never destructive.

Run: cd src && python -m competitive_memory.migrate
"""
import sys
from pathlib import Path

import psycopg

from . import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def apply_migration() -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            for path in migration_files:
                cur.execute(path.read_text())
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
