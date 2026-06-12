import asyncio
from playwright.async_api import async_playwright

async def get_ig_meta(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-TW"
        )
        page = await context.new_page()
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        meta_desc = await page.evaluate('() => document.querySelector("meta[property=\'og:description\']")?.content || document.querySelector("meta[name=\'description\']")?.content || ""')
        print(f"Meta Description: {meta_desc}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_ig_meta('https://www.instagram.com/mjstar_371'))
