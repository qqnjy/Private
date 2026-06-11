import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
try:
    r = requests.get('https://www.facebook.com/TMD88888', headers=headers, timeout=10)
    print('STATUS:', r.status_code)

    match = re.search(r'([\d\.,]+[KMBkmb萬]?)\s*(位)?追蹤者', r.text)
    if not match:
        match = re.search(r'([\d\.,]+[KMBkmb]?)\s*followers', r.text, re.IGNORECASE)
    print('MATCH BODY:', match)

    match_meta = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', r.text)
    print('MATCH META:', match_meta.group(1) if match_meta else None)
except Exception as e:
    print(e)
