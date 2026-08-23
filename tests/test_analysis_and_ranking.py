"""Sequence D, Parts 2-4: weighting evidence scoping, the analysis-
persistence boundary, and deterministic ranking. No live database, no live
ScrapeCreators request, no live model call - a small in-memory fake tuned
to db.py's actual SQL text (matched by distinguishing substrings), plus
pure-function tests for ranking.py's scoring.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from competitive_memory import config, db, ranking  # noqa: E402
from competitive_memory.analysis import (  # noqa: E402
    list_pending_analysis,
    mark_failed,
    save_analysis,
)

PAGE_ID = config.ACTIVE_PAGE_ID  # "7133041750" - the configured PacSun page
OTHER_PAGE_ID = "222222222222222"  # the old Aelfric Eden page_id, pre-Sequence-D


def make_row(
    ad_id,
    page_id=PAGE_ID,
    media_type="image",
    analysis_status="pending",
    media_url="https://cdn.example/img.jpg",
    collation_count=None,
    started_at=None,
    first_seen_at="2026-01-01T00:00:00+00:00",
    last_seen_at="2026-01-01T00:00:00+00:00",
    analysis_result=None,
    analysis_attempts=0,
):
    return {
        "ad_id": ad_id,
        "brand": "PacSun",
        "body": "body",
        "headline": "",
        "cta": "Shop now",
        "media_type": media_type,
        "media_url": media_url,
        "snapshot_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
        "started_at": started_at,
        "is_active": True,
        "page_id": page_id,
        "collation_id": None,
        "collation_count": collation_count,
        "first_seen_at": first_seen_at,
        "last_seen_at": last_seen_at,
        "times_seen": 1,
        "analysis_status": analysis_status,
        "analysis_attempts": analysis_attempts,
        "analysis_result": analysis_result,
    }


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._result = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        stripped = sql.strip()
        table = self.conn.table

        if stripped.startswith("SELECT") and "analysis_status IN" in stripped:
            page_id, limit = params["page_id"], params["limit"]
            rows = [
                r for r in table.values()
                if r["page_id"] == page_id
                and r["media_type"] == "image"
                and r["analysis_status"] in ("pending", "failed")
                and r.get("media_url")
            ]
            rows.sort(key=lambda r: (r["analysis_status"] != "pending", r["first_seen_at"]))
            self._result = [dict(r) for r in rows[:limit]]

        elif stripped.startswith("SELECT") and "analysis_status = 'complete'" in stripped:
            page_id = params["page_id"]
            self._result = [dict(r) for r in table.values() if r["page_id"] == page_id and r["analysis_status"] == "complete"]

        elif stripped.startswith("UPDATE") and "analysis_status = 'complete'" in stripped:
            row = table.get(params["ad_id"])
            if row is None or row["page_id"] != params["page_id"]:
                self._result = []
            else:
                row["analysis_status"] = "complete"
                row["analysis_result"] = params["result"].obj if hasattr(params["result"], "obj") else params["result"]
                row["analysis_error"] = None
                row["analysis_attempts"] = row.get("analysis_attempts", 0) + 1
                self._result = [(row["ad_id"],)]

        elif stripped.startswith("UPDATE") and "analysis_status = 'failed'" in stripped:
            row = table.get(params["ad_id"])
            if row is None or row["page_id"] != params["page_id"]:
                self._result = []
            else:
                row["analysis_status"] = "failed"
                row["analysis_error"] = params["error"]
                row["analysis_attempts"] = row.get("analysis_attempts", 0) + 1
                self._result = [(row["ad_id"],)]

        else:
            raise AssertionError(f"unexpected SQL in fake: {sql!r}")

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result[0] if self._result else None


class FakeConnection:
    def __init__(self, rows=None):
        self.table = {r["ad_id"]: dict(r) for r in (rows or [])}
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, row_factory=None):
        return _FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _with_connect_returning(conn):
    return mock.patch("competitive_memory.db.connect", return_value=conn)


class PendingScopingTests(unittest.TestCase):
    def test_scoped_to_configured_competitor_excludes_old_rows(self):
        rows = [
            make_row("NEW1", page_id=PAGE_ID),
            make_row("OLD1", page_id=OTHER_PAGE_ID),  # pre-Sequence-D Aelfric row
        ]
        result = db.list_pending_analysis(FakeConnection(rows), page_id=PAGE_ID, limit=10)
        self.assertEqual([r["ad_id"] for r in result], ["NEW1"])

    def test_excludes_non_image_media_type(self):
        rows = [make_row("VID1", media_type="video")]
        result = db.list_pending_analysis(FakeConnection(rows), page_id=PAGE_ID, limit=10)
        self.assertEqual(result, [])

    def test_excludes_rows_without_usable_media_url(self):
        rows = [make_row("NOURL", media_url=None)]
        result = db.list_pending_analysis(FakeConnection(rows), page_id=PAGE_ID, limit=10)
        self.assertEqual(result, [])

    def test_pending_prioritized_over_failed_retries(self):
        rows = [
            make_row("F1", analysis_status="failed", first_seen_at="2026-01-01T00:00:00+00:00"),
            make_row("P1", analysis_status="pending", first_seen_at="2026-01-02T00:00:00+00:00"),
        ]
        result = db.list_pending_analysis(FakeConnection(rows), page_id=PAGE_ID, limit=10)
        self.assertEqual([r["ad_id"] for r in result], ["P1", "F1"])

    def test_excludes_already_complete_ads(self):
        rows = [make_row("DONE1", analysis_status="complete")]
        result = db.list_pending_analysis(FakeConnection(rows), page_id=PAGE_ID, limit=10)
        self.assertEqual(result, [])

    def test_pending_work_is_queryable_independent_of_any_prior_ready_for_analysis_list(self):
        # Simulates rows that already existed in Neon from a previous,
        # unrelated run - list_pending_analysis must find them purely by
        # querying the table, with no dependency on an in-memory list from
        # whatever process originally inserted them.
        rows = [make_row("SURVIVOR1"), make_row("SURVIVOR2")]
        conn = FakeConnection(rows)
        result = db.list_pending_analysis(conn, page_id=PAGE_ID, limit=10)
        self.assertEqual({r["ad_id"] for r in result}, {"SURVIVOR1", "SURVIVOR2"})

    def test_analysis_module_uses_connect_and_closes_it(self):
        conn = FakeConnection([make_row("A1")])
        with _with_connect_returning(conn):
            result = list_pending_analysis(limit=5)
        self.assertEqual([r["ad_id"] for r in result], ["A1"])
        self.assertTrue(conn.closed)


class SaveAnalysisTests(unittest.TestCase):
    def test_successful_save_marks_complete(self):
        conn = FakeConnection([make_row("A1")])
        db.save_analysis_result(conn, ad_id="A1", page_id=PAGE_ID, result={"score": "high"})
        self.assertEqual(conn.table["A1"]["analysis_status"], "complete")
        self.assertEqual(conn.table["A1"]["analysis_result"], {"score": "high"})
        self.assertIsNone(conn.table["A1"]["analysis_error"])
        self.assertTrue(conn.committed)

    def test_rejects_non_object_result(self):
        conn = FakeConnection([make_row("A1")])
        for bad_result in ["a plain string", ["a", "list"], 42, None]:
            with self.assertRaises(db.PersistenceError):
                db.save_analysis_result(conn, ad_id="A1", page_id=PAGE_ID, result=bad_result)

    def test_rejects_unknown_ad_id(self):
        conn = FakeConnection([])
        with self.assertRaises(db.PersistenceError) as ctx:
            db.save_analysis_result(conn, ad_id="GHOST", page_id=PAGE_ID, result={"ok": True})
        self.assertIn("Unknown ad_id", str(ctx.exception))

    def test_rejects_ad_id_belonging_to_a_different_competitor(self):
        # Same ad_id namespace, wrong page_id - must be treated as unknown,
        # not silently accepted across competitor boundaries.
        conn = FakeConnection([make_row("SHARED1", page_id=OTHER_PAGE_ID)])
        with self.assertRaises(db.PersistenceError):
            db.save_analysis_result(conn, ad_id="SHARED1", page_id=PAGE_ID, result={"ok": True})

    def test_analysis_module_save_uses_connect_and_closes_it(self):
        conn = FakeConnection([make_row("A1")])
        with _with_connect_returning(conn):
            save_analysis("A1", {"ok": True})
        self.assertTrue(conn.closed)
        self.assertEqual(conn.table["A1"]["analysis_status"], "complete")


class MarkFailedTests(unittest.TestCase):
    def test_marks_failed_and_records_error(self):
        conn = FakeConnection([make_row("A1")])
        db.mark_analysis_failed(conn, ad_id="A1", page_id=PAGE_ID, error_message="model timeout")
        self.assertEqual(conn.table["A1"]["analysis_status"], "failed")
        self.assertEqual(conn.table["A1"]["analysis_error"], "model timeout")

    def test_a_failed_analysis_is_not_permanently_lost(self):
        conn = FakeConnection([make_row("A1")])
        db.mark_analysis_failed(conn, ad_id="A1", page_id=PAGE_ID, error_message="first failure")
        # Still retryable via list_pending_analysis afterward:
        pending = db.list_pending_analysis(conn, page_id=PAGE_ID, limit=10)
        self.assertEqual([r["ad_id"] for r in pending], ["A1"])

    def test_analysis_attempts_increments_on_each_failure(self):
        conn = FakeConnection([make_row("A1")])
        db.mark_analysis_failed(conn, ad_id="A1", page_id=PAGE_ID, error_message="attempt 1")
        db.mark_analysis_failed(conn, ad_id="A1", page_id=PAGE_ID, error_message="attempt 2")
        self.assertEqual(conn.table["A1"]["analysis_attempts"], 2)

    def test_rejects_unknown_ad_id(self):
        conn = FakeConnection([])
        with self.assertRaises(db.PersistenceError):
            db.mark_analysis_failed(conn, ad_id="GHOST", page_id=PAGE_ID, error_message="n/a")

    def test_analysis_module_mark_failed_uses_connect_and_closes_it(self):
        conn = FakeConnection([make_row("A1")])
        with _with_connect_returning(conn):
            mark_failed("A1", "boom")
        self.assertTrue(conn.closed)
        self.assertEqual(conn.table["A1"]["analysis_status"], "failed")


class RankingScoringTests(unittest.TestCase):
    NOW = datetime(2026, 3, 1, tzinfo=timezone.utc)

    def test_deterministic_weight_calculation(self):
        # started 10 days ago, seen running for 10 days, collation_count=5 (cap)
        ad = make_row(
            "A1",
            analysis_status="complete",
            started_at=(self.NOW - timedelta(days=10)).isoformat(),
            first_seen_at=(self.NOW - timedelta(days=10)).isoformat(),
            last_seen_at=self.NOW.isoformat(),
            collation_count=5,
            analysis_result={"ok": True},
        )
        scored = ranking._score_ad(ad, self.NOW)
        expected_recency = 1 - 10 / config.RECENCY_WINDOW_DAYS
        expected_longevity = 10 / config.LONGEVITY_WINDOW_DAYS
        expected_recurrence = 1.0  # collation_count >= RECURRENCE_CAP
        expected_weight = (
            config.RECENCY_WEIGHT * expected_recency
            + config.LONGEVITY_WEIGHT * expected_longevity
            + config.RECURRENCE_WEIGHT * expected_recurrence
        )
        self.assertAlmostEqual(scored["component_scores"]["recency"], expected_recency, places=4)
        self.assertAlmostEqual(scored["component_scores"]["longevity"], expected_longevity, places=4)
        self.assertAlmostEqual(scored["component_scores"]["recurrence"], expected_recurrence, places=4)
        self.assertAlmostEqual(scored["weight"], expected_weight, places=4)

    def test_missing_started_at_falls_back_to_first_seen_at(self):
        ad = make_row(
            "A1",
            started_at=None,
            first_seen_at=(self.NOW - timedelta(days=5)).isoformat(),
            last_seen_at=self.NOW.isoformat(),
        )
        scored = ranking._score_ad(ad, self.NOW)
        expected_recency = 1 - 5 / config.RECENCY_WINDOW_DAYS
        self.assertAlmostEqual(scored["component_scores"]["recency"], expected_recency, places=4)

    def test_missing_collation_count_is_neutral_zero_not_invented(self):
        ad = make_row("A1", collation_count=None)
        scored = ranking._score_ad(ad, self.NOW)
        self.assertEqual(scored["component_scores"]["recurrence"], 0.0)

    def test_times_seen_is_never_used_for_recurrence(self):
        # times_seen isn't even read by _score_ad - confirm a huge
        # times_seen with no collation_count still scores recurrence 0.
        ad = make_row("A1", collation_count=None)
        ad["times_seen"] = 999
        scored = ranking._score_ad(ad, self.NOW)
        self.assertEqual(scored["component_scores"]["recurrence"], 0.0)

    def test_old_ad_scores_zero_recency_not_negative(self):
        ad = make_row(
            "A1",
            started_at=(self.NOW - timedelta(days=9999)).isoformat(),
            first_seen_at=(self.NOW - timedelta(days=9999)).isoformat(),
            last_seen_at=self.NOW.isoformat(),
        )
        scored = ranking._score_ad(ad, self.NOW)
        self.assertEqual(scored["component_scores"]["recency"], 0.0)


class RankedContextTests(unittest.TestCase):
    NOW_ROW_KWARGS = dict(
        started_at=datetime.now(timezone.utc).isoformat(),
        last_seen_at=datetime.now(timezone.utc).isoformat(),
    )

    def test_only_completed_ads_for_configured_competitor_are_considered(self):
        rows = [
            make_row("DONE1", analysis_status="complete", collation_count=5, **self.NOW_ROW_KWARGS),
            make_row("PENDING1", analysis_status="pending", **self.NOW_ROW_KWARGS),
            make_row("OTHERCOMP1", analysis_status="complete", page_id=OTHER_PAGE_ID, **self.NOW_ROW_KWARGS),
        ]
        conn = FakeConnection(rows)
        output = ranking.compute_ranked_context(conn=conn)
        self.assertEqual([c["ad_id"] for c in output["context"]], ["DONE1"])

    def test_below_threshold_ads_are_dropped(self):
        # started long enough ago, no recurrence -> weight below MIN_WEIGHT_THRESHOLD
        stale = make_row(
            "STALE1",
            analysis_status="complete",
            started_at=(datetime.now(timezone.utc) - timedelta(days=9999)).isoformat(),
            first_seen_at=(datetime.now(timezone.utc) - timedelta(days=9999)).isoformat(),
            last_seen_at=(datetime.now(timezone.utc) - timedelta(days=9999)).isoformat(),
            collation_count=None,
        )
        conn = FakeConnection([stale])
        output = ranking.compute_ranked_context(conn=conn)
        self.assertEqual(output["context"], [])

    def test_top_n_is_respected_and_ordered_by_weight_descending(self):
        rows = [
            make_row(f"AD{i}", analysis_status="complete", collation_count=i, **self.NOW_ROW_KWARGS)
            for i in range(config.TOP_N + 5)
        ]
        conn = FakeConnection(rows)
        output = ranking.compute_ranked_context(conn=conn)
        self.assertEqual(len(output["context"]), config.TOP_N)
        weights = [c["weight"] for c in output["context"]]
        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_context_payload_includes_required_fields(self):
        row = make_row("A1", analysis_status="complete", analysis_result={"headline_ok": True}, **self.NOW_ROW_KWARGS)
        conn = FakeConnection([row])
        output = ranking.compute_ranked_context(conn=conn)
        item = output["context"][0]
        for key in ("ad_id", "brand", "body", "headline", "cta", "media_type", "media_url",
                    "snapshot_url", "analysis_result", "weight", "component_scores"):
            self.assertIn(key, item)


class MigrateTests(unittest.TestCase):
    def test_applies_every_migration_file_as_one_statement_each(self):
        from competitive_memory import migrate

        executed = []

        class _RecordingCursor:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql):
                executed.append(sql)

        class _RecordingConn:
            def cursor(self):
                return _RecordingCursor()

            def commit(self):
                self.committed = True

            def rollback(self):
                pass

            def close(self):
                self.closed = True

        conn = _RecordingConn()
        with mock.patch("competitive_memory.db.connect", return_value=conn):
            migrate.apply_migration()

        self.assertEqual(len(executed), len(list(migrate.MIGRATIONS_DIR.glob("*.sql"))))
        self.assertTrue(any("competitor_ads" in sql for sql in executed))
        self.assertTrue(any("analysis_result" in sql for sql in executed))
        self.assertTrue(conn.committed)
        self.assertTrue(conn.closed)


if __name__ == "__main__":
    unittest.main()
