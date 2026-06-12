import asyncio
from models import supabase
from scraper import parse_followers

async def test_ig():
    res = supabase.table('targets').select('*').eq('platform', 'ig').execute()
    targets = [x for x in res.data if '明星3缺1' in x['name'] or '明星三缺一' in x['name']]
    if not targets:
        print("Not found in db")
        return
        
    for t in targets:
        print(f"Target: {t['name']}, URL: {t['url']}")
        followers = await parse_followers('ig', t['url'])
        print(f"Scraped Followers: {followers}")

if __name__ == "__main__":
    asyncio.run(test_ig())
