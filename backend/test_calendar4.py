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
        current_month = None
        current_events = []
        
        # All relevant content seems to be in the main container. Let's iterate over all h2, h3 and date elements.
        # Actually, let's just find all elements and process in order
        for tag in soup.find_all(['h2', 'h3', 'p', 'ul', 'li']):
            text = tag.get_text(separator=' ').strip()
            if not text: continue
            
            if tag.name == 'h2':
                if '月' in text and ('(' in text or ')' in text or '一月' in text or '二月' in text):
                    # Save previous month
                    if current_month:
                        calendar.append({
                            "month": current_month,
                            "events": current_events
                        })
                    current_month = text
                    current_events = []
            elif tag.name == 'h3' and current_month:
                # Event name
                event_name = text
                # Try to find the date, which might be in the next sibling <p> or <ul>
                # Let's just look ahead or use parent text
                parent_text = tag.parent.get_text(separator='\n').split('\n')
                date_str = ""
                for line in parent_text:
                    line = line.strip()
                    if re.match(r'^\d{1,2}/\d{1,2}', line):
                        date_str = line
                        break
                
                if date_str and event_name:
                    # check if not already added to avoid duplicates from parent reading
                    exists = False
                    for e in current_events:
                        if e['name'] == event_name and e['date'] == date_str:
                            exists = True
                            break
                    if not exists:
                        current_events.append({
                            "date": date_str,
                            "name": event_name
                        })

        if current_month and current_events:
            calendar.append({
                "month": current_month,
                "events": current_events
            })

        with open('calendar.json', 'w', encoding='utf-8') as f:
            json.dump(calendar, f, ensure_ascii=False, indent=2)

except Exception as e:
    print(f"Error: {e}")
