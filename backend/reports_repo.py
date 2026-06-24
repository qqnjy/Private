"""AI report cache — read/write the `reports` Supabase table."""
from datetime import datetime
from models import supabase


def get_cached_report(brand: str, week_start: str, week_end: str) -> dict | None:
    res = supabase.table("reports").select("*") \
        .eq("brand_name", brand) \
        .eq("week_start", week_start) \
        .eq("week_end", week_end) \
        .execute()
    rows = res.data or []
    if not rows:
        return None
    r = rows[0]
    return {
        "outline": r.get("outline") or "",
        "slides": r.get("slides") or None,
        "generated_at": r.get("generated_at"),
        "notes": r.get("notes"),
    }


def save_report(brand: str, week_start: str, week_end: str, outline: str, slides: dict | None, notes: str | None) -> None:
    row = {
        "brand_name": brand,
        "week_start": week_start,
        "week_end": week_end,
        "outline": outline or "",
        "slides": slides or {},
        "notes": notes or "",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    supabase.table("reports").upsert(row, on_conflict="brand_name,week_start,week_end").execute()
