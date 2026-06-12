import urllib.request, json
import urllib.parse

token = "EAAGgeP0TIvEBRlsQljzigBAQRlp81ZAAv9zjyv3zpTp587WS69EsVMkuoAcAFu5uZA666krAkt5RwnnOasaDuaXUJU5JLSNKm6ocbU3NHQbqRJZA4wYLZAIlfCHnSsanKQdTu8ex0eKMVLaXowIdlcWXfrVRj372Ms0QtZCQ3BE6CByYLk1NYQXiXRptQLwTKrNBsu1Lg0HeQVdQQhCa3qyq2PDsRQ6zvGNThqrfH2W2t0QQGnf0IB9apXWZBAgsIMFp0RBY6Ag6XHPDidzn0ZD"

# Using a known IG Business ID to query the username
ig_account_id = "17841406145440438"
username = "mjstar_371"

url = f"https://graph.facebook.com/v19.0/{ig_account_id}?fields=business_discovery.username({username}){{followers_count}}&access_token={token}"

try:
    req = urllib.request.Request(url)
    res = urllib.request.urlopen(req)
    print(json.loads(res.read().decode('utf-8')))
except Exception as e:
    print(e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
