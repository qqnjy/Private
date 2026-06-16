import os
import re
from datetime import datetime
from models import supabase

OBSIDIAN_VAULT_PATH = r"F:\QQN\QQN\創作者成效庫"

def clean_filename(text):
    text = re.sub(r'[<>:"/\\|?*\n\r\t]', '', str(text))
    return text.strip()

def sync_to_obsidian():
    os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)
    
    print("Fetching creators data from Supabase...")
    res = supabase.table("creators").select("*").execute()
    creators = res.data
    
    if not creators:
        print("No creators found.")
        return 0

    count = 0
    for creator in creators:
        creator_name = clean_filename(creator.get("creatorName", "Unknown"))
        game_category = clean_filename(creator.get("gameCategory", "Unknown"))
        
        filename = f"{game_category}_{creator_name}.md"
        file_path = os.path.join(OBSIDIAN_VAULT_PATH, filename)
        
        # Prepare tags if any
        posts = creator.get("posts", [])
        total_views = sum([int(p.get("views") or 0) for p in posts])
        total_likes = sum([int(p.get("likes") or 0) for p in posts])
        
        yaml_frontmatter = f"""---
creatorName: {creator.get("creatorName", "")}
gameCategory: {creator.get("gameCategory", "")}
followers: {creator.get("followers", 0)}
rewardStatus: {creator.get("rewardStatus", "")}
profileLink: {creator.get("profileLink", "")}
region: {creator.get("region", "台灣")}
totalViews: {total_views}
totalLikes: {total_likes}
---

# {creator.get("creatorName", "")} ({creator.get("gameCategory", "")})

- **粉絲數**: {creator.get("followers", 0)}
- **狀態**: {creator.get("rewardStatus", "")}
- **連結**: {creator.get("profileLink", "")}
- **信箱**: {creator.get("email", "")}
- **Line**: {creator.get("line", "")}

## 貼文紀錄
"""
        
        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(yaml_frontmatter)
            for p in posts:
                post_date = str(p.get('postDate', ''))[:10]
                f.write(f"\n### {post_date} [{p.get('platform', '')}] {p.get('format', '')}\n")
                f.write(f"- **觀看**: {p.get('views', 0)} | **按讚**: {p.get('likes', 0)} | **留言**: {p.get('comments', 0)}\n")
                f.write(f"- **網址**: {p.get('url', '')}\n")
                if p.get('note'):
                    f.write(f"- **備註**: {p.get('note')}\n")
            
        count += 1

    print(f"Successfully synced {count} creators to {OBSIDIAN_VAULT_PATH}")
    return count

if __name__ == "__main__":
    sync_to_obsidian()
