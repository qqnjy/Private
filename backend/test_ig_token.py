import urllib.request
import json
import ssl

token = "EAAGgeP0TIvEBRlsQljzigBAQRlp81ZAAv9zjyv3zpTp587WS69EsVMkuoAcAFu5uZA666krAkt5RwnnOasaDuaXUJU5JLSNKm6ocbU3NHQbqRJZA4wYLZAIlfCHnSsanKQdTu8ex0eKMVLaXowIdlcWXfrVRj372Ms0QtZCQ3BE6CByYLk1NYQXiXRptQLwTKrNBsu1Lg0HeQVdQQhCa3qyq2PDsRQ6zvGNThqrfH2W2t0QQGnf0IB9apXWZBAgsIMFp0RBY6Ag6XHPDidzn0ZD"

# First, get all accounts to find linked IG accounts
url = f"https://graph.facebook.com/v19.0/me/accounts?fields=name,id,instagram_business_account&access_token={token}"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode())
        print("Pages access:")
        for page in data.get('data', []):
            print(f"- {page.get('name')} (ID: {page.get('id')})")
            ig_acct = page.get('instagram_business_account')
            if ig_acct:
                ig_id = ig_acct.get('id')
                print(f"  Linked IG ID: {ig_id}")
                
                # Fetch IG followers
                ig_url = f"https://graph.facebook.com/v19.0/{ig_id}?fields=username,followers_count&access_token={token}"
                try:
                    ig_req = urllib.request.Request(ig_url)
                    with urllib.request.urlopen(ig_req, context=ctx) as ig_response:
                        ig_data = json.loads(ig_response.read().decode())
                        print(f"  IG Account: {ig_data.get('username')}, Followers: {ig_data.get('followers_count')}")
                except urllib.error.HTTPError as e:
                    print(f"  Error fetching IG data: {e.read().decode()}")
            else:
                print("  No linked IG account.")
except urllib.error.HTTPError as e:
    print(f"Error: {e.read().decode()}")
