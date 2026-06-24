"""Facebook Graph API client for fetching weekly posts + IG media with engagement.

Token is read from FB_GRAPH_TOKEN in .env. Posts/insights data is normalized into
a shared shape so frontend and AI prompt logic can stay agnostic of platform.
"""
import os
from datetime import datetime
from typing import Optional
from functools import lru_cache
import httpx
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.getenv("FB_GRAPH_TOKEN", "")


def _get(path: str, params: dict) -> dict:
    r = httpx.get(f"{GRAPH}/{path.lstrip('/')}", params=params, timeout=20.0)
    return r.json()


@lru_cache(maxsize=1)
def list_managed_pages() -> list[dict]:
    """List all FB pages the token can manage, plus their linked IG account id."""
    if not TOKEN:
        return []
    out = _get("me/accounts", {
        "access_token": TOKEN,
        "fields": "id,name,access_token,instagram_business_account",
        "limit": 100,
    })
    result = []
    for p in out.get("data", []):
        result.append({
            "page_id": p["id"],
            "name": p["name"],
            "page_token": p.get("access_token"),
            "ig_user_id": (p.get("instagram_business_account") or {}).get("id"),
        })
    return result


def find_page_by_brand(brand_name: str) -> Optional[dict]:
    """Best-effort match: exact name, then substring (strip parens/space)."""
    pages = list_managed_pages()
    target = brand_name.strip()
    for p in pages:
        if p["name"].strip() == target:
            return p
    for p in pages:
        if target in p["name"] or p["name"] in target:
            return p
    return None


def fetch_fb_posts(page_id: str, page_token: str, since: str, until: str) -> list[dict]:
    """Fetch FB page posts in [since, until] (YYYY-MM-DD inclusive) with engagement."""
    out = _get(f"{page_id}/posts", {
        "access_token": page_token,
        "fields": (
            "id,message,created_time,permalink_url,"
            "attachments{media_type,url,media},"
            "reactions.summary(true).limit(0),"
            "comments.summary(true).limit(0),"
            "shares"
        ),
        "since": since,
        "until": until,
        "limit": 50,
    })
    posts = []
    for p in out.get("data", []):
        reactions = (p.get("reactions") or {}).get("summary", {}).get("total_count", 0)
        comments = (p.get("comments") or {}).get("summary", {}).get("total_count", 0)
        shares = (p.get("shares") or {}).get("count", 0)

        # Try to enrich with insight metrics (clicks / video views). Failures are non-fatal.
        clicks = None
        video_views = None
        try:
            ins = _get(f"{p['id']}/insights", {
                "access_token": page_token,
                "metric": "post_clicks,post_video_views",
            })
            for m in ins.get("data", []):
                v = m["values"][0].get("value") if m.get("values") else None
                if m["name"] == "post_clicks":
                    clicks = v
                elif m["name"] == "post_video_views":
                    video_views = v
        except Exception:
            pass

        attachments = (p.get("attachments") or {}).get("data") or []
        media_type = attachments[0].get("media_type") if attachments else None
        media_url = None
        if attachments:
            m = attachments[0].get("media") or {}
            img = m.get("image") or {}
            media_url = img.get("src") or attachments[0].get("url")

        engagement = reactions + comments + shares
        posts.append({
            "platform": "fb",
            "id": p["id"],
            "message": p.get("message") or "",
            "created_at": p.get("created_time"),
            "permalink": p.get("permalink_url"),
            "media_type": media_type,
            "media_url": media_url,
            "reactions": reactions,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "video_views": video_views,
            "engagement": engagement,
        })
    posts.sort(key=lambda x: x["engagement"], reverse=True)
    return posts


