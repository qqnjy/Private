import json

file_path = 'src/data/calendar2026.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for month_data in data:
    month_data['events'] = [ev for ev in month_data['events'] if not ('🇯🇵' in ev['name'] and '｜' in ev['name'])]

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Removed JP multi-day holidays")
