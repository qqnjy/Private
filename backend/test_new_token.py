import urllib.request
import json
import ssl

token = "EAAS4y3XjCTUBRiczcPVb3OcOTZCdQ3V1dZBZAyMU7cKyetezPl0W4Pb1WWT7S8uC9dC5k8anqv2DZAGh3cPPVZBwtNYgOJ1DtX5jeCFN5AsZAS4zuXGw3HUvG0Q1BcTbKUWiZAOtvyjz7p2fTuVmTyP7AJexYqhHE9mQZBJcmgm4mBgYrjSRXzBWXmkHgSOzzmWkGgZDZD"

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
            print(f"- {page.get('name')} (FB ID: {page.get('id')})")
            ig_acct = page.get('instagram_business_account')
            if ig_acct:
                ig_id = ig_acct.get('id')
                # Fetch IG followers
                ig_url = f"https://graph.facebook.com/v19.0/{ig_id}?fields=username,followers_count&access_token={token}"
                try:
                    ig_req = urllib.request.Request(ig_url)
                    with urllib.request.urlopen(ig_req, context=ctx) as ig_response:
                        ig_data = json.loads(ig_response.read().decode())
                        print(f"  Linked IG Account: {ig_data.get('username')}, Followers: {ig_data.get('followers_count')} (IG ID: {ig_id})")
                except Exception as e:
                    print(f"  Error fetching IG data: {e}")
            else:
                print("  No linked IG account.")
except urllib.error.HTTPError as e:
    print(f"Error: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
