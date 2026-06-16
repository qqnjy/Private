import httpx, asyncio, re
async def run():
    html = (await httpx.AsyncClient(follow_redirects=True).get('http://www.atmovies.com.tw/movie/next/0/')).text
    names = re.findall(r'<div class="filmTitle"><a[^>]*>(.*?)</a></div>', html)
    times = re.findall(r'<div class="runtime">上映日期：(.*?)</div>', html)
    with open('test_movies_out.txt', 'w', encoding='utf-8') as f:
        f.write(str(names[:5]) + '\n')
        f.write(str(times[:5]) + '\n')
asyncio.run(run())
