import httpx
url = "http://www.atmovies.com.tw/movie/next/0/"
r = httpx.get(url, follow_redirects=True)
with open("backend/test_html.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Saved html")
