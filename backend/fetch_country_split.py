"""Break Facebook followers down by country.

Several pages are international — 明星3缺1 carries Hong Kong, Singapore and
Macau alongside Taiwan — so a single follower total hides how much of the
audience is actually local. page_follows_country gives the split, but only with
period=day; lifetime returns nothing.
"""
import csv
import io
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import load_dotenv

load_dotenv()
from collect_follower_insights import graph_get
from follower_insights import PROJECTS

NAMES = {"TW": "台灣", "HK": "香港", "SG": "新加坡", "MO": "澳門", "MY": "馬來西亞",
         "CN": "中國", "JP": "日本", "US": "美國", "ID": "印尼", "VN": "越南",
         "TH": "泰國", "PH": "菲律賓", "KR": "南韓", "GB": "英國", "AU": "澳洲",
         "CA": "加拿大", "KH": "柬埔寨", "BN": "汶萊", "MM": "緬甸"}


def page_tokens():
    data = graph_get("me/accounts", {"access_token": os.getenv("FB_GRAPH_TOKEN"),
                                     "fields": "id,access_token", "limit": 100}).get("data", [])
    return {p["id"]: p["access_token"] for p in data}


def country_split(page_id, token, day):
    """Latest country breakdown at or before `day`."""
    payload = graph_get(f"{page_id}/insights", {
        "access_token": token, "metric": "page_follows_country", "period": "day",
        "since": (day - timedelta(days=5)).isoformat(), "until": day.isoformat()})
    vals = (payload.get("data") or [{}])[0].get("values") or []
    for v in reversed(vals):
        if v.get("value"):
            return v["end_time"][:10], v["value"]
    return None, {}


def main():
    tokens = page_tokens()
    today = date.today()
    rows = []
    for p in PROJECTS:
        tok = tokens.get(p["page_id"])
        if not tok:
            print(f"  ✗ {p['name']}：無 Page Token")
            continue
        try:
            when, split = country_split(p["page_id"], tok, today)
        except Exception as exc:
            print(f"  ✗ {p['name']}：{str(exc)[:60]}")
            continue
        if not split:
            print(f"  ✗ {p['name']}：無國家別資料")
            continue
        total = sum(split.values())
        tw = split.get("TW", 0)
        top = sorted(split.items(), key=lambda kv: -kv[1])[:4]
        print(f"  {p['name']:<8} {when}  合計 {total:>9,}　台灣 {tw:>9,}（{tw / total * 100:5.1f}%）"
              f"　其餘前三：{'、'.join(f'{NAMES.get(c, c)} {n:,}' for c, n in top if c != 'TW')[:46]}")
        for c, n in sorted(split.items(), key=lambda kv: -kv[1]):
            rows.append({"date": when, "brand": p["name"], "country": c,
                         "country_name": NAMES.get(c, c), "followers": n,
                         "share_pct": round(n / total * 100, 3)})

    out = Path.home() / "Downloads" / "FB粉絲國家別_2026.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "brand", "country", "country_name",
                                           "followers", "share_pct"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n已匯出 {out}（{len(rows):,} 筆）")


if __name__ == "__main__":
    main()
