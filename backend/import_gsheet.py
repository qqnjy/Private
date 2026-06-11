import urllib.request
import csv
import io

url = 'https://docs.google.com/spreadsheets/d/1636fAV2ug0XkSuMKiR2jHh6CVNso9vZlYNo0G2bwajM/export?format=csv&gid=929078381'
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    content = res.read().decode('utf-8')

reader = csv.reader(io.StringIO(content))
rows = list(reader)[:5]

for i, row in enumerate(rows):
    print(f"Row {i}: {row}")
