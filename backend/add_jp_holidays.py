import json
import os

jp_holidays = {
    1: [{"date": "1/1", "name": "🇯🇵 元日"}, {"date": "1/12", "name": "🇯🇵 成人之日"}],
    2: [{"date": "2/11", "name": "🇯🇵 建國紀念之日"}, {"date": "2/23", "name": "🇯🇵 天皇誕生日"}],
    3: [{"date": "3/20", "name": "🇯🇵 春分之日"}],
    4: [{"date": "4/29", "name": "🇯🇵 昭和之日"}],
    5: [
        {"date": "5/3", "name": "🇯🇵 憲法紀念日"}, 
        {"date": "5/4", "name": "🇯🇵 綠之日"}, 
        {"date": "5/5", "name": "🇯🇵 兒童之日"}, 
        {"date": "5/6", "name": "🇯🇵 振替休日"}, 
        {"date": "4/29-5/6", "name": "🇯🇵 黃金週｜八天"}
    ],
    6: [],
    7: [{"date": "7/20", "name": "🇯🇵 海之日"}],
    8: [
        {"date": "8/11", "name": "🇯🇵 山之日"}, 
        {"date": "8/13-8/16", "name": "🇯🇵 盂蘭盆節｜四天"}
    ],
    9: [{"date": "9/21", "name": "🇯🇵 敬老之日"}, {"date": "9/23", "name": "🇯🇵 秋分之日"}],
    10: [{"date": "10/12", "name": "🇯🇵 體育之日"}],
    11: [{"date": "11/3", "name": "🇯🇵 文化之日"}, {"date": "11/23", "name": "🇯🇵 勤勞感謝之日"}],
    12: [{"date": "12/29-12/31", "name": "🇯🇵 新年歲末｜三天"}]
}

file_path = 'src/data/calendar2026.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for i, month_data in enumerate(data):
    month_idx = i + 1
    if month_idx in jp_holidays:
        month_data['events'].extend(jp_holidays[month_idx])

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Added Japanese holidays to calendar2026.json")
