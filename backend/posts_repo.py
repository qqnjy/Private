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

    fb_items.sort(key=lambda x: x.get("engagement") or 0, reverse=True)
    ig_items.sort(key=lambda x: ((x.get("views") or 0), x.get("engagement") or 0), reverse=True)
    return {"fb": fb_items, "ig": ig_items, "fetched_at": fetched_max}


def save_posts(brand: str, week_start: str, week_end: str, fb: list[dict], ig: list[dict]) -> None:
    """Upsert all posts to the table. Existing post ids get refreshed metrics."""
    rows = [_normalize_post_for_db(brand, week_start, week_end, p) for p in (fb or [])] \
         + [_normalize_post_for_db(brand, week_start, week_end, p) for p in (ig or [])]
    if not rows:
        return
    supabase.table("posts").upsert(rows, on_conflict="id").execute()
