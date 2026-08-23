"""Sequence C persistence tests. No live Neon database, no network, no
credits - a small in-memory fake connection/cursor that implements the
exact semantics of db.py's two fixed SQL statements (INSERT/UPDATE/SELECT
against competitor_ads), so the row-level contract (first_seen_at
preserved, times_seen increments, started_at/is_active COALESCE, rollback
discards partial writes) can be verified without a real database.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import psycopg  # noqa: E402

from competitive_memory import db  # noqa: E402
from competitive_memory.service import refresh_competitive_memory  # noqa: E402

BRAND = "PacSun"
PAGE_ID = "7133041750"


def make_ad(
    ad_id,
    media_url="https://cdn.example/img.jpg",
    started_at="2026-01-01T00:00:00+00:00",
    is_active=True,
    body="body",
    page_id=PAGE_ID,
    collation_id=None,
    collation_count=None,
):
    return {
        "ad_id": ad_id,
        "brand": BRAND,
        "body": body,
        "headline": "",
        "cta": "Shop now",
        "media_type": "image",
        "media_url": media_url,
        "started_at": started_at,
        "is_active": is_active,
        "snapshot_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
        "page_id": page_id,
        "collation_id": collation_id,
        "collation_count": collation_count,
    }


class FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        self._conn._execute(sql, params)

    def fetchall(self):
        return self._conn._last_fetch

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeConnection:
    """In-memory stand-in for a psycopg connection, scoped exactly to the
    three statements db.py issues. `table` is the committed state (what a
    prior run would have persisted); `_pending` buffers writes until
    commit() applies them - so a rollback provably discards them."""

    def __init__(self, initial_rows=None, now=None, fail_after=None):
        self.table = {k: dict(v) for k, v in (initial_rows or {}).items()}
        self._pending = []
        self._last_fetch = []
        self.now = now or datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.fail_after = fail_after
        self._exec_count = 0
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def _execute(self, sql, params):
        self._exec_count += 1
        if self.fail_after is not None and self._exec_count > self.fail_after:
            raise psycopg.OperationalError("simulated failure")

        stripped = sql.strip()
        if stripped.startswith("SELECT"):
            (ids,) = params
            self._last_fetch = [(i,) for i in ids if i in self.table]
        elif stripped.startswith("INSERT"):
            row = {
                "brand": params["brand"],
                "body": params["body"],
                "headline": params["headline"],
                "cta": params["cta"],
                "media_type": params["media_type"],
                "latest_media_url": params["media_url"],
                "snapshot_url": params["snapshot_url"],
                "started_at": params["started_at"],
                "is_active": params["is_active"],
                "page_id": params["page_id"],
                "collation_id": params["collation_id"],
                "collation_count": params["collation_count"],
                "first_seen_at": self.now,
                "last_seen_at": self.now,
                "times_seen": 1,
                "analysis_status": "pending",
                "analysis_result": None,
                "analysis_attempts": 0,
                "analysis_error": None,
                "analyzed_at": None,
                "created_at": self.now,
                "updated_at": self.now,
            }
            self._pending.append(("insert", params["ad_id"], row))
        elif stripped.startswith("UPDATE") and "times_seen" in sql:
            ad_id = params["ad_id"]
            existing = self.table[ad_id]
            updated = dict(existing)
            updated["brand"] = params["brand"]
            updated["body"] = params["body"]
            updated["headline"] = params["headline"]
            updated["cta"] = params["cta"]
            updated["media_type"] = params["media_type"]
            updated["latest_media_url"] = params["media_url"]
            updated["snapshot_url"] = params["snapshot_url"]
            updated["started_at"] = params["started_at"] if params["started_at"] is not None else existing["started_at"]
            updated["is_active"] = params["is_active"] if params["is_active"] is not None else existing["is_active"]
            updated["page_id"] = params["page_id"] if params["page_id"] is not None else existing["page_id"]
            updated["collation_id"] = params["collation_id"] if params["collation_id"] is not None else existing["collation_id"]
            updated["collation_count"] = params["collation_count"] if params["collation_count"] is not None else existing["collation_count"]
            updated["last_seen_at"] = self.now
            updated["times_seen"] = existing["times_seen"] + 1
            updated["updated_at"] = self.now
            # first_seen_at, created_at, analysis_status: untouched
            self._pending.append(("update", ad_id, updated))
        else:
            raise AssertionError(f"unexpected SQL in FakeConnection: {sql!r}")

    def commit(self):
        for _op, ad_id, row in self._pending:
            self.table[ad_id] = row
        self._pending = []
        self.committed = True

    def rollback(self):
        self._pending = []
        self.rolled_back = True

    def close(self):
        self.closed = True


class UpsertNewAdTests(unittest.TestCase):
    def test_new_ad_is_inserted(self):
        conn = FakeConnection()
        result = db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(result["inserted_count"], 1)
        self.assertEqual(result["updated_count"], 0)
        self.assertEqual(len(result["ready_for_analysis"]), 1)
        self.assertEqual(result["ready_for_analysis"][0]["ad_id"], "A1")
        self.assertIn("A1", conn.table)
        self.assertEqual(conn.table["A1"]["times_seen"], 1)
        self.assertEqual(conn.table["A1"]["analysis_status"], "pending")
        self.assertTrue(conn.committed)


class UpsertExistingAdTests(unittest.TestCase):
    def test_repeated_ad_is_updated_not_duplicated(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("A1")])
        result = db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(len(conn.table), 1)  # not duplicated
        self.assertEqual(result["inserted_count"], 0)
        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(result["ready_for_analysis"], [])

    def test_first_seen_at_is_preserved(self):
        conn = FakeConnection(now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        db.upsert_ads(conn, [make_ad("A1")])
        original_first_seen = conn.table["A1"]["first_seen_at"]

        conn.now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(conn.table["A1"]["first_seen_at"], original_first_seen)

    def test_last_seen_at_changes_on_later_observation(self):
        conn = FakeConnection(now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        db.upsert_ads(conn, [make_ad("A1")])
        first_last_seen = conn.table["A1"]["last_seen_at"]

        conn.now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        db.upsert_ads(conn, [make_ad("A1")])
        self.assertNotEqual(conn.table["A1"]["last_seen_at"], first_last_seen)
        self.assertEqual(conn.table["A1"]["last_seen_at"], datetime(2026, 1, 2, tzinfo=timezone.utc))

    def test_times_seen_increments_exactly_once_per_run(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(conn.table["A1"]["times_seen"], 1)
        db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(conn.table["A1"]["times_seen"], 2)
        db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(conn.table["A1"]["times_seen"], 3)

    def test_existing_analysis_status_is_preserved(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("A1")])
        conn.table["A1"]["analysis_status"] = "processing"  # simulate a later analysis stage

        db.upsert_ads(conn, [make_ad("A1")])
        self.assertEqual(conn.table["A1"]["analysis_status"], "processing")

    def test_null_started_at_does_not_erase_existing_value(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("A1", started_at="2026-01-01T00:00:00+00:00")])
        self.assertEqual(conn.table["A1"]["started_at"], "2026-01-01T00:00:00+00:00")

        db.upsert_ads(conn, [make_ad("A1", started_at=None)])
        self.assertEqual(conn.table["A1"]["started_at"], "2026-01-01T00:00:00+00:00")

    def test_changed_signed_media_url_is_not_newly_discovered(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("A1", media_url="https://cdn.example/v1-signed-abc.jpg")])

        result = db.upsert_ads(conn, [make_ad("A1", media_url="https://cdn.example/v2-signed-xyz.jpg")])
        self.assertEqual(result["ready_for_analysis"], [])
        self.assertEqual(result["updated_count"], 1)
        # the URL itself is still refreshed, just not treated as "new"
        self.assertEqual(conn.table["A1"]["latest_media_url"], "https://cdn.example/v2-signed-xyz.jpg")


class MixedBatchTests(unittest.TestCase):
    def test_only_newly_inserted_ads_are_ready_for_analysis(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("OLD1")])  # seed one existing ad

        result = db.upsert_ads(conn, [make_ad("OLD1"), make_ad("NEW1"), make_ad("NEW2")])
        self.assertEqual(result["inserted_count"], 2)
        self.assertEqual(result["updated_count"], 1)
        self.assertEqual({a["ad_id"] for a in result["ready_for_analysis"]}, {"NEW1", "NEW2"})


class RollbackTests(unittest.TestCase):
    def test_database_failure_rolls_back_the_batch(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("OLD1")])  # 1 prior execute (the SELECT) - seed committed state

        # Fail partway through a 3-ad batch: allow the SELECT (1) and the
        # first INSERT (2) to succeed, then blow up.
        conn.fail_after = conn._exec_count + 2
        with self.assertRaises(db.PersistenceError):
            db.upsert_ads(conn, [make_ad("NEW1"), make_ad("NEW2"), make_ad("NEW3")])

        self.assertTrue(conn.rolled_back)
        # None of the new batch's ads were persisted - not even the one
        # whose INSERT ran before the failure.
        self.assertEqual(set(conn.table.keys()), {"OLD1"})


class DatabaseUrlTests(unittest.TestCase):
    def test_missing_database_url_raises_clear_error(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("DATABASE_URL", None)
            with mock.patch("competitive_memory.db.load_env", return_value={}):
                with self.assertRaises(db.PersistenceError) as ctx:
                    db.get_database_url()
        self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_env_var_overrides_dotenv(self):
        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://env-wins"}):
            with mock.patch("competitive_memory.db.load_env", return_value={"DATABASE_URL": "postgresql://dotenv-value"}):
                self.assertEqual(db.get_database_url(), "postgresql://env-wins")

    @mock.patch("competitive_memory.db.time.sleep")
    def test_connection_failure_never_exposes_the_dsn(self, _mock_sleep):
        secret_dsn = "postgresql://user:sk_super_secret_password@example.com/db"
        with mock.patch.dict("os.environ", {"DATABASE_URL": secret_dsn}):
            with mock.patch(
                "competitive_memory.db.psycopg.connect",
                side_effect=psycopg.OperationalError(f"connection failed: {secret_dsn}"),
            ):
                with self.assertRaises(db.PersistenceError) as ctx:
                    db.connect()
        self.assertNotIn("sk_super_secret_password", str(ctx.exception))
        self.assertNotIn(secret_dsn, str(ctx.exception))

    def test_query_failure_never_exposes_the_dsn(self):
        conn = FakeConnection(fail_after=0)
        with self.assertRaises(db.PersistenceError) as ctx:
            db.upsert_ads(conn, [make_ad("A1")])
        self.assertNotIn("DATABASE_URL", str(ctx.exception))
        self.assertNotIn("postgresql://", str(ctx.exception))


class ConnectRetryTests(unittest.TestCase):
    """db.connect()'s bounded timeout/retry policy. No real network -
    psycopg.connect itself is mocked throughout."""

    def test_connect_timeout_is_passed_to_psycopg(self):
        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake"}):
            with mock.patch("competitive_memory.db.psycopg.connect") as mock_connect:
                mock_connect.return_value = mock.sentinel.connection
                result = db.connect()
        self.assertIs(result, mock.sentinel.connection)
        mock_connect.assert_called_once_with(
            "postgresql://fake", connect_timeout=db.CONNECT_TIMEOUT_SECONDS
        )

    @mock.patch("competitive_memory.db.time.sleep")
    def test_first_attempt_fails_second_succeeds(self, mock_sleep):
        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake"}):
            with mock.patch(
                "competitive_memory.db.psycopg.connect",
                side_effect=[psycopg.OperationalError("cold start"), mock.sentinel.connection],
            ) as mock_connect:
                result = db.connect()
        self.assertIs(result, mock.sentinel.connection)
        self.assertEqual(mock_connect.call_count, 2)
        mock_sleep.assert_called_once_with(db.CONNECT_RETRY_DELAY_SECONDS)

    @mock.patch("competitive_memory.db.time.sleep")
    def test_both_attempts_fail_raises_persistence_error(self, mock_sleep):
        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake"}):
            with mock.patch(
                "competitive_memory.db.psycopg.connect",
                side_effect=psycopg.OperationalError("still down"),
            ) as mock_connect:
                with self.assertRaises(db.PersistenceError) as ctx:
                    db.connect()
        self.assertEqual(mock_connect.call_count, db.MAX_CONNECT_ATTEMPTS)
        self.assertIn(str(db.MAX_CONNECT_ATTEMPTS), str(ctx.exception))
        self.assertIn("OperationalError", str(ctx.exception))

    @mock.patch("competitive_memory.db.time.sleep")
    def test_exactly_one_retry_delay_occurs(self, mock_sleep):
        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake"}):
            with mock.patch(
                "competitive_memory.db.psycopg.connect",
                side_effect=psycopg.OperationalError("down"),
            ):
                with self.assertRaises(db.PersistenceError):
                    db.connect()
        self.assertEqual(mock_sleep.call_count, 1)  # MAX_CONNECT_ATTEMPTS - 1

    def test_non_operational_error_is_not_retried(self):
        # A non-connection-level error (e.g. a programming mistake) should
        # propagate immediately, not be mistaken for a transient blip.
        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake"}):
            with mock.patch(
                "competitive_memory.db.psycopg.connect", side_effect=ValueError("not a connection issue")
            ) as mock_connect:
                with self.assertRaises(ValueError):
                    db.connect()
        self.assertEqual(mock_connect.call_count, 1)


class RefreshConnectionOrderTests(unittest.TestCase):
    """Connect-before-fetch and connection-lifecycle behavior in
    refresh_competitive_memory(). db.connect/db.upsert_ads/fetch are all
    mocked - no real network, no real database."""

    def _patched(self, connect_side_effect=None, fetch_side_effect=None, upsert_side_effect=None):
        calls = []

        def fake_connect():
            calls.append("connect")
            if connect_side_effect:
                raise connect_side_effect
            conn = mock.MagicMock()
            conn.close = lambda: calls.append("close")
            return conn

        def fake_fetch():
            calls.append("fetch")
            if fetch_side_effect:
                raise fetch_side_effect
            return {"count": 1, "ads": [make_ad("A1")]}

        def fake_upsert(conn, ads):
            calls.append("upsert")
            if upsert_side_effect:
                raise upsert_side_effect
            return {"inserted_count": 1, "updated_count": 0, "ready_for_analysis": ads}

        return calls, fake_connect, fake_fetch, fake_upsert

    def test_connects_before_fetching(self):
        calls, fake_connect, fake_fetch, fake_upsert = self._patched()
        with mock.patch("competitive_memory.service.db.connect", side_effect=fake_connect), \
             mock.patch("competitive_memory.service.fetch_and_normalize_ads", side_effect=fake_fetch), \
             mock.patch("competitive_memory.service.db.upsert_ads", side_effect=fake_upsert):
            refresh_competitive_memory()
        self.assertEqual(calls, ["connect", "fetch", "upsert", "close"])

    def test_failed_connection_means_fetch_is_never_called(self):
        calls, fake_connect, fake_fetch, fake_upsert = self._patched(
            connect_side_effect=db.PersistenceError("down")
        )
        with mock.patch("competitive_memory.service.db.connect", side_effect=fake_connect), \
             mock.patch("competitive_memory.service.fetch_and_normalize_ads", side_effect=fake_fetch), \
             mock.patch("competitive_memory.service.db.upsert_ads", side_effect=fake_upsert):
            with self.assertRaises(db.PersistenceError):
                refresh_competitive_memory()
        self.assertEqual(calls, ["connect"])  # fetch and upsert never ran; no credit spent

    def test_successful_connection_allows_fetch(self):
        calls, fake_connect, fake_fetch, fake_upsert = self._patched()
        with mock.patch("competitive_memory.service.db.connect", side_effect=fake_connect), \
             mock.patch("competitive_memory.service.fetch_and_normalize_ads", side_effect=fake_fetch), \
             mock.patch("competitive_memory.service.db.upsert_ads", side_effect=fake_upsert):
            refresh_competitive_memory()
        self.assertIn("fetch", calls)

    def test_fetch_failure_closes_an_owned_connection(self):
        from ad_fetcher.scrapecreators_client import ScrapeCreatorsError

        calls, fake_connect, fake_fetch, fake_upsert = self._patched(
            fetch_side_effect=ScrapeCreatorsError("provider down")
        )
        with mock.patch("competitive_memory.service.db.connect", side_effect=fake_connect), \
             mock.patch("competitive_memory.service.fetch_and_normalize_ads", side_effect=fake_fetch), \
             mock.patch("competitive_memory.service.db.upsert_ads", side_effect=fake_upsert):
            with self.assertRaises(ScrapeCreatorsError):
                refresh_competitive_memory()
        self.assertEqual(calls, ["connect", "fetch", "close"])

    def test_upsert_failure_closes_an_owned_connection(self):
        calls, fake_connect, fake_fetch, fake_upsert = self._patched(
            upsert_side_effect=db.PersistenceError("rolled back")
        )
        with mock.patch("competitive_memory.service.db.connect", side_effect=fake_connect), \
             mock.patch("competitive_memory.service.fetch_and_normalize_ads", side_effect=fake_fetch), \
             mock.patch("competitive_memory.service.db.upsert_ads", side_effect=fake_upsert):
            with self.assertRaises(db.PersistenceError):
                refresh_competitive_memory()
        self.assertEqual(calls, ["connect", "fetch", "upsert", "close"])

    def test_successful_refresh_closes_an_owned_connection(self):
        calls, fake_connect, fake_fetch, fake_upsert = self._patched()
        with mock.patch("competitive_memory.service.db.connect", side_effect=fake_connect), \
             mock.patch("competitive_memory.service.fetch_and_normalize_ads", side_effect=fake_fetch), \
             mock.patch("competitive_memory.service.db.upsert_ads", side_effect=fake_upsert):
            refresh_competitive_memory()
        self.assertIn("close", calls)

    def test_injected_connection_is_never_closed(self):
        conn = FakeConnection()
        fake_fetched = {"count": 1, "ads": [make_ad("A1")]}
        with mock.patch("competitive_memory.service.fetch_and_normalize_ads", return_value=fake_fetched):
            refresh_competitive_memory(conn=conn)
        self.assertFalse(conn.closed)


class ServiceJsonOutputTests(unittest.TestCase):
    def test_ready_for_analysis_contains_only_newly_inserted_ads(self):
        conn = FakeConnection()
        db.upsert_ads(conn, [make_ad("OLD1")])  # seed an existing ad

        fake_fetched = {"count": 2, "ads": [make_ad("OLD1"), make_ad("NEW1")]}
        with mock.patch("competitive_memory.service.fetch_and_normalize_ads", return_value=fake_fetched):
            output = refresh_competitive_memory(conn=conn)

        self.assertEqual(output["fetched_count"], 2)
        self.assertEqual(output["inserted_count"], 1)
        self.assertEqual(output["updated_count"], 1)
        self.assertEqual(output["ready_for_analysis_count"], 1)
        self.assertEqual([a["ad_id"] for a in output["ready_for_analysis"]], ["NEW1"])
        # Sequence A's contract key is `media_url`, not the DB column name.
        self.assertIn("media_url", output["ready_for_analysis"][0])
        self.assertNotIn("latest_media_url", output["ready_for_analysis"][0])
        self.assertFalse(conn.closed)  # injected connection - caller owns it, not us


if __name__ == "__main__":
    unittest.main()
