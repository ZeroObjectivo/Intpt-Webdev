import datetime
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ARCHIVE_RETENTION_DAYS = 90
_LAST_PURGE_TS = 0.0


def _iso_utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _json_safe(value: Any):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def _select_all_eq(client, table: str, column: str, value: Any):
    res = client.table(table).select("*").eq(column, value).execute()
    return res.data or []


def purge_expired_archived_posts(client, limit: int = 200) -> int:
    """
    Best-effort cleanup for archives past retention window.
    Safe to call often; no-op if table/data is unavailable.
    """
    try:
        now_iso = _iso_utc_now()
        expired_res = client.table('archived_posts')\
            .select("id")\
            .lt("purge_after", now_iso)\
            .limit(limit).execute()
        expired_ids = [row.get('id') for row in (expired_res.data or []) if row.get('id')]
        if not expired_ids:
            return 0
        client.table('archived_posts').delete().in_("id", expired_ids).execute()
        return len(expired_ids)
    except Exception as e:
        logger.warning("Archive cleanup skipped: %s", e)
        return 0


def maybe_purge_expired_archived_posts(client, interval_seconds: int = 3600, limit: int = 200) -> int:
    """
    Throttled purge helper for request paths.
    Executes at most once per interval in the running process.
    """
    global _LAST_PURGE_TS
    now_ts = time.time()
    if _LAST_PURGE_TS and (now_ts - _LAST_PURGE_TS) < max(60, int(interval_seconds)):
        return 0
    _LAST_PURGE_TS = now_ts
    return purge_expired_archived_posts(client, limit=limit)


def archive_post_snapshot(
    client,
    post_id: str,
    *,
    deleted_by: Optional[str] = None,
    deleted_by_role: Optional[str] = None,
    source: str = "admin",
    reason: Optional[str] = None,
    note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Captures post + related rows into archived_posts before destructive deletion.
    Returns the post row when archived or None if post not found.
    """
    post_res = client.table('posts').select("*").eq("id", post_id).limit(1).execute()
    post_rows = post_res.data or []
    if not post_rows:
        return None

    post_row = post_rows[0]
    payload = {
        "post": post_row,
        "comments": _select_all_eq(client, 'comments', 'post_id', post_id),
        "likes": _select_all_eq(client, 'likes', 'post_id', post_id),
        "reports": _select_all_eq(client, 'reports', 'post_id', post_id),
        "warnings": _select_all_eq(client, 'warnings', 'post_id', post_id),
        "captured_at": _iso_utc_now(),
    }

    purge_after = (
        datetime.datetime.now(datetime.timezone.utc) +
        datetime.timedelta(days=ARCHIVE_RETENTION_DAYS)
    ).isoformat()

    client.table('archived_posts').insert({
        "original_post_id": post_id,
        "post_owner_id": post_row.get("user_id"),
        "deleted_by": deleted_by,
        "deleted_by_role": deleted_by_role,
        "deletion_source": source,
        "delete_reason": reason,
        "delete_note": note,
        "archived_payload": _json_safe(payload),
        "archived_at": _iso_utc_now(),
        "purge_after": purge_after,
    }).execute()

    return post_row
