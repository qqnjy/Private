import urllib.request
from bs4 import BeautifulSoup
import json

url = 'https://academy.blueeyes.tw/LearningHub/knowledge_xiaobian_calendar.php'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to find tables or lists that look like calendar data
        results = []
        # Usually it's in a table, or some specific div class
        tables = soup.find_all('table')
        if tables:
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    cols = [ele.text.strip() for ele in cols]
                    results.append(cols)
        else:
            # Maybe list items?
            lists = soup.find_all('li')
            for li in lists:
                results.append(li.text.strip())

        with open('calendar_debug.json', 'w', encoding='utf-8') as f:
            json.dump(results[:100], f, ensure_ascii=False, indent=2)
        print("Data parsed and saved to calendar_debug.json")
        print(f"Found {len(tables)} tables")
except Exception as e:
    print(f"Error: {e}")
