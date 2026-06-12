import urllib.request
from bs4 import BeautifulSoup
import json
import re

url = 'https://academy.blueeyes.tw/LearningHub/knowledge_xiaobian_calendar.php'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        
        calendar = []
        # Let's find all panels. Usually month sections have class="panel" or are grouped.
        # Looking at typical blueeyes pages, they use <div class="col-md-3"> for each month.
        months = soup.find_all('div', class_='col-md-3')
        if not months:
            months = soup.find_all('div', class_='col-sm-3')
        if not months:
            # Maybe they just use standard h3 and ul
            pass
            
        # Let's try parsing headers
        h3s = soup.find_all('h3')
        for h3 in h3s:
            month_name = h3.text.strip()
            # The dates are usually in the next sibling or parent
            # Let's get the text of the parent
            parent_text = h3.parent.get_text(separator='\n').split('\n')
            
            events = []
            for line in parent_text:
                line = line.strip()
                if line and re.match(r'^\d{1,2}/\d{1,2}', line):
                    events.append(line)
            
            if events:
                calendar.append({
                    "month": month_name,
                    "events": events
                })

        with open('calendar.json', 'w', encoding='utf-8') as f:
            json.dump(calendar, f, ensure_ascii=False, indent=2)

except Exception as e:
    print(f"Error: {e}")
