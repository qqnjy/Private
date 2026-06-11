import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_ANON_KEY'))

def main():
    t_res = supabase.table('targets').select('*').execute()
    targets = t_res.data

    for t in targets:
        tid = t['id']
        name = t['name']
        
        r_res = supabase.table('records').select('*').eq('target_id', tid).order('scraped_at', desc=True).execute()
        records = r_res.data
        
        if not records:
            continue
            
        # 找出現有最新的追蹤數
        latest_total = max([r['followers'] for r in records[:5]]) # Take max of recent 5 to avoid a bad latest
        
        if latest_total < 100:
            continue
            
        print(f"[{name}] 檢查中... (最新指標數: {latest_total})")
        
        current_total = records[0]['followers']
        if current_total < latest_total * 0.1:
            current_total = latest_total
            
        updates = []
        
        for r in records:
            val = r['followers']
            
            # 判斷這筆是「總數」還是「增量」
            if val > latest_total * 0.1:
                # 這是總數，更新 current_total 基準
                current_total = val
            else:
                # 這是增量，需要更新這筆紀錄為 current_total，並把 current_total 往前扣
                updates.append({
                    "id": r['id'],
                    "target_id": r['target_id'],
                    "followers": current_total,
                    "scraped_at": r['scraped_at']
                })
                current_total -= val
                
        if updates:
            batch_size = 500
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i+batch_size]
                supabase.table("records").upsert(batch).execute()
            print(f"  -> 已修正 {len(updates)} 筆混雜的增量紀錄！")
        else:
            print(f"  -> 無需修正。")

if __name__ == "__main__":
    main()
