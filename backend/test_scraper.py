import asyncio
from scraper import parse_followers

async def main():
    print("Testing IG scraper...")
    count = await parse_followers("ig", "https://www.instagram.com/mjstar_371/")
    print(f"Result: {count}")

asyncio.run(main())
