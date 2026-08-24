"""Sequence F: the one thing the skill needs that isn't already an
existing CLI/module - a stale-aware exclusive run lock so a manual
invocation and the 12-hour OpenClaw automation can never overlap.

No custom resumable framework here (per the brief) - this file does
exactly one job: exclusive-create/read/release one lock file. Run
tracking itself is just the run-directory JSON/log files the skill
writes directly, plus Neon's own analysis_status columns and OpenClaw's
own automation run history - none of that is duplicated here.

Exclusive creation via open(path, "x") is the portable, stdlib way to get
an atomic create-or-fail on both POSIX and Windows (backed by O_CREAT|
O_EXCL / CreateFile with CREATE_NEW under the hood) - no flock/fcntl
(POSIX-only) and no third-party lock library needed for one lock file.
"""
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOCK_PATH = PROJECT_ROOT / ".samsin_pipeline.lock"

STALE_AFTER_SECONDS = 60 * 60  # 60 minutes, per the skill's run boundary


class LockHeldError(Exception):
    """Raised when a fresh (non-stale) lock is already held."""


def read_lock(lock_path: Path = LOCK_PATH) -> dict | None:
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        # A corrupt/unreadable lock file is treated as stale-replaceable,
        # not a crash - see acquire().
        return {}


def acquire(run_id: str, mode: str, lock_path: Path = LOCK_PATH) -> dict:
    """Exclusive-create the lock file. If one already exists, replace it
    only when it's older than STALE_AFTER_SECONDS; otherwise raise
    LockHeldError. Returns the payload written, plus stale_replaced."""
    payload = {
        "run_id": run_id,
        "mode": mode,
        "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "acquired_epoch": time.time(),
    }
    stale_replaced = False

    try:
        with open(lock_path, "x", encoding="utf-8") as f:
            json.dump(payload, f)
    except FileExistsError:
        existing = read_lock(lock_path) or {}
        age = time.time() - existing.get("acquired_epoch", 0)
        if age < STALE_AFTER_SECONDS:
            raise LockHeldError(
                f"lock held by run_id={existing.get('run_id', 'unknown')} "
                f"(age={int(age)}s, mode={existing.get('mode', 'unknown')}); "
                f"not stale until {STALE_AFTER_SECONDS}s."
            )
        lock_path.unlink()
        with open(lock_path, "x", encoding="utf-8") as f:
            json.dump(payload, f)
        stale_replaced = True

    return {**payload, "stale_replaced": stale_replaced}


def release(lock_path: Path = LOCK_PATH) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
