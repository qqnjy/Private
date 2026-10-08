"""Collect authorized project follower flows without persisting credentials."""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import httpx
from dotenv import load_dotenv
from follower_insights import DATA_PATH, PROJECTS, TAIPEI, fb_daily_rows, ig_daily_row

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


def fetch_project(page, token, start, end):
    rows, errors = [], []
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
            rows.extend(r for r in fb_daily_rows(payload) if start.isoformat() <= r['date'] <= end.isoformat())
        except RuntimeError as exc:
            errors.append('FB：' + str(exc))
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
                return None, 'IG：' + str(exc)
        dates = [start + timedelta(days=i) for i in range((end-start).days + 1)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row, error in pool.map(fetch_day, dates):
                if row:
                    rows.append(row)
                if error:
                    errors.append(error)
    else:
        errors.append('粉專未連結 IG 帳號')
    return rows, errors


def collect(start=None, end=None, project=None):
    token = os.getenv('FB_GRAPH_TOKEN')
    if not token:
        raise RuntimeError('缺少 FB_GRAPH_TOKEN，未修改既有資料')
    yesterday = datetime.now(TAIPEI).date() - timedelta(days=1)
    end = min(end or yesterday, yesterday)
    start = start or end - timedelta(days=6)
    if start > end:
        raise ValueError('開始日期不能晚於結束日期')
    selected = [p for p in PROJECTS if project is None or p['key'] == project]
    if not selected:
        raise ValueError('未知專案')
    pages = graph_get('me/accounts', {'access_token': token, 'fields': 'id,name,access_token,instagram_business_account', 'limit': 100})
    page_lookup = {p['id']: p for p in pages.get('data', [])}
    snapshot = json.loads(DATA_PATH.read_text(encoding='utf-8')) if DATA_PATH.exists() else {'rows': []}
    stored = {(r.get('project', 'tmd'), r['platform'], r['date']): {**r, 'project': r.get('project', 'tmd')} for r in snapshot['rows']}
    statuses = snapshot.get('project_status', {})
    # Migrate the existing TMD snapshot without changing its recorded values.
    statuses.setdefault('tmd', {'updated_at': snapshot.get('updated_at')})
    successes = 0
    for item in selected:
        key = item['key']
        print('正在更新：' + item['name'], flush=True)
        page = page_lookup.get(item['page_id'])
        rows, errors = fetch_project(page, token, start, end) if page else ([], ['既有授權找不到此粉專'])
        attempt = datetime.now(TAIPEI).isoformat()
        if errors:
            statuses[key] = {**statuses.get(key, {}), 'last_attempt': attempt, 'error': '；'.join(sorted(set(errors)))}
            print(item['name'] + '：保留既有資料，' + statuses[key]['error'], flush=True)
            continue
        for row in rows:
            row['project'] = key
            record_key = (key, row['platform'], row['date'])
            prior = stored.get(record_key, {})
            for field in ('follows', 'unfollows'):
                if row[field] is None and prior.get(field) is not None:
                    row[field] = prior[field]
            stored[record_key] = row
        statuses[key] = {'updated_at': attempt, 'last_attempt': attempt, 'error': None}
        successes += 1
        print('%s：更新 %d 筆每日資料' % (item['name'], len(rows)), flush=True)
    if not successes:
        raise RuntimeError('所有專案讀取失敗，未覆寫既有檔案')
    snapshot.pop('brand', None)
    snapshot.update({'version': 2, 'updated_at': datetime.now(TAIPEI).isoformat(), 'project_status': statuses,
        'reporting_windows': {'fb': 'Meta daily buckets', 'ig': 'Asia/Taipei calendar day'},
        'rows': sorted(stored.values(), key=lambda r: (r['project'], r['date'], r['platform']))})
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(DATA_PATH)
    print('已更新 %d／%d 個專案：%s 至 %s，累積 %d 筆（不含權杖）' % (successes, len(selected), start, end, len(stored)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat)
    parser.add_argument('--project', choices=[p['key'] for p in PROJECTS])
    args = parser.parse_args()
    collect(args.start, args.end, args.project)
