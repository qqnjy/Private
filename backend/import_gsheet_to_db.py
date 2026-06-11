import urllib.request
import csv
import io
from datetime import datetime
from sqlalchemy.orm import Session
from models import SessionLocal, Target, Record, init_db

url = 'https://docs.google.com/spreadsheets/d/1636fAV2ug0XkSuMKiR2jHh6CVNso9vZlYNo0G2bwajM/export?format=csv&gid=929078381'
print("下載資料中...")
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    content = res.read().decode('utf-8')

reader = csv.reader(io.StringIO(content))
rows = list(reader)

init_db()
db = SessionLocal()

# 目標 ID (從資料庫查詢得知)
# (2, 'fb', 'https://www.facebook.com/Gametower371', '明星3缺1粉絲團', '', 0)
# (5, 'ig', 'https://www.instagram.com/mjstar_371', '明星3缺1_IG', '', 0)
target_fb_id = 2
target_ig_id = 5

added_count = 0
skip_count = 0

print("開始匯入資料...")

# 讀取從第3列開始的數據 (index 2)
for row in rows[2:]:
    if len(row) < 5:
        continue
        
    date_str = row[1].strip()
    fb_followers = row[2].strip()
    ig_followers = row[4].strip()
    
    if not date_str:
        continue
        
    try:
        # 將 '2026/02/21' 解析為 datetime
        dt_obj = datetime.strptime(date_str, "%Y/%m/%d")
    except ValueError:
        continue # 日期格式不正確或為空

    # 處理 FB
    if fb_followers.isdigit():
        val = int(fb_followers)
        # 檢查該天是否已有紀錄
        existing = db.query(Record).filter(
            Record.target_id == target_fb_id,
            Record.scraped_at >= dt_obj.replace(hour=0, minute=0, second=0),
            Record.scraped_at <= dt_obj.replace(hour=23, minute=59, second=59)
        ).first()
        
        if not existing:
            db.add(Record(target_id=target_fb_id, followers=val, scraped_at=dt_obj))
            added_count += 1
        else:
            skip_count += 1

    # 處理 IG
    if ig_followers.isdigit():
        val = int(ig_followers)
        # 檢查該天是否已有紀錄
        existing = db.query(Record).filter(
            Record.target_id == target_ig_id,
            Record.scraped_at >= dt_obj.replace(hour=0, minute=0, second=0),
            Record.scraped_at <= dt_obj.replace(hour=23, minute=59, second=59)
        ).first()
        
        if not existing:
            db.add(Record(target_id=target_ig_id, followers=val, scraped_at=dt_obj))
            added_count += 1
        else:
            skip_count += 1

db.commit()
db.close()

print(f"✅ 匯入完成！成功新增了 {added_count} 筆紀錄 (跳過 {skip_count} 筆重複紀錄)。")
