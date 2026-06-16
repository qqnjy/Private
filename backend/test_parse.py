import httpx, asyncio, re
async def run():
    url = 'http://www.atmovies.com.tw/movie/next/0/'
    html = (await httpx.AsyncClient(follow_redirects=True).get(url)).text
    sections = html.split('<h2 class="major">')
    events = []
    for sec in sections[1:]:
        date_match = re.search(r'<span>(.*?)</span>', sec)
        if date_match:
            date_str = date_match.group(1).replace('/', '-').strip()
            names = re.findall(r'<div class="filmtitle"><a[^>]*>(.*?)</a></div>', sec)
            for name in names:
                events.append({'name': name.strip(), 'date': date_str})
    print(events[:2])
asyncio.run(run())
