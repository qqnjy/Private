"""Collect TMD flows into a durable, credential-free snapshot in the observatory repo."""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import httpx
from dotenv import load_dotenv
from follower_insights import DATA_PATH, TAIPEI, fb_daily_rows, ig_daily_row

load_dotenv()
GRAPH = 'https://graph.facebook.com/v21.0/'


def graph_get(path, params):
    for attempt in range(3):
        try:
            response = httpx.get(GRAPH + path, params=params, timeout=25)
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise RuntimeError('Meta 連線失敗') from None
        if 'error' not in payload and response.is_success:
            return payload
        code = payload.get('error', {}).get('code')
        if code in (4, 17, 32, 613) and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        raise RuntimeError('Meta 指標讀取失敗（代碼 %s）' % code)


def collect(start=None, end=None):
    token = os.getenv('FB_GRAPH_TOKEN')
    if not token:
        raise RuntimeError('缺少 FB_GRAPH_TOKEN，未修改既有資料')
    yesterday = datetime.now(TAIPEI).date() - timedelta(days=1)
    end = min(end or yesterday, yesterday)
    start = start or end - timedelta(days=6)
    if start > end:
        raise ValueError('開始日期不能晚於結束日期')
    pages = graph_get('me/accounts', {'access_token': token, 'fields': 'id,name,access_token,instagram_business_account', 'limit': 100})
    page = next((p for p in pages.get('data', []) if p.get('name') == '滿貫大亨'), None)
    if not page:
        raise RuntimeError('既有授權找不到滿貫大亨粉專，未修改既有資料')
    snapshot = json.loads(DATA_PATH.read_text(encoding='utf-8')) if DATA_PATH.exists() else {'brand': '滿貫大亨', 'rows': []}
    stored = {(r['platform'], r['date']): r for r in snapshot['rows']}
    errors = []
    def merge(row):
        key = (row['platform'], row['date'])
        prior = stored.get(key, {})
        for field in ('follows', 'unfollows'):
            if row[field] is None and prior.get(field) is not None:
                row[field] = prior[field]
        stored[key] = row
    cursor = start
    while cursor <= end:
        stop = min(cursor + timedelta(days=29), end)
        try:
            payload = graph_get(page['id'] + '/insights', {'access_token': page.get('access_token') or token,
                'metric': 'page_daily_follows,page_daily_unfollows', 'period': 'day',
                'since': cursor.isoformat(), 'until': (stop + timedelta(days=1)).isoformat()})
            now = datetime.now(TAIPEI)
            for metric in payload.get('data', []):
                metric['values'] = [v for v in metric.get('values', []) if datetime.strptime(v['end_time'], '%Y-%m-%dT%H:%M:%S%z') <= now]
            for row in fb_daily_rows(payload):
                if start.isoformat() <= row['date'] <= end.isoformat():
                    merge(row)
        except RuntimeError as exc:
            errors.append({'platform': 'fb', 'start': cursor.isoformat(), 'end': stop.isoformat(), 'reason': str(exc)})
        cursor = stop + timedelta(days=1)
    ig_id = (page.get('instagram_business_account') or {}).get('id')
    if ig_id:
        def fetch_day(day):
            try:
                since = int(datetime.combine(day, datetime.min.time(), TAIPEI).timestamp())
                payload = graph_get(ig_id + '/insights', {'access_token': token, 'metric': 'follows_and_unfollows',
                    'period': 'day', 'metric_type': 'total_value', 'breakdown': 'follow_type',
                    'since': since, 'until': since + 86400})
                return ig_daily_row(day.isoformat(), payload), None
            except RuntimeError as exc:
                return None, {'platform': 'ig', 'date': day.isoformat(), 'reason': str(exc)}
        dates = [start + timedelta(days=i) for i in range((end-start).days + 1)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row, error in pool.map(fetch_day, dates):
                if row:
                    merge(row)
                if error:
                    errors.append(error)
    else:
        errors.append({'platform': 'ig', 'reason': '粉專未連結 IG 帳號'})
    if errors:
        # Keep the last known-good snapshot if the collection is incomplete.
        raise RuntimeError('資料讀取有 %d 個錯誤，未覆寫既有檔案：%s' % (len(errors), json.dumps(errors[:3], ensure_ascii=False)))
    snapshot.update({'updated_at': datetime.now(TAIPEI).isoformat(),
        'reporting_windows': {'fb': 'Meta daily buckets', 'ig': 'Asia/Taipei calendar day'},
        'rows': sorted(stored.values(), key=lambda r: (r['date'], r['platform']))})
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(DATA_PATH)
    print('已更新滿貫追蹤增減：%s 至 %s，累積 %d 筆（不含權杖）' % (start, end, len(stored)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat)
    args = parser.parse_args()
    collect(args.start, args.end)
