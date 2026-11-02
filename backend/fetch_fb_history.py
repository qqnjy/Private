"""Pull true daily Facebook follower totals from the Graph API.

The 2026 history in `records` before 2026-06-15 was reconstructed by
過往資料/calc_history.py, which walked backwards from today subtracting the
CSV's daily NEW follows. That column is gross follows, not net change, so the
series sinks the further back it goes — four IG accounts went negative. The
page_follows insight gives the real running total instead, and reaches back to
at least January, so the Facebook side can simply be refetched.

Needs a Page access token, not the user token: page_follows refuses the latter.
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

START, END = date(2026, 1, 1), date.today()


def page_tokens():
    data = graph_get("me/accounts", {"access_token": os.getenv("FB_GRAPH_TOKEN"),
                                     "fields": "id,name,access_token", "limit": 100}).get("data", [])
    return {p["id"]: p["access_token"] for p in data}


def daily_follows(page_id, token, start, end):
    """page_follows, day by day. Meta caps the window, so walk it in chunks."""
    out, cursor = {}, start
    while cursor <= end:
        stop = min(cursor + timedelta(days=29), end)
        payload = graph_get(f"{page_id}/insights", {
            "access_token": token, "metric": "page_follows", "period": "day",
            "since": cursor.isoformat(), "until": (stop + timedelta(days=1)).isoformat()})
        for v in (payload.get("data") or [{}])[0].get("values", []):
            # end_time marks the close of the bucket, so the figure is that day's.
            out[v["end_time"][:10]] = v["value"]
        cursor = stop + timedelta(days=1)
    return out


def main():
    tokens = page_tokens()
    rows, summary = [], []
    for p in PROJECTS:
        tok = tokens.get(p["page_id"])
        if not tok:
            print(f"  ✗ {p['name']}：取不到 Page Token，略過")
            continue
        try:
            series = daily_follows(p["page_id"], tok, START, END)
        except Exception as exc:
            print(f"  ✗ {p['name']}：{str(exc)[:70]}")
            continue
        if not series:
            print(f"  ✗ {p['name']}：無資料")
            continue
        days = sorted(series)
        rows += [{"date": d, "brand": p["name"], "platform": "FB", "followers": series[d]}
                 for d in days]
        summary.append((p["name"], days[0], series[days[0]], days[-1], series[days[-1]]))
        print(f"  ✓ {p['name']}：{len(days)} 天　{days[0]} {series[days[0]]:,} → {days[-1]} {series[days[-1]]:,}")

    out = Path.home() / "Downloads" / f"FB粉絲數_GraphAPI實際值_2026.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "brand", "platform", "followers"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["brand"], r["date"])))
    print(f"\n已匯出 {out}（{len(rows):,} 筆）")
    return summary


if __name__ == "__main__":
    main()
