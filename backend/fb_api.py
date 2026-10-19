"""Facebook Graph API client for fetching weekly posts + IG media with engagement.

Token is read from FB_GRAPH_TOKEN in .env. Posts/insights data is normalized into
a shared shape so frontend and AI prompt logic can stay agnostic of platform.
"""
import os
import re
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
    """Fetch FB page posts in [since, until] (YYYY-MM-DD inclusive) with engagement.

    For video posts we pull view counts; for live broadcasts we additionally
    pull `post_video_views_live` and tag the post with is_live=True.
    """
    out = _get(f"{page_id}/posts", {
        "access_token": page_token,
        "fields": (
            "id,message,created_time,permalink_url,status_type,"
            "attachments{media_type,url,media,target{id}},"
            "reactions.summary(true).limit(0),"
            "comments.summary(true).limit(0),"
            "shares"
        ),
        "since": since,
        "until": until,
        "limit": 50,
    })

    # Build a lookup: which posts came from live broadcasts? Live VODs are
    # listed under /page/live_videos and link to a post via permalink_url.
    live_posts: dict[str, dict] = {}
    try:
        lv = _get(f"{page_id}/live_videos", {
            "access_token": page_token,
            "fields": "id,title,broadcast_start_time,permalink_url",
            "limit": 50,
        })
        for v in lv.get("data") or []:
            link = v.get("permalink_url") or ""
            # link looks like /1323185103270629/videos/1011752444736502
            tail = link.rstrip("/").rsplit("/", 1)[-1] if link else ""
            if tail:
                live_posts[tail] = v
    except Exception:
        pass

    posts = []
    for p in out.get("data", []):
        reactions = (p.get("reactions") or {}).get("summary", {}).get("total_count", 0)
        comments = (p.get("comments") or {}).get("summary", {}).get("total_count", 0)
        shares = (p.get("shares") or {}).get("count", 0)

        # Check if this post is a live broadcast — match by the trailing post id
        post_tail = p["id"].split("_")[-1]
        live_info = live_posts.get(post_tail)
        is_live = bool(live_info)

        clicks = None
        video_views = None
        video_views_unique = None
        video_views_15s = None
        avg_watch_ms = None
        live_views = None
        try:
            metric_list = [
                "post_clicks",
                "post_video_views",
                "post_video_views_unique",
                "post_video_views_15s",
                "post_video_avg_time_watched",
            ]
            if is_live:
                metric_list.append("post_video_views_live")
            ins = _get(f"{p['id']}/insights", {
                "access_token": page_token,
                "metric": ",".join(metric_list),
            })
            for m in ins.get("data", []):
                v = m["values"][0].get("value") if m.get("values") else None
                if m["name"] == "post_clicks":
                    clicks = v
                elif m["name"] == "post_video_views":
                    video_views = v
                elif m["name"] == "post_video_views_unique":
                    video_views_unique = v
                elif m["name"] == "post_video_views_15s":
                    video_views_15s = v
                elif m["name"] == "post_video_avg_time_watched":
                    avg_watch_ms = v
                elif m["name"] == "post_video_views_live":
                    live_views = v
        except Exception:
            pass

        attachments = (p.get("attachments") or {}).get("data") or []
        media_type = attachments[0].get("media_type") if attachments else None
        media_url = None
        video_id = None
        if attachments:
            m_att = attachments[0].get("media") or {}
            img = m_att.get("image") or {}
            media_url = img.get("src") or attachments[0].get("url")
            tgt = attachments[0].get("target") or {}
            if media_type == "video":
                video_id = tgt.get("id")

        # Post type classification — heuristic: video → 影片, photo → 圖片, album → 圖文
        if media_type == "video":
            post_type = "影片"
        elif media_type == "album":
            post_type = "圖文"
        elif media_type == "photo":
            post_type = "圖片"
        else:
            post_type = "其他"

        # For video posts, fetch the video object's `views` field — this matches
        # what Meta Business Suite shows in its UI (and is much higher than
        # `post_video_views` which only counts ≥ 3-second views).
        total_views = None
        if video_id:
            try:
                vo = _get(video_id, {"access_token": page_token, "fields": "views"})
                total_views = vo.get("views")
            except Exception:
                pass

        engagement = reactions + comments + shares
        posts.append({
            "platform": "fb",
            "id": p["id"],
            "message": p.get("message") or "",
            "created_at": p.get("created_time"),
            "permalink": p.get("permalink_url"),
            "status_type": p.get("status_type"),
            "media_type": media_type,
            "media_url": media_url,
            "post_type": post_type,
            "is_live": is_live,
            "live_title": live_info.get("title") if live_info else None,
            "reactions": reactions,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "total_views": total_views,
            "video_views": video_views,
            "video_views_unique": video_views_unique,
            "video_views_15s": video_views_15s,
            "avg_watch_ms": avg_watch_ms,
            "live_views": live_views,
            "engagement": engagement,
        })
    # Sort by total_views (matches Meta UI) when available, fall back to other signals.
    posts.sort(key=lambda x: ((x.get("total_views") or x.get("video_views") or 0), x["engagement"]), reverse=True)
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

        mt = m.get("media_type")
        if mt == "VIDEO":
            ig_post_type = "影片"
        elif mt == "CAROUSEL_ALBUM":
            ig_post_type = "圖文"
        elif mt == "IMAGE":
            ig_post_type = "圖片"
        else:
            ig_post_type = "其他"

        media.append({
            "platform": "ig",
            "id": m["id"],
            "message": m.get("caption") or "",
            "created_at": ts,
            "permalink": m.get("permalink"),
            "media_type": mt,
            "media_url": m.get("thumbnail_url") or m.get("media_url"),
            "post_type": ig_post_type,
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


def get_historical_fans(brand: str, platform: str, on_or_before_date: str) -> int | None:
    """Return the latest scraped follower count for this brand+platform on or
    before the given date (YYYY-MM-DD). Uses the local scraper's `records` table."""
    try:
        from models import supabase
        targets = supabase.table("targets").select("id, name").eq("platform", platform).execute().data or []
        target = None
        normalized = brand.strip()
        for t in targets:
            clean = (t["name"]
                     .replace("粉絲團", "")
                     .replace("(FB)", "").replace("(IG)", "")
                     .replace("(THREADS)", "")
                     .replace("_IG", "").replace("_YT", "")
                     .strip())
            if clean == normalized or normalized in clean or clean in normalized:
                target = t
                break
        if not target:
            return None
        rec = supabase.table("records").select("followers") \
            .eq("target_id", target["id"]) \
            .lte("scraped_at", f"{on_or_before_date}T23:59:59+00:00") \
            .order("scraped_at", desc=True).limit(1).execute().data or []
        return rec[0]["followers"] if rec else None
    except Exception as e:
        print(f"get_historical_fans failed: {e}")
        return None


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


_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002190-\U000021FF\U00002300-\U000027BF"
    "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0001F1E6-\U0001F1FF]+"
)


def _clean_title(text: str, limit: int) -> str:
    """Post title for the prompt, with emoji removed.

    The model translates stray emoji into words — 🚕 has come back as the
    Turkish "araç" and the German "Fahr" in the middle of a Chinese report.
    Dropping them costs nothing, since the titles are quoted as plain text.
    """
    t = _EMOJI_RE.sub("", str(text or "")).replace("\n", " ")
    return re.sub(r"\s{2,}", " ", t).strip()[:limit]


def _type_breakdown(posts: list, views_key, label: str) -> list:
    """Views vs engagement split by post type.

    Posts are ranked by views, so photos never make the TOP list even when they
    carry the week's interactions. Without this the report only ever describes
    videos.
    """
    if not posts:
        return []
    buckets = {}
    for p in posts:
        b = buckets.setdefault(p.get("post_type") or "其他", {"n": 0, "v": 0, "e": 0})
        b["n"] += 1
        b["v"] += views_key(p) or 0
        b["e"] += p.get("engagement") or 0
    total_v = sum(b["v"] for b in buckets.values())
    total_e = sum(b["e"] for b in buckets.values())
    lines = [f"【{label} 貼文類型分佈】"]
    for name, b in sorted(buckets.items(), key=lambda kv: -kv[1]["v"]):
        vp = f"{b['v'] / total_v * 100:.1f}%" if total_v else "—"
        ep = f"{b['e'] / total_e * 100:.1f}%" if total_e else "—"
        lines.append(
            f"  {name}：{b['n']} 則，觀看 {b['v']:,}（佔 {vp}）、互動 {b['e']:,}（佔 {ep}）"
        )
    return lines


def _top_by_engagement(posts: list, top_n: int, label: str) -> list:
    """The interaction leaders, which the views ranking hides.

    The ratios are computed here rather than left to the model, which gets them
    wrong (it has reported a 1.27% comment rate as 24.5%).
    """
    ranked = sorted(posts, key=lambda p: p.get("engagement") or 0, reverse=True)[:top_n]
    if not ranked:
        return []
    week_comments = sum(p.get("comments") or 0 for p in posts)
    week_eng = sum(p.get("engagement") or 0 for p in posts)
    lines = [f"【{label} 互動最高貼文】（比率均已算好，請直接引用，不要自行計算）"]
    for i, p in enumerate(ranked, 1):
        msg = _clean_title(p.get("message") or p.get("live_title") or "(無文字)", 60)
        views = p.get("total_views") or p.get("video_views") or 0
        eng = p.get("engagement") or 0
        com = p.get("comments") or 0
        ratios = []
        if week_eng:
            ratios.append(f"占全週互動 {eng / week_eng * 100:.1f}%")
        if week_comments:
            ratios.append(f"占全週留言 {com / week_comments * 100:.1f}%")
        if views:
            ratios.append(f"留言率 {com / views * 100:.2f}%")
            ratios.append(f"互動率 {eng / views * 100:.2f}%")
        lines.append(
            f"  {i}. [{p.get('post_type') or '其他'}] {msg} — 觀看 {views:,}、互動 {eng}"
            f"（讚 {p.get('reactions') or 0}、留言 {com}、分享 {p.get('shares') or 0}）"
            + ("；" + "、".join(ratios) if ratios else "")
        )
    return lines


def fan_trend_summary(brand: str, week_end: str, weeks: int = 5) -> str:
    """Week-ending follower counts for the last few weeks.

    Single-week deltas read as noise; the useful line in the report is whether
    this is the first down week or the third, and what it adds up to.
    """
    from datetime import datetime as _d, timedelta as _t

    try:
        end = _d.strptime(week_end, "%Y-%m-%d").date()
    except ValueError:
        return ""
    lines = []
    for plat, label in (("fb", "FB"), ("ig", "IG")):
        series = []
        for i in range(weeks - 1, -1, -1):
            d = (end - _t(days=7 * i)).isoformat()
            n = get_historical_fans(brand, plat, d)
            if n:
                series.append((d, n))
        if len(series) < 2:
            continue
        bits = []
        for idx, (d, n) in enumerate(series):
            if idx == 0:
                bits.append(f"{d} {n:,}")
            else:
                bits.append(f"{d} {n:,}（{n - series[idx - 1][1]:+,}）")
        net = series[-1][1] - series[0][1]
        # Count the run of consecutive down (or up) weeks ending this week, so
        # the model never has to count it itself.
        deltas = [series[i][1] - series[i - 1][1] for i in range(1, len(series))]
        streak, direction = 0, None
        for d in reversed(deltas):
            if d < 0 and direction in (None, "down"):
                direction, streak = "down", streak + 1
            elif d > 0 and direction in (None, "up"):
                direction, streak = "up", streak + 1
            else:
                break
        lines.append(f"【{label} 近 {len(series)} 週粉絲數】")
        lines.append("  " + " → ".join(bits))
        lines.append(f"  區間淨變化：{net:+,} 人")
        if direction == "down":
            lines.append(f"  連續淨流失週數：{streak} 週（寫報告時請直接寫「連續第 {streak} 週」，不要自行推算）")
        elif direction == "up":
            lines.append(f"  連續淨成長週數：{streak} 週")
        else:
            lines.append("  本週持平")
        lines.append("")
    return "\n".join(lines).rstrip()


_WOW_FIELDS = [
    ("post_count", "發佈篇數", ""),
    ("total_views", "總觀看", ""),
    ("total_reach", "總觸及", ""),
    ("avg_view", "平均觀看", ""),
    ("total_interactions", "總互動", ""),
    ("interaction_rate", "互動率", "%"),
    ("total_likes", "讚", ""),
    ("total_comments", "留言", ""),
    ("total_shares", "分享", ""),
]


def wow_summary(this_week: dict, last_week: dict) -> str:
    """This week vs last week, per platform.

    The report is meant to read as a trend, not a snapshot, so the model needs
    last week's aggregates to state any change rate at all.
    """
    if not this_week:
        return ""
    lines = []
    for plat in ("fb", "ig"):
        cur = this_week.get(plat) or {}
        prev = (last_week or {}).get(plat) or {}
        if not cur.get("post_count"):
            continue
        lines.append(f"【{plat.upper()} 本週 vs 上週】")
        for key, label, unit in _WOW_FIELDS:
            now = cur.get(key) or 0
            if not now and not (prev.get(key) or 0):
                continue
            before = prev.get(key) or 0
            if before:
                pct = (now - before) / before * 100
                delta = f"（上週 {before:,}{unit}，{pct:+.1f}%）"
            else:
                delta = "（上週無資料）"
            lines.append(f"  {label}：{now:,}{unit}{delta}")
        lines.append("")
    return "\n".join(lines).rstrip()


def top_posts_summary(weekly: dict, top_n: int = 5) -> str:
    """Format top N posts per platform as text for the AI prompt."""
    lines = []
    fb = weekly.get("fb") or []
    if fb:
        lines += _type_breakdown(fb, lambda p: p.get("total_views") or p.get("video_views"), "FB")
        lines.append("")
        lines.append("【FB TOP 貼文（影片按觀看數排序）】")
        for i, p in enumerate(fb[:top_n], 1):
            msg = _clean_title(p["message"] or p.get("live_title") or "(無文字)", 80)
            tag = "🔴 直播" if p.get("is_live") else f"[{p.get('post_type') or '其他'}]"
            parts = [f"  {i}. {tag} {msg}".strip()]
            metric_bits = []
            views = p.get("total_views") or p.get("video_views")
            if views:
                metric_bits.append(f"觀看 {views}")
            if p.get("live_views"):
                metric_bits.append(f"直播即時觀看 {p['live_views']}")
            metric_bits.append(f"讚 {p['reactions']}")
            metric_bits.append(f"留言 {p['comments']}")
            metric_bits.append(f"分享 {p['shares']}")
            if p.get("clicks") is not None:
                metric_bits.append(f"點擊 {p['clicks']}")
            lines.append(parts[0] + " — " + "、".join(metric_bits))
        eng = _top_by_engagement(fb, 3, "FB")
        if eng:
            lines.append("")
            lines += eng
    ig = weekly.get("ig") or []
    if ig:
        if fb:
            lines.append("")
        lines += _type_breakdown(ig, lambda m: m.get("views"), "IG")
        lines.append("")
        lines.append("【IG TOP 貼文（按觀看次數排序）】")
        for i, m in enumerate(ig[:top_n], 1):
            msg = _clean_title(m["message"] or "(無文字)", 80)
            lines.append(
                f"  {i}. [{m.get('post_type') or '其他'}] {msg} — 觀看 {m.get('views') or '?'}"
                f"、觸及 {m.get('reach') or '?'}、讚 {m['likes']}、留言 {m['comments']}"
                + (f"、儲存 {m['saved']}" if m.get("saved") else "")
                + (f"、互動 {m['total_interactions']}" if m.get("total_interactions") else "")
            )
    return "\n".join(lines)


BASELINE_PATH = os.path.join(os.path.dirname(__file__), "data", "calendar_baseline.json")


def baseline_summary(brand: str, week_start: str, week_end: str) -> str:
    """This week against the frozen pre-calendar baseline.

    The posting calendar and GEO copy went live on 2026-10-12, and the question
    the ops team asked is whether they lift performance. That needs a fixed
    comparison period — a rolling window would absorb the very change we are
    trying to see — so the baseline is frozen in calendar_baseline.json.
    """
    import json as _json
    from datetime import date as _date

    if not os.path.exists(BASELINE_PATH):
        return ""
    try:
        with open(BASELINE_PATH, encoding="utf-8") as fh:
            bl = _json.load(fh)
    except Exception:
        return ""
    # Baseline brand only, and only for weeks after the baseline period.
    if bl.get("brand") != brand or week_start <= bl.get("period", {}).get("end", ""):
        return ""

    from posts_repo import get_cached_posts

    cached = get_cached_posts(brand, week_start, week_end) or {}
    week_over = _date.today().isoformat() > week_end

    lines = [
        "【行事曆／GEO 導入後對照】",
        f"  基準期：{bl['period']['start']} ~ {bl['period']['end']}"
        f"（{'、'.join(bl['weeks'])}，導入前 {bl['platforms']['fb']['weeks']} 週平均）",
    ]
    if not week_over:
        lines.append("  本週尚未結束，以下僅為進度參考，不可寫成單週成效或成長率。")

    def compare(now, was):
        # A zero means the manual view counts have not been patched in yet, not
        # that nobody watched — never turn that into a -100%.
        if not now:
            return f"尚待取得（基準週均 {was:,}）"
        if not was or not week_over:
            return f"{now:,}（基準週均 {was:,}）"
        return f"{now:,}（基準週均 {was:,}，{(now - was) / was * 100:+.1f}%）"

    for plat, label in (("fb", "FB"), ("ig", "IG")):
        base = bl["platforms"].get(plat) or {}
        posts = cached.get(plat) or []
        if not posts or not base:
            lines.append(f"  {label}：本週尚無貼文資料，尚待取得")
            continue
        per_post = [(p.get("total_views") or p.get("video_views") or 0) if plat == "fb"
                    else (p.get("views") or 0) for p in posts]
        views = sum(per_post)
        missing = sum(1 for v in per_post if not v)
        eng = sum(p.get("engagement") or 0 for p in posts)
        # A partial view total compared against a full-week baseline reads as a
        # collapse that did not happen, so withhold it until every post has one.
        if missing:
            views_txt = (f"{len(posts) - missing}/{len(posts)} 篇有觀看數，"
                         f"合計未完整，尚待取得（基準週均 {base['views_per_week']:,}）")
            views = 0
        else:
            views_txt = compare(views, base["views_per_week"])
        lines.append(
            f"  {label}：發文 {len(posts)} 篇（基準週均 {base['posts_per_week']} 篇）；"
            f"觀看 {views_txt}；"
            f"互動 {compare(eng, base['engagement_per_week'])}"
            f"；每篇平均互動 {eng / len(posts):.1f}"
            f"（基準 {base['engagement_per_week'] / base['posts_per_week']:.1f}"
            + (f"，{(eng / len(posts) - base['engagement_per_week'] / base['posts_per_week']) / (base['engagement_per_week'] / base['posts_per_week']) * 100:+.1f}%）"
               if week_over and base.get("posts_per_week") else "）")
        )
        rate = eng / views * 100 if views else None
        if rate and base.get("interaction_rate") and week_over:
            d = (rate - base["interaction_rate"]) / base["interaction_rate"] * 100
            lines.append(f"      互動率 {rate:.2f}%（基準 {base['interaction_rate']}%，{d:+.1f}%）")
        elif rate:
            lines.append(f"      互動率 {rate:.2f}%（基準 {base['interaction_rate']}%）")
        else:
            lines.append("      互動率：觀看數尚待取得，暫不計算")

    lines.append("  注意：單週差異可能來自檔期或題材，尚不足以歸因於行事曆或 GEO；"
                 "GEO 的搜尋收錄與引用無法由社群數據驗證，不得宣稱成效。")
    return "\n".join(lines)


_WEEKDAYS = "一二三四五六日"

_THEME_KEYWORDS = {
    "抽獎／贈獎": ("抽獎", "抽出", "得獎", "送出", "紅鑽", "好禮", "獎品"),
    "留言互動": ("留言", "你最早", "你會嗎", "舉手", "告訴我", "選出", "猜"),
    "時事／節慶": ("中秋", "國慶", "連假", "開學", "鬼門", "母親節", "新年", "媽祖"),
    "直播／主播": ("直播", "主播", "班表", "晚上8點", "晚上 8 點"),
    "教學／冷知識": ("英語", "知識", "教你", "怎樣才可以"),
}

# Prizes you can hold in your hand vs in-game currency.
_PHYSICAL_PRIZE = ("零錢包", "抱枕", "旗子", "實體", "娃娃", "周邊")
_VIRTUAL_PRIZE = ("紅鑽", "鑽石", "金幣", "點數", "兌換碼")

_MIN_EFFECTIVE = 10   # below this a slice is noise, and the report must say so


def posting_pattern_summary(brand: str, before_date: str | None = None) -> str:
    """Long-run posting patterns, which a single week cannot show.

    The weekly report only ever sees its own seven days, so it kept recommending
    generic things like "優化內容形式". Weekday, time slot, theme and prize type
    only separate over months of posts, and those are what the schedule is
    actually built from.
    """
    from models import supabase
    from datetime import timedelta

    try:
        rows = supabase.table("posts").select("*") \
            .eq("brand_name", brand).eq("platform", "fb").execute().data or []
    except Exception:
        return ""
    if before_date:
        rows = [p for p in rows if p.get("created_at", "")[:10] <= before_date]
    if len(rows) < 30:
        return ""

    def taipei(p):
        return datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) + timedelta(hours=8)

    def views(p):
        m = p.get("metrics") or {}
        return m.get("total_views") or m.get("video_views") or 0

    def eng(p):
        return (p.get("metrics") or {}).get("engagement") or 0

    def slice_line(label, posts):
        eff = [p for p in posts if views(p)]
        if not posts:
            return f"  {label}：0 則（區間內未發文）"
        if not eff:
            return f"  {label}：{len(posts)} 則，觀看數尚待取得，互動率無法計算"
        rate = sum(eng(p) / views(p) * 100 for p in eff) / len(eff)
        warn = "，樣本偏少僅供參考" if len(eff) < _MIN_EFFECTIVE else ""
        return (f"  {label}：{len(posts)} 則（有觀看數 {len(eff)} 則），"
                f"平均互動率 {rate:.2f}%{warn}")

    lines = [f"【FB 長期檔期型態（{len(rows)} 則，{min(taipei(p) for p in rows).date()} 起）】",
             "  ※ 以下為跨週累積型態，用來支撐「後續規劃」的排程建議；"
             "括號中的「有觀看數」是有效樣本數，樣本偏少者不可當作結論。"]

    by_wd = {d: [] for d in _WEEKDAYS}
    for p in rows:
        by_wd[_WEEKDAYS[taipei(p).weekday()]].append(p)
    lines.append(" ─ 依星期 ─")
    lines += [slice_line(f"週{d}", by_wd[d]) for d in _WEEKDAYS]

    slots = {"09-11 早": [], "12-14 午": [], "15-18 下午": [], "19-21 晚": [], "其他時段": []}
    for p in rows:
        h = taipei(p).hour
        key = ("09-11 早" if 9 <= h < 12 else "12-14 午" if 12 <= h < 15
               else "15-18 下午" if 15 <= h < 19 else "19-21 晚" if 19 <= h < 22 else "其他時段")
        slots[key].append(p)
    lines.append(" ─ 依發布時段（台灣時間）─")
    lines += [slice_line(k, v) for k, v in slots.items() if v]

    lines.append(" ─ 依題材（關鍵字比對，一則可能落入多個題材，不可加總）─")
    for name, kws in _THEME_KEYWORDS.items():
        lines.append(slice_line(name, [p for p in rows
                                       if any(k in (p.get("message") or "") for k in kws)]))

    def prize_block(label, kws):
        ps = [p for p in rows if any(k in (p.get("message") or "") for k in kws)
              and any(k in (p.get("message") or "") for k in _THEME_KEYWORDS["抽獎／贈獎"])]
        if not ps:
            return None
        best = max(ps, key=eng)
        es = sorted((eng(p) for p in ps), reverse=True)
        return (f"  {label}：{len(ps)} 則，最高互動 {es[0]}，前三名 {es[:3]}，"
                f"代表作「{_clean_title(best.get('message') or '', 18)}」")

    is_draw = lambda p: any(k in (p.get("message") or "")
                            for k in _THEME_KEYWORDS["抽獎／贈獎"])
    phys = [p for p in rows if is_draw(p)
            and any(k in (p.get("message") or "") for k in _PHYSICAL_PRIZE)]
    virt = [p for p in rows if is_draw(p)
            and any(k in (p.get("message") or "") for k in _VIRTUAL_PRIZE)]

    pb = [b for b in (prize_block("實體獎品", _PHYSICAL_PRIZE),
                      prize_block("遊戲內獎品", _VIRTUAL_PRIZE)) if b]
    if len(pb) == 2:
        lines.append(" ─ 抽獎獎品類型 ─")
        lines += pb

    gaps = _gap_lines(rows, taipei, views, eng, by_wd, phys, virt)
    if gaps:
        lines.append(" ─ 排程落差（請在「後續規劃」中引用，每一點都要提到）─")
        lines += [f"  {i}. {g}" for i, g in enumerate(gaps, 1)]

    return "\n".join(lines)


