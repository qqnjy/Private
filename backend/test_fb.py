import asyncio
from playwright.async_api import async_playwright
import re

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            locale="zh-TW"
        )
        page = await context.new_page()
        await page.goto("https://www.facebook.com/TMD88888", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        text = await page.inner_text("body")
        print("BODY PREVIEW:", repr(text[:1000]))
        
        match1 = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(位)?追蹤者', text)
        match2 = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(個)?讚', text)
        print("MATCH 追蹤者:", match1)
        print("MATCH 個讚:", match2)

        meta_desc = await page.evaluate('() => document.querySelector("meta[property=\'og:description\']")?.content || document.querySelector("meta[name=\'description\']")?.content || ""')
        print("META DESCRIPTION:", meta_desc)
        
        await page.screenshot(path='fb_test2.png')

        await browser.close()

if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run())
