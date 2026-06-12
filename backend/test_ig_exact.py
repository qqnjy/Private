import asyncio, re
from playwright.async_api import async_playwright

async def t():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('https://www.instagram.com/gametower_ig/')
        html = await page.content()
        match = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html) or re.search(r'follower_count(?:":\s*|\s*:\s*)(\d+)', html)
        if match:
            print('Exact followers:', match.group(1))
        else:
            print('No exact match found in HTML.')
            meta = await page.evaluate('() => document.querySelector("meta[property=\'og:description\']")?.content')
            print('Meta description:', meta)
        await browser.close()

asyncio.run(t())