def _gap_lines(rows, taipei, views, eng, by_wd, phys, virt) -> list:
    """The conclusions a reader should draw from the pattern tables.

    Kept separate because the report inserts these verbatim: asked to summarise
    them the model dropped two of three and inverted the third.
    """
    gaps = []
    rated = [(d, by_wd[d], [p for p in by_wd[d] if views(p)]) for d in _WEEKDAYS]
    scored = [(d, posts, sum(eng(p) / views(p) * 100 for p in eff) / len(eff))
              for d, posts, eff in rated if len(eff) >= _MIN_EFFECTIVE]
    empty = [d for d, posts, _ in rated if not posts]
    if empty:
        gaps.append(f"週{'、週'.join(empty)}在統計區間內完全沒有發文，是未被使用的檔期。")
    if len(scored) >= 2:
        worst = min(scored, key=lambda x: x[2])
        best = max(scored, key=lambda x: x[2])
        gaps.append(
            f"週{worst[0]}平均互動率最低（{worst[2]:.2f}%）卻排了 {len(worst[1])} 則；"
            f"週{best[0]}最高（{best[2]:.2f}%）排了 {len(best[1])} 則。"
            "發文量與互動率並不一致，排程有調整空間。"
        )
    if phys and virt:
        pe, ve = max(eng(p) for p in phys), max(eng(p) for p in virt)
        if ve:
            gaps.append(
                f"抽獎獎品以實體效果較佳：實體獎品最高互動 {pe}，遊戲內獎品最高 {ve}，"
                f"相差 {pe / ve:.1f} 倍（實體 {len(phys)} 則、遊戲內 {len(virt)} 則，"
                "樣本皆偏少，僅供參考）。"
            )
    return gaps


