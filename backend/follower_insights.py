"""Read durable follower-flow snapshots; no credentials are returned to clients."""
import calendar
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA_PATH = Path(__file__).parent / 'data' / 'follower_daily.json'
TAIPEI = timezone(timedelta(hours=8))


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


def monthly_report(snapshot, month, today=None):
    today = today or datetime.now(TAIPEI).date()
    start = date.fromisoformat(month + '-01')
    if start > today:
        raise ValueError('請選擇本月或以前的月份')
    end = min(date(start.year, start.month, calendar.monthrange(start.year, start.month)[1]), today - timedelta(days=1))
    count = max(0, (end - start).days + 1)
    previous = start - timedelta(days=1)
    previous_start = previous.replace(day=1)
    previous_count = min(count, previous.day)
    lookup = {(r['platform'], r['date']): r for r in snapshot.get('rows', [])}
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
    return {'brand': '滿貫大亨', 'month': month, 'updated_at': snapshot.get('updated_at'),
            'period': {'start': start.isoformat(), 'end': end.isoformat() if count else None},
            'platforms': platforms,
            'notes': ['FB 依 Meta 每日區間；IG 依台灣時間每日區間。跨平台及後台比較請先對齊口徑。',
                      '新增與退追為平台回報數量，相減不一定等於追蹤總數快照的變化。',
                      '本月只列昨日以前的資料；缺值不當作 0，資料不完整時不計淨變化與月比較。']}


def load_month(month):
    if not DATA_PATH.exists():
        raise FileNotFoundError('追蹤增減資料尚未建立')
    return monthly_report(json.loads(DATA_PATH.read_text(encoding='utf-8')), month)
