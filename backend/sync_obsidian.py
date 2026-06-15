import os
from datetime import datetime, timedelta
from models import supabase

OBSIDIAN_VAULT_PATH = r"F:\QQN\QQN"
OBSIDIAN_FILE_NAME = "粉絲團數據.md"

def sync_from_supabase(days=7):
    file_path = os.path.join(OBSIDIAN_VAULT_PATH, OBSIDIAN_FILE_NAME)
    
    # 確保檔案存在
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# 粉絲團每日追蹤數據\n\n")
            f.write("| 日期 | 平台 | 粉絲團名稱 | 粉絲數 |\n")
            f.write("| --- | --- | --- | --- |\n")
            
    # 讀取現有內容，避免重複寫入
    with open(file_path, "r", encoding="utf-8") as f:
        existing_lines = set(f.read().splitlines())

    # 取得 Target 對應表
    targets_res = supabase.table("targets").select("*").execute()
    targets = {t['id']: t for t in targets_res.data}
    
    # 計算時間範圍
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # 取得 Records
    records_res = supabase.table("records").select("*").gte("scraped_at", start_date).order("scraped_at", desc=False).execute()
    
    new_entries = []
    
    for r in records_res.data:
        t = targets.get(r['target_id'])
        if not t:
            continue
            
        # Supabase 回傳的是 UTC 時間，加上時區資訊
        date_str_utc = r['scraped_at'].replace('Z', '+00:00')
        # 如果 Supabase 沒有回傳 Z，確保它可以被正確解析
        if '+' not in date_str_utc:
            date_str_utc += '+00:00'
            
        date_obj = datetime.fromisoformat(date_str_utc)
        # 轉成台灣時間 UTC+8
        date_tw = date_obj + timedelta(hours=8)
        date_str = date_tw.strftime("%Y-%m-%d")
        
        followers = r['followers']
        platform = t['platform'].upper()
        name = t['name']
        
        log_entry = f"| {date_str} | {platform} | {name} | {followers:,} |"
        
        if log_entry not in existing_lines:
            new_entries.append(log_entry + "\n")
            existing_lines.add(log_entry) # 避免同一次迴圈內重複
            
    if new_entries:
        with open(file_path, "a", encoding="utf-8") as f:
            f.writelines(new_entries)
        print(f"成功同步了 {len(new_entries)} 筆新數據到 Obsidian！")
    else:
        print("Obsidian 已經是最新的，沒有需要同步的數據。")

if __name__ == "__main__":
    print("開始同步 Supabase 數據到 Obsidian...")
    sync_from_supabase(days=7)
