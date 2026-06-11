import asyncio
from playwright.async_api import async_playwright
import re

async def parse_followers(platform: str, url: str) -> int:
    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-TW"
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000) # 等待一些 JS 渲染
            
            followers_count = -1
            
            if platform in ['ig', 'threads']:
                # IG 和 Threads 通常可以從 meta tag 直接拿到描述
                meta_desc = await page.evaluate('() => document.querySelector("meta[property=\'og:description\']")?.content || document.querySelector("meta[name=\'description\']")?.content || ""')
                # 尋找 "1.2M Followers" 或 "120萬位粉絲"
                match = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(?:[Ff]ollowers|位粉絲)', meta_desc)
                if match:
                    followers_count = parse_number_str(match.group(1))
                    
            elif platform == 'fb':
                # 使用 FB Graph API
                fb_token = "EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD"
                
                # 從網址解析 username 或是 page_id
                # 支援: https://www.facebook.com/TMD88888 或是 https://www.facebook.com/profile.php?id=123456
                page_id_or_name = None
                if "profile.php?id=" in url:
                    match = re.search(r'id=(\d+)', url)
                    if match:
                        page_id_or_name = match.group(1)
                else:
                    # 去掉末端的斜線，並取得最後一個片段
                    clean_url = url.strip('/').split('?')[0]
                    page_id_or_name = clean_url.split('/')[-1]

                if page_id_or_name:
                    import urllib.request
                    import json
                    api_url = f"https://graph.facebook.com/v19.0/{page_id_or_name}?fields=followers_count&access_token={fb_token}"
                    req = urllib.request.Request(api_url)
                    try:
                        with urllib.request.urlopen(req) as response:
                            data = json.loads(response.read().decode('utf-8'))
                            followers_count = data.get('followers_count', -1)
                    except Exception as e:
                        print(f"Graph API Error: {e}")
                else:
                    print("無法從網址解析出 FB 粉絲團 ID 或 Username")

            elif platform == 'yt':
                # YT 尋找訂閱者文字
                text = await page.inner_text("body")
                match = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(位)?訂閱者', text)
                if not match:
                    match = re.search(r'([\d\.,]+[KMBkmb]?)\s*subscribers', text, re.IGNORECASE)
                if match:
                    followers_count = parse_number_str(match.group(1))
                    
            return followers_count
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return -1
        finally:
            await browser.close()

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
