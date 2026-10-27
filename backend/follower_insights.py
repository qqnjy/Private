"""Read durable follower-flow snapshots; no credentials are returned to clients."""
import calendar
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA_PATH = Path(__file__).parent / 'data' / 'follower_daily.json'
TAIPEI = timezone(timedelta(hours=8))
PROJECTS = [
    {'key': 'tmd', 'name': '滿貫大亨', 'page_id': '244504085653567'},
    {'key': 'mjstar31', 'name': '明星3缺1', 'page_id': '285546094839900'},
    {'key': 'donut', 'name': '競技麻將2', 'page_id': '323273157717210'},
    {'key': 'panther', 'name': '金好運', 'page_id': '1784471515125001'},
    {'key': 'partygo', 'name': '玩星派對', 'page_id': '107262232363722'},
    {'key': 'slam888', 'name': '大滿貫', 'page_id': '306343012746356'},
    {'key': 'hoyeah', 'name': '金猴爺', 'page_id': '612956795508104'},
]


def project_choices():
    return [{'key': p['key'], 'name': p['name']} for p in PROJECTS]


def fb_daily_rows(payload):
    rows = {}
    for metric in payload.get('data', []):
        field = {'page_daily_follows': 'follows', 'page_daily_unfollows': 'unfollows'}.get(metric['name'])
        if not field:
            continue
        for item in metric.get('values', []):
            # Meta closes these daily buckets on the following calendar day.
            day = (datetime.strptime(item['end_time'], '%Y-%m-%dT%H:%M:%S%z') - timedelta(days=1)).date().isoformat()
            rows.setdefault(day, {'date': day, 'platform': 'fb', 'follows': None, 'unfollows': None})[field] = item.get('value')
    return list(rows.values())


def ig_daily_row(day, payload):
    row = {'date': day, 'platform': 'ig', 'follows': None, 'unfollows': None}
    for metric in payload.get('data', []):
        if metric.get('name') != 'follows_and_unfollows':
            continue
        for breakdown in metric.get('total_value', {}).get('breakdowns', []):
            keys = breakdown.get('dimension_keys', [])
            if 'follow_type' not in keys:
                continue
            index = keys.index('follow_type')
            for item in breakdown.get('results', []):
                values = item.get('dimension_values', [])
                kind = values[index] if len(values) > index else None
                field = {'FOLLOWER': 'follows', 'NON_FOLLOWER': 'unfollows'}.get(kind)
                if field:
                    row[field] = item.get('value')
    return row


def summarize(rows):
    def total(field):
        values = [r[field] for r in rows if r.get(field) is not None]
        return sum(values) if values else None
    follows, unfollows = total('follows'), total('unfollows')
    complete = sum(r.get('follows') is not None and r.get('unfollows') is not None for r in rows)
    return {'follows': follows, 'unfollows': unfollows,
            'net': follows - unfollows if complete == len(rows) and rows and follows is not None and unfollows is not None else None,
            'complete_days': complete, 'expected_days': len(rows),
            'is_complete': bool(rows) and complete == len(rows)}


def monthly_report(snapshot, month, today=None, project='tmd'):
    selected = next((p for p in PROJECTS if p['key'] == project), None)
    if not selected:
        raise ValueError('未知專案')
    today = today or datetime.now(TAIPEI).date()
    start = date.fromisoformat(month + '-01')
    if start > today:
        raise ValueError('請選擇本月或以前的月份')
    end = min(date(start.year, start.month, calendar.monthrange(start.year, start.month)[1]), today - timedelta(days=1))
    count = max(0, (end - start).days + 1)
    previous = start - timedelta(days=1)
    previous_start = previous.replace(day=1)
    previous_count = min(count, previous.day)
    lookup = {(r['platform'], r['date']): r for r in snapshot.get('rows', []) if r.get('project', 'tmd') == project}
    def days(platform, first, n):
        out = []
        for offset in range(n):
            day = (first + timedelta(days=offset)).isoformat()
            r = lookup.get((platform, day), {})
            follows, unfollows = r.get('follows'), r.get('unfollows')
            out.append({'date': day, 'follows': follows, 'unfollows': unfollows,
                        'net': follows - unfollows if follows is not None and unfollows is not None else None})
        return out
    platforms = {}
    for platform in ('fb', 'ig'):
        rows = days(platform, start, count)
        comparison_count = previous_count if count < calendar.monthrange(start.year, start.month)[1] else previous.day
        prev_rows = days(platform, previous_start, comparison_count)
        partial_month = count < calendar.monthrange(start.year, start.month)[1]
        comparable_rows = rows[:previous_count] if partial_month else rows
        current, prior = summarize(rows), summarize(prev_rows)
        comparable = summarize(comparable_rows)
        change = {}
        for field in ('follows', 'unfollows', 'net'):
            change[field] = comparable[field] - prior[field] if comparable['is_complete'] and prior['is_complete'] else None
        platforms[platform] = {'rows': rows, 'summary': current, 'previous': prior,
                               'change': change, 'comparison_current': summarize(comparable_rows),
                               'previous_period': {'start': previous_start.isoformat(), 'end': prev_rows[-1]['date'] if prev_rows else None}}
    status = snapshot.get('project_status', {}).get(project, {})
    updated_at = status.get('updated_at') or (snapshot.get('updated_at') if project == 'tmd' and not snapshot.get('project_status') else None)
    return {'brand': selected['name'], 'project_key': project, 'projects': project_choices(),
            'collection_error': status.get('error'), 'month': month, 'updated_at': updated_at,
            'period': {'start': start.isoformat(), 'end': end.isoformat() if count else None},
            'platforms': platforms,
            'notes': ['FB 依 Meta 每日區間；IG 依台灣時間每日區間。跨平台及後台比較請先對齊口徑。',
                      '新增與退追為平台回報數量，相減不一定等於追蹤總數快照的變化。',
                      '本月只列昨日以前的資料；缺值不當作 0，資料不完整時不計淨變化與月比較。']}


