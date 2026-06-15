import urllib.request
import csv
import io
import json
import os
from models import supabase

url = 'https://docs.google.com/spreadsheets/d/10E_qaLyqIudNeJmDRzj9JtoXaCwGyAMbbLzxUznP0Vs/export?format=csv'
req = urllib.request.Request(url)

try:
    with urllib.request.urlopen(req) as response:
        csv_content = response.read().decode('utf-8')
except Exception as e:
    print(f"Error fetching data: {e}")
    exit(1)

reader = csv.reader(io.StringIO(csv_content))
rows = list(reader)

# Brand name mapping
brand_map = {
    '808online': '包你發',
    'xinstarsonline': '星城',
    '08online': '老子有錢',
    'star.partygo': '玩星派對',
    'HSCasino': '豪神'
}

data = []
for row in rows:
    if len(row) < 9:
        continue
    
    # row[0]: content
    # row[1]: url
    # row[2]: date
    # row[3]: brand
    # row[4]: likes
    # row[5]: comments
    # row[6]: platform
    # row[7]: shares
    # row[8]: tags
    
    brand_raw = row[3].strip()
    brand_display = brand_map.get(brand_raw, brand_raw)
    
    def parse_int(val):
        try:
            return int(val.strip()) if val.strip() else 0
        except:
            return 0
    
    likes = parse_int(row[4])
    comments = parse_int(row[5])
    shares = parse_int(row[7])
    
    tags_raw = row[8].strip()
    tags = [t.strip() for t in tags_raw.split(',')] if tags_raw else []
    # Filter out empty tags
    tags = [t for t in tags if t]
    
    # Calculate total engagement
    engagement = likes + comments + shares
    
    item = {
        'content': row[0].strip(),
        'url': row[1].strip(),
        'post_date': row[2].strip(),
        'brand': brand_display,
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'platform': row[6].strip(),
        'tags': tags,
        'engagement': engagement
    }
    data.append(item)

# Sort data by date descending
data.sort(key=lambda x: x['post_date'], reverse=True)

# Write to Supabase
if data:
    print(f"Upserting {len(data)} competitor posts to Supabase...")
    batch_size = 500
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        # Insert/update based on url
        res = supabase.table("competitor_posts").upsert(batch, on_conflict="url").execute()
        print(f"Upserted batch {i} to {i+len(batch)}")

print(f"Successfully processed {len(data)} competitor posts.")
