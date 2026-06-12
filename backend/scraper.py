import asyncio
from playwright.async_api import async_playwright
import re

async def parse_followers(platform: str, url: str) -> int:
        try:
            followers_count = -1
            
            # API Token
            api_token = "EAAS4y3XjCTUBRiczcPVb3OcOTZCdQ3V1dZBZAyMU7cKyetezPl0W4Pb1WWT7S8uC9dC5k8anqv2DZAGh3cPPVZBwtNYgOJ1DtX5jeCFN5AsZAS4zuXGw3HUvG0Q1BcTbKUWiZAOtvyjz7p2fTuVmTyP7AJexYqhHE9mQZBJcmgm4mBgYrjSRXzBWXmkHgSOzzmWkGgZDZD"
            base_ig_id = "17841406145440438" # mjstar_371 (做為 business_discovery 查詢的跳板)

            if platform == 'ig':
                # 從網址取出 IG 帳號 (例如 https://www.instagram.com/mjstar_371/)
                username = url.strip('/').split('/')[-1].split('?')[0]
                if username:
                    import urllib.request
                    import json
                    api_url = f"https://graph.facebook.com/v19.0/{base_ig_id}?fields=business_discovery.username({username}){{followers_count}}&access_token={api_token}"
                    req = urllib.request.Request(api_url)
                    try:
                        with urllib.request.urlopen(req) as response:
                            data = json.loads(response.read().decode('utf-8'))
                            followers_count = data.get('business_discovery', {}).get('followers_count', -1)
                    except Exception as e:
                        print(f"IG Graph API Error: {e}")
                else:
                    print("無法從網址解析出 IG Username")
            
            elif platform == 'fb':
                # 從網址解析 username 或是 page_id
                page_id_or_name = None
                if "profile.php?id=" in url:
                    match = re.search(r'id=(\d+)', url)
                    if match:
                        page_id_or_name = match.group(1)
                else:
                    page_id_or_name = url.strip('/').split('?')[0].split('/')[-1]

                if page_id_or_name:
                    import urllib.request
                    import json
                    api_url = f"https://graph.facebook.com/v19.0/{page_id_or_name}?fields=followers_count&access_token={api_token}"
                    req = urllib.request.Request(api_url)
                    try:
                        with urllib.request.urlopen(req) as response:
                            data = json.loads(response.read().decode('utf-8'))
                            followers_count = data.get('followers_count', -1)
                    except Exception as e:
                        print(f"FB Graph API Error: {e}")
                else:
                    print("無法從網址解析出 FB 粉絲團 ID 或 Username")

            elif platform in ['threads', 'yt']:
                if platform == 'threads':
                    import urllib.request
                    url = url.replace("threads.com", "threads.net")
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    try:
                        with urllib.request.urlopen(req, timeout=10) as response:
                            html = response.read().decode('utf-8')
                            match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
                            if match:
                                desc = match.group(1)
                                print(f"DEBUG: Threads desc match: {desc}")
                                fm = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(?:[Ff]ollowers|位粉絲)', desc)
                                if fm:
                                    print(f"DEBUG: Threads followers match: {fm.group(1)}")
                                    followers_count = parse_number_str(fm.group(1))
                                else:
                                    print("DEBUG: NO FOLLOWERS MATCH")
                            else:
                                print("DEBUG: NO META MATCH")
                    except Exception as e:
                        print(f"Threads scrape error: {e}")
                else:
                    async with async_playwright() as p:
                        # 啟動瀏覽器
                        browser = await p.chromium.launch(headless=True)
                        context = await browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            locale="zh-TW"
                        )
                        page = await context.new_page()
                        
                        try:
                            if platform == 'yt':
                                # YT 用 Playwright 抓
                                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                                await page.wait_for_timeout(3000)
                                text = await page.inner_text("body")
                                match = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(位)?訂閱者', text)
                                if not match:
                                    match = re.search(r'([\d\.,]+[KMBkmb]?)\s*subscribers', text, re.IGNORECASE)
                                if match:
                                    followers_count = parse_number_str(match.group(1))
                        finally:
                            await browser.close()
                    
            return followers_count
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return -1

def parse_number_str(num_str: str) -> int:
    num_str = num_str.upper().replace(',', '')
    multiplier = 1
    if 'K' in num_str:
        multiplier = 1000
        num_str = num_str.replace('K', '')
    elif 'M' in num_str:
        multiplier = 1000000
        num_str = num_str.replace('M', '')
    elif 'B' in num_str:
        multiplier = 1000000000
        num_str = num_str.replace('B', '')
    elif '萬' in num_str:
        multiplier = 10000
        num_str = num_str.replace('萬', '')
        
    try:
        return int(float(num_str) * multiplier)
    except:
        return 0
