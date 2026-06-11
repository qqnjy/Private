import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_ANON_KEY'))

def main():
    t_res = supabase.table('targets').select('*').execute()
    targets = t_res.data

    for t in targets:
        tid = t['id']
        name = t['name']
        
        # 取得所有紀錄，照時間由新到舊排序
        r_res = supabase.table('records').select('*').eq('target_id', tid).order('scraped_at', desc=True).execute()
        records = r_res.data
        
        if not records:
            continue
            
        # 找出現有最新的追蹤數（取第一筆，或最大的，這裡取最新的一筆作為基準）
        latest_record = records[0]
        latest_total = latest_record['followers']
        
        # 如果最新追蹤數太小，可能連基準都沒有，跳過
        if latest_total < 100:
            continue
            
        # 檢查舊紀錄是否是增量（看過去的紀錄最大值是否極小於最新總數）
        older_records = records[1:]
        if not older_records:
            continue
            
        max_older = max([r['followers'] for r in older_records])
        
        # 判斷是否為增量：如果過去最大值小於最新值的 10%，判定為增量
        if max_older < latest_total * 0.1:
            print(f"[{name}] 判定為增量紀錄！開始倒推... (最新總數: {latest_total})")
            
            # 從最新的一筆往前推
            current_total = latest_total
            updates = []
            
            # 第一筆(最新的)保留，從第二筆開始算是前一天的增量
            # 假設 records 是 [R_today, R_yesterday, R_day_before...]
            # R_yesterday 的修正值 = current_total
            # current_total = current_total - R_yesterday.followers (原本的增量)
            for r in older_records:
                increment = r['followers']
                
                # 更新這筆紀錄的 followers 為目前的總數
                updates.append({
                    "id": r['id'],
                    "target_id": r['target_id'],
                    "followers": current_total,
                    "scraped_at": r['scraped_at']
                })
                
                # 扣掉這天的增量，變成上一天的總數
                current_total = current_total - increment
                
            # 批次更新回 Supabase
            if updates:
                # Upsert is based on primary key 'id'
                # batch updates
                batch_size = 500
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i+batch_size]
                    supabase.table("records").upsert(batch).execute()
                print(f"  -> 已修正 {len(updates)} 筆歷史紀錄。")
        else:
            print(f"[{name}] 判定為正常總數紀錄，略過。")

if __name__ == "__main__":
    main()