def fetch_ig_media(ig_user_id: str, since_ts: int, until_ts: int) -> list[dict]:
    """Fetch IG media in [since_ts, until_ts] (unix seconds) with engagement."""
    # IG /media doesn't honor since/until reliably — pull recent and filter client-side.
    out = _get(f"{ig_user_id}/media", {
        "access_token": TOKEN,
        "fields": (
            "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,"
            "like_count,comments_count"
        ),
        "limit": 50,
    })
    media = []
    for m in out.get("data", []):
        ts = m.get("timestamp")
        if not ts:
            continue
        # ISO 8601 → unix
        try:
            dt = datetime.strptime(ts.replace("+0000", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            continue
        ts_int = int(dt.timestamp())
        if ts_int < since_ts or ts_int > until_ts:
            continue

        reach = None
        saved = None
        views = None
        total_interactions = None
        avg_watch_time = None
        try:
            # `views` works for all media types (IMAGE/VIDEO/CAROUSEL) since v21
            ins = _get(f"{m['id']}/insights", {
                "access_token": TOKEN,
                "metric": "reach,saved,views,total_interactions",
            })
            for x in ins.get("data", []):
                v = x["values"][0].get("value") if x.get("values") else None
                if x["name"] == "reach":
                    reach = v
                elif x["name"] == "saved":
                    saved = v
                elif x["name"] == "views":
                    views = v
                elif x["name"] == "total_interactions":
                    total_interactions = v
        except Exception:
            pass

        # Reels-specific: average watch time (in ms)
        if m.get("media_type") in ("VIDEO", "REELS"):
            try:
                ins2 = _get(f"{m['id']}/insights", {
                    "access_token": TOKEN,
                    "metric": "ig_reels_avg_watch_time",
                })
                for x in ins2.get("data", []):
                    if x["name"] == "ig_reels_avg_watch_time":
                        avg_watch_time = x["values"][0].get("value") if x.get("values") else None
            except Exception:
                pass

        likes = m.get("like_count") or 0
        comments = m.get("comments_count") or 0
        engagement = total_interactions if total_interactions is not None else (likes + comments + (saved or 0))

        media.append({
            "platform": "ig",
            "id": m["id"],
            "message": m.get("caption") or "",
            "created_at": ts,
            "permalink": m.get("permalink"),
            "media_type": m.get("media_type"),
            "media_url": m.get("thumbnail_url") or m.get("media_url"),
            "likes": likes,
            "comments": comments,
            "saved": saved,
            "reach": reach,
            "views": views,
            "total_interactions": total_interactions,
            "avg_watch_time_ms": avg_watch_time,
            "engagement": engagement,
        })
    # Sort by views (most important) then engagement
    media.sort(key=lambda x: ((x["views"] or 0), x["engagement"]), reverse=True)
    return media


def fetch_brand_meta(brand_name: str) -> dict:
    """Return live follower / fan counts for a brand's FB page + IG account."""
    page = find_page_by_brand(brand_name)
    if not page:
        return {"matched_page": None}
    fb_meta = _get(page["page_id"], {
        "access_token": page.get("page_token") or TOKEN,
        "fields": "id,name,fan_count,followers_count,talking_about_count,were_here_count",
    })
    ig_meta = {}
    if page.get("ig_user_id"):
        ig_meta = _get(page["ig_user_id"], {
            "access_token": TOKEN,
            "fields": "id,username,followers_count,follows_count,media_count,profile_picture_url",
        })
    return {
        "matched_page": {"page_id": page["page_id"], "name": page["name"], "ig_user_id": page.get("ig_user_id")},
        "fb": fb_meta if "error" not in fb_meta else None,
        "ig": ig_meta if "error" not in ig_meta else None,
    }


def fetch_weekly_posts(brand_name: str, start_date: str, end_date: str) -> dict:
    """Fetch FB + IG posts for the given brand within [start_date, end_date]."""
    page = find_page_by_brand(brand_name)
    if not page:
        return {"matched_page": None, "fb": [], "ig": []}

    # Convert dates to unix for IG filter
    since_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    # End of day for "until"
    until_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86400 - 1

    fb_posts = fetch_fb_posts(page["page_id"], page["page_token"], start_date, end_date) if page.get("page_token") else []
    ig_media = fetch_ig_media(page["ig_user_id"], since_ts, until_ts) if page.get("ig_user_id") else []

    return {
        "matched_page": {"page_id": page["page_id"], "name": page["name"], "ig_user_id": page.get("ig_user_id")},
        "fb": fb_posts,
        "ig": ig_media,
    }


def top_posts_summary(weekly: dict, top_n: int = 3) -> str:
    """Format top N posts per platform as text for the AI prompt."""
    lines = []
    fb = weekly.get("fb") or []
    if fb:
        lines.append("【FB TOP 貼文（按互動排序）】")
        for i, p in enumerate(fb[:top_n], 1):
            msg = (p["message"] or "(無文字)")[:80].replace("\n", " ")
            lines.append(
                f"  {i}. {msg} — 讚 {p['reactions']}、留言 {p['comments']}、分享 {p['shares']}"
                + (f"、點擊 {p['clicks']}" if p.get("clicks") is not None else "")
                + (f"、影片觀看 {p['video_views']}" if p.get("video_views") else "")
            )
    ig = weekly.get("ig") or []
    if ig:
        lines.append("【IG TOP 貼文（按觀看次數排序）】")
        for i, m in enumerate(ig[:top_n], 1):
            msg = (m["message"] or "(無文字)")[:80].replace("\n", " ")
            lines.append(
                f"  {i}. {msg} — 觀看 {m.get('views') or '?'}、觸及 {m.get('reach') or '?'}、讚 {m['likes']}、留言 {m['comments']}"
                + (f"、儲存 {m['saved']}" if m.get("saved") else "")
                + (f"、互動 {m['total_interactions']}" if m.get("total_interactions") else "")
            )
    return "\n".join(lines)
