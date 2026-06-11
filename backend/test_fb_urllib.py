import urllib.request
import re

url = 'https://www.facebook.com/TMD88888'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
})
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read().decode('utf-8')
        print('HTML LENGTH:', len(html))
        with open('fb_response.html', 'w', encoding='utf-8') as f:
            f.write(html)
except Exception as e:
    print(e)

