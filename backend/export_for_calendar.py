"""Export a finished weekly report to the social-analysis folder.

The calendar workstream schedules posts from its own conversation and cannot
see this repo's Supabase data, so each week's measured results have to be
handed over as a file — the mirror image of the 週報可用事實.txt it writes for
the report side.

Usage:
    python export_for_calendar.py 滿貫大亨 2026-10-12 2026-10-18
    python export_for_calendar.py            # defaults to 滿貫大亨, last full week
"""
import io
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT_DIR = Path(r"C:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\社群分析")


def last_full_week(today=None):
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(days=7), monday - timedelta(days=1)


def build(brand: str, start: str, end: str) -> str:
    from models import supabase
    from posts_repo import get_cached_posts
    from fb_api import baseline_summary, posting_pattern_summary, fan_trend_summary
    from follower_insights import acquisition_summary

    iso = date.fromisoformat(start).isocalendar()
    parts = [
        f"{brand}｜第 {iso.week} 週社群成效（{start} ~ {end}）",
        "產出：週報端自動匯出，供社群行事曆排程參考。",
        "本檔只陳述已量測到的結果，不建議題材、不改排程、不涉及文案與 GEO。",
        "",
        "■ 本週實際發布與成效",
    ]
    cached = get_cached_posts(brand, start, end) or {}
    for plat, label in (("fb", "FB"), ("ig", "IG")):
        posts = cached.get(plat) or []
        if not posts:
            parts.append(f"  {label}：本週無貼文資料")
            continue
        parts.append(f"  {label}（{len(posts)} 篇）")
        for p in sorted(posts, key=lambda x: x["created_at"]):
            v = (p.get("total_views") or p.get("video_views")) if plat == "fb" else p.get("views")
            tag = "有hashtag" if "#" in (p.get("message") or "") else "無hashtag"
            msg = (p.get("message") or "(無文字)").splitlines()[0][:34]
            parts.append(
                f"    {p['created_at'][:10]} [{p.get('post_type') or '?'}] "
                f"觀看 {v if v else '尚待取得'}、互動 {p.get('engagement') or 0}、"
                f"留言 {p.get('comments') or 0}、{tag}｜{msg}"
            )

    for title, text in (
        ("對照凍結基準", baseline_summary(brand, start, end)),
        ("追蹤增減（真實進出）", acquisition_summary(brand, start, end)),
        ("粉絲數走勢", fan_trend_summary(brand, end)),
        ("長期檔期型態", posting_pattern_summary(brand, end)),
    ):
        if text:
            parts += ["", f"■ {title}", text]

    row = supabase.table("reports").select("outline").eq("brand_name", brand) \
        .eq("week_start", start).execute().data
    if row and row[0].get("outline"):
        parts += ["", "■ 本週週報全文（寄送給營運的版本）", row[0]["outline"].strip()]

    parts += [
        "",
        "■ 判讀提醒",
        "  1. 標示「尚待取得」的欄位代表人工補登的觀看數尚未填入，不可當作 0。",
        "  2. 互動率＝互動÷觀看；FB 圖片觀看為人工補登，與影片的 API 觀看口徑不同。",
        "  3. 單週差異可能來自檔期或題材，不足以歸因於排程調整或 GEO。",
        "  4. 樣本標示偏少者僅供參考，不可作為結論。",
        "  5. 排程與題材決策仍由社群端負責，本檔僅提供數據依據。",
    ]
    return "\n".join(parts) + "\n"


def main():
    args = sys.argv[1:]
    brand = args[0] if args else "滿貫大亨"
    if len(args) >= 3:
        start, end = args[1], args[2]
    else:
        a, b = last_full_week()
        start, end = a.isoformat(), b.isoformat()

    doc = build(brand, start, end)
    iso = date.fromisoformat(start).isocalendar()
    out = OUT_DIR / f"週報成效_{brand}_第{iso.week}週_{start}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"已匯出：{out}（{len(doc)} 字）")


if __name__ == "__main__":
    main()
