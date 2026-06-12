import urllib.request
import json
import time

req = urllib.request.Request('http://127.0.0.1:8000/api/targets')
targets = json.loads(urllib.request.urlopen(req).read().decode())

for t in targets:
    url = f"http://127.0.0.1:8000/api/targets/{t['id']}/scrape"
    try:
        req = urllib.request.Request(url, method='POST')
        urllib.request.urlopen(req)
        print(f"Triggered target {t['id']} ({t['name']})")
        time.sleep(0.5)
    except Exception as e:
        print(f"Failed to trigger {t['id']}: {e}")

print('All triggered')
