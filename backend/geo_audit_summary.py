"""Summarise the manual AI-answer audit for the weekly report.

GEO cannot be read off Meta or Google Trends — whether an AI answer cites us is
only observable by asking the models and writing it down. This turns that sheet
into the FY27 KPI (我方資產被引用題數 ÷ 總題數) and a per-platform breakdown.
"""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

AUDIT_DIR = Path(r"C:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\社群分析\GEO巡檢")
PLATFORM_LABEL = {"chatgpt": "ChatGPT", "gemini": "Gemini",
                  "google_ai": "Google AI 模式", "perplexity": "Perplexity"}


def load():
    path = AUDIT_DIR / "巡檢記錄.csv"
    if not path.exists():
        return [], {}
    rows = [r for r in csv.DictReader(path.open(encoding="utf-8")) if r.get("date")]
    questions = {}
    qpath = AUDIT_DIR / "題目清單.csv"
    if qpath.exists():
        questions = {r["question_id"]: r for r in csv.DictReader(qpath.open(encoding="utf-8"))}
    return rows, questions


def summarise(rows, questions, month=None):
    months = sorted({r["date"][:7] for r in rows})
    if not months:
        return "【GEO AI 答案巡檢】尚無巡檢記錄，本月份待執行。"
    month = month or months[-1]
    cur = [r for r in rows if r["date"].startswith(month)]
    if not cur:
        return f"【GEO AI 答案巡檢】{month} 無記錄。"

    def rate(subset):
        if not subset:
            return None
        hit = sum(1 for r in subset if r.get("mentioned") == "yes")
        return hit, len(subset), hit / len(subset) * 100

    lines = [f"【GEO AI 答案巡檢｜{month}】（人工巡檢，無痕未登入）"]
    hit, total, pct = rate(cur)
    lines.append(f"  提及率：{hit}/{total} 題次（{pct:.1f}%）")

    ours = sum(1 for r in cur if (r.get("our_source") or "none") != "none")
    lines.append(f"  引用我方資產：{ours}/{total} 題次"
                 f"（{ours / total * 100:.1f}%）← FY27 KPI")

    by_plat = defaultdict(list)
    for r in cur:
        by_plat[r.get("platform") or "?"].append(r)
    lines.append("  各平台提及率：")
    for p, rs in sorted(by_plat.items()):
        h, t, pc = rate(rs)
        lines.append(f"    {PLATFORM_LABEL.get(p, p)}：{h}/{t}（{pc:.1f}%）")

    missed = sorted({r["question_id"] for r in cur if r.get("mentioned") != "yes"})
    if missed:
        lines.append("  完全未被提及的題目：")
        for q in missed:
            if all(r.get("mentioned") != "yes" for r in cur if r["question_id"] == q):
                text = (questions.get(q) or {}).get("question", q)
                lines.append(f"    {q} {text}")

    prev = [m for m in months if m < month]
    if prev:
        p_rows = [r for r in rows if r["date"].startswith(prev[-1])]
        ph, pt, ppc = rate(p_rows)
        lines.append(f"  對比 {prev[-1]}：提及率 {ppc:.1f}% → {pct:.1f}%（{pct - ppc:+.1f} 個百分點）")
    else:
        lines.append("  首次巡檢，尚無對比基準；至少累積三個月才看趨勢。")

    notes = [r["note"] for r in cur if r.get("note")]
    if notes:
        lines.append("  值得注意：")
        lines += [f"    - {n}" for n in dict.fromkeys(notes)]

    lines.append("  說明：rank 空白代表未被提及，不計為最差名次；單月結果會因模型更新跳動。")
    return "\n".join(lines)


if __name__ == "__main__":
    rows, questions = load()
    print(summarise(rows, questions, sys.argv[1] if len(sys.argv) > 1 else None))
