import os
import requests
from datetime import datetime, timedelta

FILE_MAP = {
    "滿貫大亨粉絲團追蹤人數.csv": 1,
    "明星3缺1粉絲團追蹤人數.csv": 2,
    "競技麻將2粉絲團追蹤人數.csv": 3,
    "大滿貫粉絲團追蹤人數.csv": 4,
    "明星3缺1IG追蹤人數.csv.csv": 5,
    "滿貫大亨IG追蹤數.csv": 6,
    "競技麻將2IG追蹤人數.csv": 7,
    "金好運粉絲團追蹤人數.csv": 9,
    "金好運IG追蹤人數.csv": 10,
    "玩星派對粉絲團追蹤人數.csv": 11,
    "玩星派對IG追蹤人數.csv": 12,
}

HEADERS = {
    'apikey': 'sb_publishable_Lal67MF3Igaoq1lCEHlYCw_EFRPkSsA',
    'Authorization': 'Bearer sb_publishable_Lal67MF3Igaoq1lCEHlYCw_EFRPkSsA',
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates,return=minimal'
}
BASE_URL = 'https://rlrpiawkdqatrsqtjiaz.supabase.co/rest/v1'

def main():
    print("抓取目前資料庫最新資料做為基準...")
    records_res = requests.get(f"{BASE_URL}/records?select=target_id,followers,scraped_at&order=scraped_at.desc&limit=2000", headers=HEADERS).json()
    
    latest_followers = {}
    for r in records_res:
        tid = r['target_id']
        if tid not in latest_followers:
            latest_followers[tid] = r['followers']

    all_inserts = []
    all_updates = []

    for file_name, target_id in FILE_MAP.items():
        if not os.path.exists(file_name):
            continue
            
        current_followers = latest_followers.get(target_id)
        if not current_followers:
            continue
            
        with open(file_name, 'rb') as f:
            raw = f.read()
        encoding = 'utf-16' if raw.startswith(b'\xff\xfe') else ('utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8')
        
        with open(file_name, 'r', encoding=encoding, errors='replace') as f:
            lines = f.readlines()
            
        data_rows = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('sep=') or 'Primary' in line or line.startswith('\ufeff'): continue
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    dt = datetime.fromisoformat(parts[0].strip().replace('"', '').replace('Z', ''))
                    inc_val = int(float(parts[1].strip().replace('"', '')))
                    data_rows.append((dt.strftime("%Y-%m-%d"), inc_val))
                except:
                    pass
                    
        data_rows.sort(key=lambda x: x[0], reverse=True)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        running_followers = current_followers
        calculated_data = {}
        
        for d_str, inc in data_rows:
            if d_str == today_str:
                running_followers -= inc
                d_prev = (datetime.strptime(d_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                calculated_data[d_prev] = running_followers
            else:
                running_followers -= inc
                d_prev = (datetime.strptime(d_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                calculated_data[d_prev] = running_followers

        # Fetch existing records
        existing_res = requests.get(f"{BASE_URL}/records?select=id,scraped_at&target_id=eq.{target_id}", headers={'apikey': HEADERS['apikey'], 'Authorization': HEADERS['Authorization']}).json()
        existing_map = {}
        for er in existing_res:
            d_str = er['scraped_at'].split('T')[0]
            existing_map[d_str] = er['id']

        for d_str, followers in calculated_data.items():
            scraped_at = f"{d_str}T00:00:00+00:00"
            obj = {'target_id': target_id, 'followers': followers, 'scraped_at': scraped_at}
            if d_str in existing_map:
                obj['id'] = existing_map[d_str]
                all_updates.append(obj)
            else:
                all_inserts.append(obj)

    print(f"準備批次更新 {len(all_updates)} 筆，新增 {len(all_inserts)} 筆...")
    
    def do_batch(payload):
        chunk_size = 500
        for i in range(0, len(payload), chunk_size):
            chunk = payload[i:i+chunk_size]
            res = requests.post(f"{BASE_URL}/records", headers=HEADERS, json=chunk)
            if res.status_code >= 400:
                print(f"批次失敗: {res.text}")
            else:
                print(f"成功處理 ({len(chunk)} 筆)")

    if all_updates:
        print("--- 執行更新 ---")
        do_batch(all_updates)
        
    if all_inserts:
        print("--- 執行新增 ---")
        do_batch(all_inserts)
        
    print("全部完成！")

if __name__ == '__main__':
    main()
