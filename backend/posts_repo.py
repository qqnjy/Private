"""Posts persistence — read/write the `posts` table in Supabase."""
from datetime import datetime
from models import supabase


def _normalize_post_for_db(brand: str, week_start: str, week_end: str, p: dict) -> dict:
    """Strip the in-memory post shape into the table columns + jsonb metrics."""
    metrics = {k: v for k, v in p.items() if k not in {
        "id", "platform", "message", "created_at", "permalink",
        "media_type", "media_url", "_platform", "_views",
    }}
    return {
        "id": p["id"],
        "brand_name": brand,
        "platform": p["platform"],
        "message": p.get("message") or "",
        "permalink": p.get("permalink"),
        "media_type": p.get("media_type"),
        "media_url": p.get("media_url"),
        "created_at": p.get("created_at"),
        "metrics": metrics,
        "week_start": week_start,
        "week_end": week_end,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def get_cached_posts(brand: str, week_start: str, week_end: str) -> dict | None:
    """Return cached posts for the brand+week if any. Returns None if none cached."""
    res = supabase.table("posts").select("*") \
        .eq("brand_name", brand) \
        .eq("week_start", week_start) \
        .eq("week_end", week_end) \
        .execute()
    rows = res.data or []
    if not rows:
        return None

    fb_items = []
    ig_items = []
    fetched_max = None
    for r in rows:
        metrics = r.get("metrics") or {}
        item = {
            "platform": r["platform"],
            "id": r["id"],
            "message": r.get("message") or "",
            "created_at": r.get("created_at"),
            "permalink": r.get("permalink"),
            "media_type": r.get("media_type"),
            "media_url": r.get("media_url"),
            **metrics,
        }
        if r["platform"] == "fb":
            fb_items.append(item)
        else:
            ig_items.append(item)
        if r.get("fetched_at"):
            fetched_max = max(fetched_max, r["fetched_at"]) if fetched_max else r["fetched_at"]

    # Match the same sort key fb_api uses on the live path
    fb_items.sort(key=lambda x: ((x.get("total_views") or x.get("video_views") or 0), x.get("engagement") or 0), reverse=True)
    ig_items.sort(key=lambda x: ((x.get("views") or 0), x.get("engagement") or 0), reverse=True)
    return {"fb": fb_items, "ig": ig_items, "fetched_at": fetched_max}


def _aggregate(items: list[dict], platform: str) -> dict:
    """Aggregate a list of posts into the metrics we compare week-over-week."""
    n = len(items)
    if n == 0:
        return {"post_count": 0}
    total_reach = 0
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    total_saves = 0
    for p in items:
        total_likes += (p.get("reactions") if platform == "fb" else p.get("likes")) or 0
        total_comments += p.get("comments") or 0
        total_shares += p.get("shares") or 0
        if platform == "fb":
            total_reach += 0  # FB reach not exposed
            total_views += (p.get("total_views") or p.get("video_views") or 0)
        else:
            total_reach += p.get("reach") or 0
            total_views += p.get("views") or 0
            total_saves += p.get("saved") or 0

    interactions = total_likes + total_comments + total_shares + total_saves
    avg_view = total_views / n if total_views else 0
    avg_reach = total_reach / n if total_reach else 0
    interaction_rate = (interactions / total_views * 100) if total_views > 0 else 0

    return {
        "post_count": n,
        "total_views": total_views,
        "total_reach": total_reach,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_saves": total_saves,
        "total_interactions": interactions,
        "avg_view": round(avg_view, 1),
        "avg_reach": round(avg_reach, 1),
        "interaction_rate": round(interaction_rate, 2),
    }


def get_week_summary(brand: str, week_start: str, week_end: str) -> dict:
    """Return aggregated metrics for the week. Empty dict if no cached data."""
    cached = get_cached_posts(brand, week_start, week_end)
    if not cached:
        return {}
    return {
        "fb": _aggregate(cached.get("fb") or [], "fb"),
        "ig": _aggregate(cached.get("ig") or [], "ig"),
    }


# Metric keys that a manual override should protect from being wiped by a
# subsequent Graph API refetch. If a row has metrics._manual_override = True,
# whichever of these keys are already set survive the upsert.
MANUAL_PROTECTED_KEYS = {
    "total_views", "video_views", "video_views_unique", "video_views_15s",
    "reach", "views", "saved", "avg_watch_ms", "avg_watch_time_ms",
    "live_views",
}


def save_posts(brand: str, week_start: str, week_end: str, fb: list[dict], ig: list[dict]) -> None:
    """Upsert all posts to the table. Existing post ids get refreshed metrics.

    Rows previously marked with metrics._manual_override = True keep their
    manually-set metric values (e.g. FB photo views that the Graph API can't
    provide) even when a live refetch would overwrite them with 0 / None.
    """
    rows = [_normalize_post_for_db(brand, week_start, week_end, p) for p in (fb or [])] \
         + [_normalize_post_for_db(brand, week_start, week_end, p) for p in (ig or [])]
    if not rows:
        return

    # Pull existing rows in one query so we can merge manual overrides
    ids = [r["id"] for r in rows]
    existing_rows = supabase.table("posts").select("id, metrics").in_("id", ids).execute().data or []
    existing = {r["id"]: (r.get("metrics") or {}) for r in existing_rows}

    for row in rows:
        old_metrics = existing.get(row["id"])
        if not old_metrics or not old_metrics.get("_manual_override"):
            continue
        # Merge: keep the manual flag + any manually-set protected values
        new_metrics = row["metrics"]
        new_metrics["_manual_override"] = True
        for k in MANUAL_PROTECTED_KEYS:
            if old_metrics.get(k) is not None:
                # only keep manual if it looks more informative
                # (non-zero manual overrides a zero/None from live fetch)
                if not new_metrics.get(k):
                    new_metrics[k] = old_metrics[k]
                # If both are set (rare), respect the manual one — user
                # explicitly overrode it, so keep the human-supplied value.
                elif old_metrics.get(k):
                    new_metrics[k] = old_metrics[k]

    supabase.table("posts").upsert(rows, on_conflict="id").execute()
