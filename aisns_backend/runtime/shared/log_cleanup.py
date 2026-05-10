import asyncio
import logging
import os
import re
import shutil
import stat
from datetime import datetime, timedelta
from pathlib import Path


logger = logging.getLogger(__name__)


def _logs_root() -> Path:
    return Path(__file__).resolve().parents[1] / "logs"


def _on_rmtree_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        return


def cleanup_old_backend_logs(*, retention_days: int) -> dict:
    try:
        days = int(retention_days)
    except Exception:
        return {"success": False, "skipped": True, "reason": "invalid_retention_days"}

    if days < 0:
        return {"success": False, "skipped": True, "reason": "negative_retention_days"}

    root = _logs_root()
    if not root.exists() or not root.is_dir():
        return {"success": True, "deleted": 0, "failed": 0, "skipped": True, "reason": "logs_root_missing"}

    now = datetime.now()
    cutoff = now - timedelta(days=days)

    deleted = 0
    failed = 0

    logger.info(
        "Backend log cleanup starting: retention_days=%s",
        days
    )

    logger.info(
        "Backend log cleanup starting: root=%s",
        str(root)
    )


    logger.info(
        "Backend log cleanup starting: cutoff=%s",
        cutoff.strftime("%Y-%m-%d %H:%M:%S")
    )

    try:
        entries = list(root.iterdir())
    except Exception as e:
        logger.warning("Backend log cleanup failed to list root=%s err=%s", str(root), e)
        return {"success": False, "deleted": 0, "failed": 0, "skipped": True, "reason": "list_failed"}

    for p in entries:
        try:
            if not p.is_dir():
                continue
            name = p.name
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", name):
                continue

            try:
                folder_date = datetime.strptime(name, "%Y-%m-%d")
            except Exception:
                continue

            if folder_date >= cutoff:
                continue

            try:
                shutil.rmtree(p, onerror=_on_rmtree_error)
                deleted += 1
            except Exception as e:
                failed += 1
                logger.warning("Backend log cleanup failed to delete dir=%s err=%s", str(p), e)
        except Exception:
            failed += 1
            continue

    logger.info(
        "Backend log cleanup finished: retention_days=%s deleted=%s failed=%s",
        days,
        deleted,
        failed,
    )

    return {"success": failed == 0, "deleted": deleted, "failed": failed}


async def cleanup_old_backend_logs_async(*, retention_days: int) -> dict:
    return await asyncio.to_thread(cleanup_old_backend_logs, retention_days=retention_days)
