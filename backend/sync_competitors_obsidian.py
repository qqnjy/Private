import os
import re
from datetime import datetime
from models import supabase

OBSIDIAN_VAULT_PATH = r"F:\QQN\QQN\競品貼文庫"

def clean_filename(text):
    # Remove invalid characters for Windows filenames
    text = re.sub(r'[<>:"/\\|?*\n\r\t]', '', text)
    # Truncate to 20 characters
    return text[:20].strip()

def sync_to_obsidian():
    os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)
    
    print("Fetching competitor posts from Supabase...")
    res = supabase.table("competitor_posts").select("*").execute()
    posts = res.data
    
    if not posts:
        print("No posts found.")
        return 0

    count = 0
    for post in posts:
        # Generate filename: Date_Brand_ShortContent.md
        date_str = post.get("post_date", "")[:10]  # Just YYYY-MM-DD
        brand = post.get("brand", "Unknown")
        content = post.get("content", "")
        
        # Clean up the content for filename
        short_content = clean_filename(content)
        if not short_content:
            short_content = "無內容"
            
        filename = f"{date_str}_{brand}_{short_content}.md"
        file_path = os.path.join(OBSIDIAN_VAULT_PATH, filename)
        
        # Prepare YAML Frontmatter
        # We need to escape newlines in content, but content goes in the body so it's fine.
        tags = post.get("tags", [])
        if not isinstance(tags, list):
            tags = []
            
        tags_yaml = "\n".join([f"  - {tag}" for tag in tags])
        if not tags_yaml:
            tags_yaml = "  []"
            
        yaml_frontmatter = f"""---
brand: {brand}
post_date: {date_str}
likes: {post.get('likes', 0)}
comments: {post.get('comments', 0)}
shares: {post.get('shares', 0)}
engagement: {post.get('engagement', 0)}
platform: {post.get('platform', '')}
url: {post.get('url', '')}
tags:
{tags_yaml if tags else '  []'}
---

"""
        
        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(yaml_frontmatter)
            f.write(content)
            
        count += 1

    print(f"Successfully synced {count} posts to {OBSIDIAN_VAULT_PATH}")
    return count

if __name__ == "__main__":
    sync_to_obsidian()
