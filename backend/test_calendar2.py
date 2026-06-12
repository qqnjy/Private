import urllib.request
from bs4 import BeautifulSoup

url = 'https://academy.blueeyes.tw/LearningHub/knowledge_xiaobian_calendar.php'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        # the calendar is likely in divs with classes containing 'month' or 'day' or similar
        months = soup.find_all(class_='month')
        if not months:
            # Let's just find headers or something
            headers = soup.find_all(['h2', 'h3'])
            for h in headers[:10]:
                print(f"Header: {h.text.strip()}")
            
            # Print a snippet of the body to see what classes are used
            body_text = soup.body.decode_contents()
            with open('body.html', 'w', encoding='utf-8') as f:
                f.write(body_text[:10000])
            print("Saved body.html")

except Exception as e:
    print(f"Error: {e}")
