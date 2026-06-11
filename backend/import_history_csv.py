import os
import pandas as pd
import sqlite3
from datetime import datetime

# Map filename keywords to target IDs
TARGET_MAP = {
    "大滿貫粉絲團追蹤人數": 4,
    "明星3缺1IG追蹤人數": 5,
    "明星3缺1粉絲團追蹤人數": 2,
    "滿貫大亨IG追蹤數": 6,
    "滿貫大亨粉絲團追蹤人數": 1,
    "玩星派對IG追蹤人數": 12,
    "玩星派對粉絲團追蹤人數": 11,
    "競技麻將2IG追蹤人數": 7,
    "競技麻將2粉絲團追蹤人數": 3,
    "金好運IG追蹤人數": 10,
    "金好運粉絲團追蹤人數": 9
}

CSV_DIR = r"C:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\粉絲團數據追蹤\過往資料"
DB_PATH = r"C:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\粉絲團數據追蹤\backend\data.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_inserted = 0
    
    for filename in os.listdir(CSV_DIR):
        if not filename.endswith(".csv"):
            continue
            
        filepath = os.path.join(CSV_DIR, filename)
        
        target_id = None
        for key, tid in TARGET_MAP.items():
            if key in filename:
                target_id = tid
                break
                
        if target_id is None:
            print(f"Unknown target for file: {filename}")
            continue
            
        print(f"Processing {filename} for target {target_id}...")
        try:
            # Read CSV
            df = pd.read_csv(filepath, encoding='utf-16', skiprows=2, header=None, names=['Date', 'Followers'])
            
            # Clean data
            df = df.dropna()
            
            # Insert into database
            inserted = 0
            for index, row in df.iterrows():
                date_str = str(row['Date'])
                try:
                    followers = int(row['Followers'])
                except ValueError:
                    continue
                    
                # Format: 2025-01-01T00:00:00
                if "T" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
                else:
                    # try fallback
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        
                # check if exist
                cursor.execute("""
                    SELECT id FROM records 
                    WHERE target_id = ? 
                    AND date(scraped_at) = date(?)
                """, (target_id, dt))
                
                if cursor.fetchone() is None:
                    cursor.execute("""
                        INSERT INTO records (target_id, followers, scraped_at) 
                        VALUES (?, ?, ?)
                    """, (target_id, followers, dt))
                    inserted += 1
            
            conn.commit()
            total_inserted += inserted
            print(f"Inserted {inserted} records for {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    conn.close()
    print(f"Finished! Total inserted: {total_inserted}")

if __name__ == '__main__':
    main()