def scheduling_gap_lines(brand: str, before_date: str | None = None) -> list:
    """Scheduling gaps on their own, for insertion straight into the outline."""
    from collections import defaultdict
    from datetime import timedelta
    from models import supabase

    try:
        rows = supabase.table("posts").select("*") \
            .eq("brand_name", brand).eq("platform", "fb").execute().data or []
    except Exception:
        return []
    if before_date:
        rows = [p for p in rows if p.get("created_at", "")[:10] <= before_date]
    if len(rows) < 30:
        return []

    def taipei(p):
        return datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) + timedelta(hours=8)

    def views(p):
        m = p.get("metrics") or {}
        return m.get("total_views") or m.get("video_views") or 0

    def eng(p):
        return (p.get("metrics") or {}).get("engagement") or 0

    by_wd = defaultdict(list)
    for d in _WEEKDAYS:
        by_wd[d] = []
    for p in rows:
        by_wd[_WEEKDAYS[taipei(p).weekday()]].append(p)

    def is_draw(p):
        return any(k in (p.get("message") or "") for k in _THEME_KEYWORDS["抽獎／贈獎"])

    phys = [p for p in rows if is_draw(p)
            and any(k in (p.get("message") or "") for k in _PHYSICAL_PRIZE)]
    virt = [p for p in rows if is_draw(p)
            and any(k in (p.get("message") or "") for k in _VIRTUAL_PRIZE)]
    return _gap_lines(rows, taipei, views, eng, by_wd, phys, virt)
