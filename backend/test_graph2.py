import urllib.request
import urllib.error
url = 'https://graph.facebook.com/v19.0/TMD88888?fields=followers_count&access_token=EAAGgeP0TIvEBRmkOKvRKCk60UY8ruVSHu5TT8QaWanDOPhdYP8sq98symGIS8HK5rZBc0ZCaGpNNQ8ZAaTjJXBBTdhZCmJkZAZAFS6ureHzZCf8y8KDyIiM6iwt1f2T7FR8VF7vHvQcdgNeqGNTwLRft71kEz9lRMbbbzBwWkmTc92gZCg0sGSD8f3Jux5uECwZDZD'
try:
    print(urllib.request.urlopen(url).read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode())
