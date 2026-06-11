import urllib.request
import json

token = 'EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD'

try:
    url = f'https://graph.facebook.com/v19.0/TMD88888?fields=followers_count&access_token={token}'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        print(json.loads(res.read().decode('utf-8')))
except Exception as e:
    print(e)
