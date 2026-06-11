import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")

supabase: Client = create_client(url, key)

# 提供一些 mock functions 或把不要用到的東西清掉，
# 不過因為我們會大幅重構 main.py，這裡就只要 export supabase 即可。
