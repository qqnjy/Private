import os
import glob
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. Map files to Target IDs (we infer this from the names)
FILE_MAP = {
    "滿貫大亨粉絲團追蹤人數.csv": 1,
    "明星3缺1粉絲團追蹤人數.csv": 2,
    "競技麻將2粉絲團追蹤人數.csv": 3,
    "大滿貫粉絲團追蹤人數.csv": 4,
    "明星3缺1IG追蹤人數.csv.csv": 5,
    "滿貫大亨IG追蹤數.csv": 6,
    "競技麻將2IG追蹤人數.csv": 7,
    # 8 is 大滿貫IG (not in files)
    "金好運粉絲團追蹤人數.csv": 9,
    "金好運IG追蹤人數.csv": 10,
    "玩星派對粉絲團追蹤人數.csv": 11,
    "玩星派對IG追蹤人數.csv": 12,
}

# 2. Fetch today's actual numbers and targets from Supabase
print("Fetching from Supabase...")
headers = {
    'apikey': 'sb_publishable_Lal67MF3Igaoq1lCEHlYCw_EFRPkSsA',
    'Authorization': 'Bearer sb_publishable_Lal67MF3Igaoq1lCEHlYCw_EFRPkSsA'
}
targets_res = requests.get('https://rlrpiawkdqatrsqtjiaz.supabase.co/rest/v1/targets?select=*', headers=headers).json()
records_res = requests.get('https://rlrpiawkdqatrsqtjiaz.supabase.co/rest/v1/records?select=*&order=scraped_at.desc&limit=100', headers=headers).json()

# Create lookup dictionaries
targets_dict = {t['id']: t for t in targets_res}

# Get latest followers for each target_id
latest_followers = {}
for r in records_res:
    tid = r['target_id']
    if tid not in latest_followers:
        latest_followers[tid] = r['followers']

print("Latest Followers mapped:", latest_followers)

# 3. Process each CSV and calculate backwards
results = [] # list of dicts: {'date': '2026-06-16', 'platform': 'FB', 'name': '...', 'followers': 1234}

for file_name, target_id in FILE_MAP.items():
    if not os.path.exists(file_name):
        print(f"File not found: {file_name}")
        continue
    
    target_info = targets_dict.get(target_id)
    if not target_info:
        continue
        
    platform = target_info['platform'].upper()
    name = target_info['name'].encode('latin1').decode('utf-8', errors='ignore') if '?' in target_info['name'] else target_info['name']
    
    # Try to read name cleanly if it's messed up by console encoding earlier
    clean_name = file_name.replace("追蹤人數.csv", "").replace("追蹤數.csv", "").replace(".csv", "")
    
    current_followers = latest_followers.get(target_id)
    if current_followers is None:
        print(f"No current followers for {file_name}")
        continue
        
    print(f"Processing {file_name} (Current: {current_followers})")
    
    # Add today's record
    today_str = datetime.now().strftime("%Y-%m-%d")
    results.append({
        'date': today_str,
        'platform': platform,
        'name': clean_name,
        'followers': current_followers
    })
    
    # Read CSV
    try:
        # Some files have 'sep=,' in the first line and utf-16 BOM
        with open(file_name, 'rb') as f:
            raw = f.read()
        
        encoding = 'utf-8'
        if raw.startswith(b'\xff\xfe'):
            encoding = 'utf-16'
        elif raw.startswith(b'\xef\xbb\xbf'):
            encoding = 'utf-8-sig'
            
        with open(file_name, 'r', encoding=encoding, errors='replace') as f:
            lines = f.readlines()
            
        # parse lines
        data_rows = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('sep=') or 'Primary' in line or line.startswith('\ufeff'):
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                date_str = parts[0].strip().replace('"', '')
                inc_str = parts[1].strip().replace('"', '')
                try:
                    inc_val = int(float(inc_str)) # might be float
                    dt = datetime.fromisoformat(date_str.replace('Z', ''))
                    data_rows.append((dt.strftime("%Y-%m-%d"), inc_val))
                except Exception:
                    pass
        
        # Sort desc by date
        data_rows.sort(key=lambda x: x[0], reverse=True)
        
        # Calculate backwards
        # If increase is for Date D, then followers at D-1 = followers(D) - increase(D)
        # We start with `current_followers` which represents today.
        
        running_followers = current_followers
        last_date_recorded = today_str
        
        for d_str, inc in data_rows:
            if d_str == today_str:
                # If there's an increase entry for today, we subtract it to get yesterday
                running_followers -= inc
                last_date_recorded = (datetime.strptime(d_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                results.append({
                    'date': last_date_recorded,
                    'platform': platform,
                    'name': clean_name,
                    'followers': running_followers
                })
            else:
                # we assume the running_followers is for the date right after this increase
                # Actually, simply:
                running_followers -= inc
                d_prev = (datetime.strptime(d_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                results.append({
                    'date': d_prev,
                    'platform': platform,
                    'name': clean_name,
                    'followers': running_followers
                })

    except Exception as e:
        print(f"Error parsing {file_name}: {e}")

# 4. Write to Obsidian
OBSIDIAN_VAULT_PATH = r"F:\QQN\QQN"
OBSIDIAN_FILE_NAME = "粉絲團歷史數據.md"  # Writing to a new file to prevent breaking the old one completely, or appending?
# I'll overwrite "粉絲團歷史推算數據.md" so it's a complete clean record

out_path = os.path.join(OBSIDIAN_VAULT_PATH, OBSIDIAN_FILE_NAME)
try:
    os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 粉絲團與IG歷史推算數據\n\n")
        f.write("> 此為由今日數據往前推算之完整紀錄\n\n")
        f.write("| 日期 | 平台 | 粉絲團/IG名稱 | 粉絲數 |\n")
        f.write("| --- | --- | --- | --- |\n")
        
        # Sort results by date ascending, then platform, then name
        results.sort(key=lambda x: (x['date'], x['platform'], x['name']))
        
        for r in results:
            f.write(f"| {r['date']} | {r['platform']} | {r['name']} | {r['followers']:,} |\n")
            
    print(f"Successfully saved calculated data to {out_path}")
except Exception as e:
    print(f"Failed to write to Obsidian: {e}")