def load_month(month, project='tmd'):
    if not DATA_PATH.exists():
        raise FileNotFoundError('追蹤增減資料尚未建立')
    return monthly_report(json.loads(DATA_PATH.read_text(encoding='utf-8')), month, project=project)


def _week_rows(rows, project, platform, start, end):
    return [r for r in rows
            if r.get('project') == project and r.get('platform') == platform
            and start <= r.get('date', '') <= end]


def _prev_day(d):
    from datetime import date as _d, timedelta as _t
    return (_d.fromisoformat(d) - _t(days=1)).isoformat()


def acquisition_summary(brand_name, week_start, week_end):
    """Gross follows/unfollows for the week, with the other brands as benchmark.

    The weekly report goes to the ops team, and the point it has to make is that
    a net follower loss here is an acquisition problem, not a churn problem —
    which only the gross split can show. Rates are normalised by follower base
    so a 45k page and an 880k page can sit in the same table.
    """
    if not DATA_PATH.exists():
        return ''
    try:
        snapshot = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    except Exception:
        return ''
    rows = snapshot.get('rows') or []
    me = next((p for p in PROJECTS if p['name'] == brand_name), None)
    if not me:
        return ''

    from fb_api import get_historical_fans

    def totals(project, platform):
        wk = _week_rows(rows, project, platform, week_start, week_end)
        f = [r['follows'] for r in wk if r.get('follows') is not None]
        u = [r['unfollows'] for r in wk if r.get('unfollows') is not None]
        if not f and not u:
            return None
        return {'follows': sum(f), 'unfollows': sum(u), 'days': len(wk)}

    lines = []
    for platform, label in (('fb', 'FB'), ('ig', 'IG')):
        t = totals(me['key'], platform)
        if not t:
            continue
        net = t['follows'] - t['unfollows']
        block = (f"【{label} 本週追蹤增減（真實進出，非淨值）】\n"
                 f"  新增追蹤 {t['follows']:,} 人、退追 {t['unfollows']:,} 人、淨 {net:+,} 人"
                 f"（{t['days']} 天資料）")
        # Cross-check against the scraped follower count. Meta's daily buckets
        # occasionally absorb several days at once — every brand spiked on
        # 2026-10-25 — and a gross net that contradicts the actual change must
        # not be reported as though it were sound.
        before = get_historical_fans(brand_name, platform, _prev_day(week_start))
        after = get_historical_fans(brand_name, platform, week_end)
        if before and after:
            actual = after - before
            if abs(net - actual) > max(10, abs(actual) * 0.5):
                block += (f"\n  ※ 本週粉絲數實際變化為 {actual:+,} 人（{before:,} → {after:,}），"
                          f"與上列淨值相差 {net - actual:+,}。兩者口徑不同：新增／退追是當日發生數，"
                          f"粉絲數是當日快照，週末或週界的變動常落在下一次快照才反映。"
                          f"對外引用粉絲增減請以粉絲數為準。")
        week_rows_ = _week_rows(rows, me['key'], platform, week_start, week_end)
        daily = sorted((r.get('follows') or 0) for r in week_rows_)
        if len(daily) >= 4:
            mid = daily[len(daily) // 2]
            if daily[-1] > max(5, mid * 5):
                peak = max(week_rows_, key=lambda r: r.get('follows') or 0)
                block += (f"\n  ※ 單日新增高峰 {daily[-1]:,} 人（{peak['date']}），"
                          f"為當週中位數 {mid:,} 的數倍。這類高峰通常有外部成因"
                          f"（線下活動、擺攤、廣告投放、KOL 合作等），"
                          f"**撰寫報告前務必確認當天發生了什麼**，不可逕自當成資料異常或自然成長。")
        lines.append(block)

    bench = []
    for p in PROJECTS:
        t = totals(p['key'], 'fb')
        base = get_historical_fans(p['name'], 'fb', week_end)
        if not t or not base:
            continue
        bench.append((p['name'], base, t['follows'], t['unfollows'],
                      t['follows'] / base * 100, t['unfollows'] / base * 100))
    if len(bench) > 1:
        lines.append("")
        lines.append("【各專案 FB 新增／退追對比（本週，率＝人數÷粉絲基數）】")
        for n, b, f, u, fr, ur in sorted(bench, key=lambda r: -r[4]):
            mark = "  ← 本專案" if n == brand_name else ""
            lines.append(
                f"  {n}：基數 {b:,}，新增 {f:,}（{fr:.3f}%）、退追 {u:,}（{ur:.3f}%）{mark}"
            )
        lines.append("  解讀重點：退追率若與其他專案相近，粉絲淨減的原因就不是內容不受歡迎，"
                     "而是新增追蹤太少（缺乏遊戲內導流等進水來源）。")
    return "\n".join(lines)
