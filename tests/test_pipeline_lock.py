"""Sequence F: one focused test for the stale-aware exclusive run lock.
No network, no filesystem outside a temp dir per test.
"""
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline_run.lock import LockHeldError, acquire, read_lock, release  # noqa: E402


class LockTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.lock_path = Path(self._tmp.name) / ".samsin_pipeline.lock"

    def tearDown(self):
        self._tmp.cleanup()

    def test_acquire_then_release_round_trips(self):
        result = acquire("run-1", "dry-run", lock_path=self.lock_path)
        self.assertEqual(result["run_id"], "run-1")
        self.assertEqual(result["mode"], "dry-run")
        self.assertFalse(result["stale_replaced"])
        self.assertTrue(self.lock_path.exists())

        release(lock_path=self.lock_path)
        self.assertFalse(self.lock_path.exists())

    def test_fresh_lock_blocks_a_second_acquire(self):
        acquire("run-1", "dry-run", lock_path=self.lock_path)
        with self.assertRaises(LockHeldError) as ctx:
            acquire("run-2", "dry-run", lock_path=self.lock_path)
        self.assertIn("run-1", str(ctx.exception))

    def test_stale_lock_is_replaced_and_reported(self):
        acquire("run-1", "dry-run", lock_path=self.lock_path)
        # Backdate the lock past the staleness threshold instead of
        # sleeping 60 real minutes.
        stale = read_lock(self.lock_path)
        stale["acquired_epoch"] = time.time() - 3601
        self.lock_path.write_text(__import__("json").dumps(stale), encoding="utf-8")

        result = acquire("run-2", "dry-run", lock_path=self.lock_path)
        self.assertEqual(result["run_id"], "run-2")
        self.assertTrue(result["stale_replaced"])

    def test_release_when_no_lock_exists_is_a_no_op(self):
        release(lock_path=self.lock_path)  # must not raise


if __name__ == "__main__":
    unittest.main()
