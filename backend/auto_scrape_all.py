import os
import asyncio
from models import supabase
from scraper import parse_followers
from datetime import datetime

OBSIDIAN_VAULT_PATH = r"F:\QQN\QQN"
OBSIDIAN_FILE_NAME = "粉絲團數據.md"

def update_obsidian_note(platform, name, followers):
    try:
        file_path = os.path.join(OBSIDIAN_VAULT_PATH, OBSIDIAN_FILE_NAME)
        today = datetime.now().strftime("%Y-%m-%d")
        log_entry = f"| {today} | {platform.upper()} | {name} | {followers:,} |\n"
        
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("# 粉絲團每日追蹤數據\n\n")
                f.write("| 日期 | 平台 | 粉絲團名稱 | 粉絲數 |\n")
                f.write("| --- | --- | --- | --- |\n")
                
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"成功寫入 Obsidian: {name} ({followers})")
    except Exception as e:
        print(f"寫入 Obsidian 失敗: {e}")

def run_all_scrapes():
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    print(f"開始自動排程抓取數據: {datetime.now()}")
    
    targets_res = supabase.table("targets").select("*").execute()
    targets = targets_res.data
    
    for t in targets:
        print(f"正在抓取: {t['name']} ({t['platform']})")
        try:
            followers = asyncio.run(parse_followers(t['platform'], t['url']))
            if followers >= 0:
                record_data = {"target_id": t['id'], "followers": followers}
                supabase.table("records").insert(record_data).execute()
                update_obsidian_note(t['platform'], t['name'], followers)
            else:
                print(f"抓取失敗: {t['name']}")
        except Exception as e:
            print(f"Scrape error for {t['name']}: {e}")
            
    print(f"自動排程抓取結束: {datetime.now()}")

if __name__ == "__main__":
    run_all_scrapes()
