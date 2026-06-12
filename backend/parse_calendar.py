import urllib.request
from bs4 import BeautifulSoup
import json
import re

url = 'https://academy.blueeyes.tw/LearningHub/knowledge_xiaobian_calendar.php'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        # The page seems to have charset=utf-8, let's decode it
        html = response.read().decode('utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        
        calendar_data = []
        
        # The months are probably in some div or h2
        # Let's find all rows with class 'headline' or 'panel' or something
        # Wait, if we just find all elements, we can look for "一月", "二月", etc.
        # Let's dump the text of the body to see how it looks
        
        text = soup.get_text(separator='\n')
        with open('calendar_text.txt', 'w', encoding='utf-8') as f:
            f.write(text)
            
        # We can also try to find the specific structure.
        # Blueeyes usually uses Bootstrap. So there might be 'row', 'col-md-x'
        panels = soup.find_all('div', class_='col-md-3')
        for p in panels:
            title = p.find(['h2', 'h3', 'h4'])
            if title:
                calendar_data.append(title.text.strip())
                
        with open('calendar_panels.json', 'w', encoding='utf-8') as f:
            json.dump(calendar_data, f, ensure_ascii=False, indent=2)

except Exception as e:
    print(f"Error: {e}")
