"""Sequence D, Part 3: the analysis-persistence boundary. No AI model call
happens here or anywhere in this repository - this is only the contract a
future external agent (OpenClaw) will read pending work from and write
results back through. Each function owns and closes its own connection -
same one-connection-per-invocation pattern as service.py's refresh."""
from . import config, db


def list_pending_analysis(limit: int | None = None) -> list:
    limit = limit or config.PENDING_BATCH_SIZE
    conn = db.connect()
    try:
        return db.list_pending_analysis(conn, page_id=config.ACTIVE_PAGE_ID, limit=limit)
    finally:
        conn.close()


def save_analysis(ad_id: str, result: dict) -> None:
    conn = db.connect()
    try:
        db.save_analysis_result(conn, ad_id=ad_id, page_id=config.ACTIVE_PAGE_ID, result=result)
    finally:
        conn.close()


def mark_failed(ad_id: str, error_message: str) -> None:
    conn = db.connect()
    try:
        db.mark_analysis_failed(conn, ad_id=ad_id, page_id=config.ACTIVE_PAGE_ID, error_message=error_message)
    finally:
        conn.close()
