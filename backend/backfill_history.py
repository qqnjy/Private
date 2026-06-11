import urllib.request
import json
import re
from datetime import datetime
from models import supabase

FB_ACCOUNTS = {
    "107262232363722": "EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD",
    "323273157717210": "EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD",
    "285546094839900": "EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD",
    "1784471515125001": "EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD",
    "306343012746356": "EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD"
}

GENERAL_TOKEN = list(FB_ACCOUNTS.values())[0]

def get_page_id(page_id_or_name: str) -> str:
    url = f"https://graph.facebook.com/v19.0/{page_id_or_name}?fields=id&access_token={GENERAL_TOKEN}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            return data.get('id', page_id_or_name)
    except Exception as e:
        print(f"無法解析 Page ID {page_id_or_name}: {e}")
        return page_id_or_name

def backfill():
    res = supabase.table("targets").select("*").eq("platform", "fb").execute()
    targets = res.data
    
    for t in targets:
        print(f"\n準備補齊: {t['name']} (URL: {t['url']})")
        page_id_or_name = None
        if "profile.php?id=" in t['url']:
            match = re.search(r'id=(\d+)', t['url'])
            if match:
                page_id_or_name = match.group(1)
        else:
            clean_url = t['url'].strip('/').split('?')[0]
            page_id_or_name = clean_url.split('/')[-1]
            
        if not page_id_or_name:
            print("無效的 URL 格式")
            continue
            
        real_page_id = get_page_id(page_id_or_name)
        print(f"解析出真實 Page ID: {real_page_id}")
        
        token = FB_ACCOUNTS.get(real_page_id)
        if not token:
            print(f"找不到 {t['name']} 的管理員 Token！(歷史資料 Insights 需要管理員權限)")
            continue
            
        import datetime as dt
        until = int(dt.datetime.now().timestamp())
        since = int((dt.datetime.now() - dt.timedelta(days=90)).timestamp())
        
        api_url = f"https://graph.facebook.com/v19.0/{real_page_id}/insights/page_fans?period=day&since={since}&until={until}&access_token={token}"
        
        try:
            req = urllib.request.Request(api_url)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                if 'data' in data and len(data['data']) > 0:
                    history_values = data['data'][0]['values']
                    
                    added_count = 0
                    for item in history_values:
                        val = item['value']
                        end_time = item['end_time']
                        
                        dt_obj = dt.datetime.strptime(end_time[:19], "%Y-%m-%dT%H:%M:%S")
                        
                        start_of_day = dt_obj.replace(hour=0, minute=0, second=0).isoformat()
                        end_of_day = dt_obj.replace(hour=23, minute=59, second=59).isoformat()
                        
                        existing = supabase.table("records").select("id").eq("target_id", t['id']).gte("scraped_at", start_of_day).lte("scraped_at", end_of_day).execute()
                        
                        if not existing.data:
                            record_data = {"target_id": t['id'], "followers": val, "scraped_at": dt_obj.isoformat()}
                            supabase.table("records").insert(record_data).execute()
                            added_count += 1
                            
                    print(f"✅ {t['name']} 補齊完成！共新增了 {added_count} 筆歷史紀錄。")
                else:
                    print(f"❌ {t['name']} 沒有回傳任何 Insights 歷史資料。")
        except Exception as e:
            print(f"Graph API 發生錯誤: {e}")

if __name__ == "__main__":
    backfill()
