import csv
from datetime import datetime
from sqlalchemy.orm import Session
from models import SessionLocal, Target, Record, init_db
import os

csv_path = '../過往資料/滿貫大亨IG追蹤數.csv'

# IG Target ID 6: 滿貫大亨_IG
target_id = 6

init_db()
db = SessionLocal()

# 從資料庫抓取目前最新（今天）的總人數
latest_record = db.query(Record).filter(Record.target_id == target_id).order_by(Record.scraped_at.desc()).first()
if not latest_record:
    print("找不到目前最新的粉絲數，無法回推！")
    exit(1)

current_total = latest_record.followers
print(f"目前最新 IG 總粉絲數: {current_total}")

# 讀取 CSV
with open(csv_path, 'r', encoding='utf-16') as f:
    reader = csv.reader(f)
    rows = list(reader)

# 資料是從頭開始（最舊到最新），我們先反轉它變成從新到舊
data_rows = []
for row in rows:
    if len(row) >= 2 and 'T' in row[0]:
        try:
            # e.g. "2025-01-01T00:00:00"
            dt_obj = datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S")
            added = int(row[1])
            data_rows.append((dt_obj, added))
        except ValueError:
            pass

# 依日期反向排序 (由新到舊)
data_rows.sort(key=lambda x: x[0], reverse=True)

added_count = 0
skip_count = 0

for dt_obj, added in data_rows:
    # 儲存這天的總數
    day_total = current_total
    
    # 計算上一天的總數
    current_total = current_total - added

    # 寫入資料庫
    existing = db.query(Record).filter(
        Record.target_id == target_id,
        Record.scraped_at >= dt_obj.replace(hour=0, minute=0, second=0),
        Record.scraped_at <= dt_obj.replace(hour=23, minute=59, second=59)
    ).first()
    
    if not existing:
        db.add(Record(target_id=target_id, followers=day_total, scraped_at=dt_obj))
        added_count += 1
    else:
        skip_count += 1

db.commit()
db.close()

print(f"✅ 回推匯入完成！新增了 {added_count} 筆歷史紀錄 (跳過 {skip_count} 筆)。")
