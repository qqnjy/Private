import sqlite3
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

DB_PATH = r"C:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\粉絲團數據追蹤\backend\data.db"

def main():
    if not os.path.exists(DB_PATH):
        print("data.db 不存在，跳過轉移。")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Migrate targets
    cursor.execute("SELECT id, platform, url, name, tags, is_competitor FROM targets")
    targets = cursor.fetchall()
    
    # 清空 Supabase 上的 targets (視需求，如果是首次轉移可以不用清)
    # 不過為了保證一致性，如果有先建立過可能會有 conflict。這裡假設是空的或我們用 upsert。
    
    target_data = []
    for t in targets:
        target_data.append({
            "id": t[0],
            "platform": t[1],
            "url": t[2],
            "name": t[3],
            "tags": t[4] if t[4] else "",
            "is_competitor": t[5] if t[5] is not None else 0
        })
    
    if target_data:
        print(f"Migrating {len(target_data)} targets...")
        res = supabase.table("targets").upsert(target_data).execute()
        print("Targets migrated.")

    # 2. Migrate records
    cursor.execute("SELECT id, target_id, followers, scraped_at FROM records")
    records = cursor.fetchall()
    
    record_data = []
    for r in records:
        record_data.append({
            "id": r[0],
            "target_id": r[1],
            "followers": r[2],
            "scraped_at": r[3] # SQLite store format: YYYY-MM-DD HH:MM:SS.mmmmmm
        })
    
    if record_data:
        print(f"Migrating {len(record_data)} records... this might take a bit for 3000+ rows.")
        # Supabase API has a limit on payload size, so batch it
        batch_size = 500
        for i in range(0, len(record_data), batch_size):
            batch = record_data[i:i+batch_size]
            supabase.table("records").upsert(batch).execute()
            print(f"Migrated batch {i} to {i+len(batch)}")
            
        print("Records migrated.")

    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    main()
