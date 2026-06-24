from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from urllib.parse import quote
from scraper import parse_followers
from pydantic import BaseModel
import contextlib
import os
from datetime import datetime, timedelta
from models import supabase

OBSIDIAN_VAULT_PATH = r"F:\QQN\QQN"
OBSIDIAN_FILE_NAME = "粉絲團數據.md"

def update_obsidian_note(platform, name, followers):
    try:
        file_path = os.path.join(OBSIDIAN_VAULT_PATH, OBSIDIAN_FILE_NAME)
        today = datetime.now().strftime("%Y-%m-%d")
        log_entry = f"| {today} | {platform.upper()} | {name} | {followers:,} |\n"
        
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("# 粉絲團每日追蹤數據\n\n")
                f.write("| 日期 | 平台 | 粉絲團名稱 | 粉絲數 |\n")
                f.write("| --- | --- | --- | --- |\n")
                
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"寫入 Obsidian 失敗: {e}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TargetCreate(BaseModel):
    name: str
    url: str
    platform: str

scraping_status = {}

@app.get("/api/targets")
def get_targets():
    # Fetch targets
    targets_res = supabase.table("targets").select("*").execute()
    targets = targets_res.data
    
    # We can fetch latest record for each target. 
    # Supabase select with order and limit per group is hard, so we just fetch all recent records or fetch all and filter in python.
    records_res = supabase.table("records").select("*").order("scraped_at", desc=True).execute()
    
    # Build dictionary for latest records
    latest_records = {}
    for r in records_res.data:
        tid = r["target_id"]
        if tid not in latest_records:
            latest_records[tid] = r

    res = []
    for t in targets:
        latest = latest_records.get(t["id"])
        res.append({
            "id": t["id"],
            "name": t["name"],
            "platform": t["platform"],
            "url": t["url"],
            "latest_followers": latest["followers"] if latest else None,
            "updated_at": latest["scraped_at"] if latest else None,
            "status": scraping_status.get(t["id"], "idle")
        })
    return res

@app.post("/api/targets")
def add_target(target: TargetCreate):
    # Fix sequence out of sync issue by finding max id manually
    max_id_res = supabase.table("targets").select("id").order("id", desc=True).limit(1).execute()
    new_id = (max_id_res.data[0]["id"] + 1) if max_id_res.data else 1
    
    data = {"id": new_id, "name": target.name, "url": target.url, "platform": target.platform}
    supabase.table("targets").insert(data).execute()
    return {"status": "ok"}

@app.delete("/api/targets/{target_id}")
def delete_target(target_id: int):
    # Supabase on delete cascade is set up in schema, so deleting target deletes records
    supabase.table("targets").delete().eq("id", target_id).execute()
    if target_id in scraping_status:
        del scraping_status[target_id]
    return {"status": "ok"}

def scrape_task_sync(target_id: int, platform: str, url: str, name: str):
    import asyncio
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    scraping_status[target_id] = "scraping"
    try:
        followers = asyncio.run(parse_followers(platform, url))
        if followers >= 0:
            inserted = False
            retry_count = 0
            while not inserted and retry_count < 10:
                try:
                    max_id_res = supabase.table("records").select("id").order("id", desc=True).limit(1).execute()
                    new_id = (max_id_res.data[0]["id"] + 1) if max_id_res.data else 1
                    
                    record_data = {"id": new_id, "target_id": target_id, "followers": followers}
                    supabase.table("records").insert(record_data).execute()
                    inserted = True
                except Exception as ex:
                    if '23505' in str(ex):
                        retry_count += 1
                        import time
                        time.sleep(0.5)
                    else:
                        raise ex
            
            update_obsidian_note(platform, name, followers)
            scraping_status[target_id] = "idle"
        else:
            scraping_status[target_id] = "error"
    except Exception as e:
        print(f"Scrape error: {e}")
        scraping_status[target_id] = "error"

@app.post("/api/targets/{target_id}/scrape")
def force_scrape(target_id: int, background_tasks: BackgroundTasks):
    target_res = supabase.table("targets").select("*").eq("id", target_id).execute()
    if not target_res.data:
        raise HTTPException(status_code=404)
    
    target = target_res.data[0]
    scraping_status[target["id"]] = "scraping"
    background_tasks.add_task(scrape_task_sync, target["id"], target["platform"], target["url"], target["name"])
    return {"status": "scraping started in background"}
    
@app.get("/api/targets/{target_id}/history")
def get_history(target_id: int):
    res = supabase.table("records").select("*").eq("target_id", target_id).order("scraped_at").execute()
    return res.data

@app.get("/api/stats/summary")
def get_stats_summary(target_ids: str = None):
    query = supabase.table("targets").select("*")
    if target_ids:
        tids = [int(tid) for tid in target_ids.split(",") if tid.strip().isdigit()]
        if tids:
            query = query.in_("id", tids)
    
    targets_res = query.execute()
    targets = targets_res.data
    
    tids_to_fetch = [t["id"] for t in targets]
    
    records_res = supabase.table("records").select("*").in_("target_id", tids_to_fetch).order("scraped_at", desc=True).execute()
    
    latest_records = {}
    for r in records_res.data:
        tid = r["target_id"]
        if tid not in latest_records:
            latest_records[tid] = r

    total_followers = 0
    platform_stats = {}
    
    for t in targets:
        latest = latest_records.get(t["id"])
        if latest and latest["followers"] > 0:
            total_followers += latest["followers"]
            p = t["platform"]
            platform_stats[p] = platform_stats.get(p, 0) + latest["followers"]

    return {
        "total_followers": total_followers,
        "platform_stats": platform_stats
    }

@app.get("/api/stats/trend")
def get_stats_trend(days: int = 30, target_ids: str = None, start_date: str = None, end_date: str = None):
    query = supabase.table("records").select("*")
    
    if start_date:
        query = query.gte("scraped_at", f"{start_date}T00:00:00+00:00")
    else:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.gte("scraped_at", cutoff.isoformat())
        
    if end_date:
        query = query.lte("scraped_at", f"{end_date}T23:59:59+00:00")
        
    if target_ids:
        tids = [int(tid) for tid in target_ids.split(",") if tid.strip().isdigit()]
        if tids:
            query = query.in_("target_id", tids)
            
    records_res = query.order("scraped_at").execute()
    records = records_res.data
    
    targets_res = supabase.table("targets").select("id, platform").execute()
    target_platforms = {t["id"]: t["platform"] for t in targets_res.data}
    
    # Process into daily stats
    daily_data = {}
    for r in records:
        # Convert string to dt to get date
        dt = datetime.fromisoformat(r["scraped_at"].replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        if date_str not in daily_data:
            daily_data[date_str] = {}
        daily_data[date_str][r["target_id"]] = r["followers"]
        
    chart_data = []
    last_known = {}
    sorted_dates = sorted(list(daily_data.keys()))
    
    for d in sorted_dates:
        for tid, followers in daily_data[d].items():
            last_known[tid] = followers
            
        platforms_sum = {}
        for tid, followers in last_known.items():
            p = target_platforms.get(tid)
            if p:
                platforms_sum[p] = platforms_sum.get(p, 0) + followers
                
        daily_total = sum(last_known.values())
        entry = {
            "date": d,
            "total": daily_total
        }
        entry.update(platforms_sum)
        chart_data.append(entry)
        
    return chart_data

@app.get("/api/competitors")
def get_competitors():
    try:
        res = supabase.table("competitor_posts").select("*").order("post_date", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/competitors/fetch")
def fetch_competitors():
    import subprocess
    import sys
    try:
        script_path = os.path.join(os.path.dirname(__file__), "fetch_competitors.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            return {"status": "success", "message": "資料更新成功", "output": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=f"更新失敗: {result.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/obsidian/sync_competitors")
def api_sync_competitors_obsidian():
    import subprocess
    import sys
    try:
        script_path = os.path.join(os.path.dirname(__file__), "sync_competitors_obsidian.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            return {"status": "success", "message": "Obsidian 同步成功", "output": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=f"同步失敗: {result.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/obsidian/sync_creators")
def api_sync_creators_obsidian():
    import subprocess
    import sys
    try:
        script_path = os.path.join(os.path.dirname(__file__), "sync_creators_obsidian.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            return {"status": "success", "message": "創作者 Obsidian 同步成功", "output": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=f"同步失敗: {result.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/movies/yahoo")
async def get_yahoo_movies():
    import httpx
    import re
    # We use atmovies since Yahoo has anti-scraping
    url = "http://www.atmovies.com.tw/movie/next/0/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        html = response.text

    events = []
    # Split by the date header
    sections = html.split('<h2 class="major">')
    for sec in sections[1:]:
        date_match = re.search(r'<span>(.*?)</span>', sec)
        if date_match:
            # Format to YYYY-MM-DD
            date_str = date_match.group(1).replace('/', '-').strip()
            # Extract movie titles under this date
            names = re.findall(r'<div class="filmtitle"><a[^>]*>(.*?)</a></div>', sec)
            for name in names:
                events.append({
                    "name": f"🎬 {name.strip()}",
                    "date": date_str
                })
            
    return events

from pydantic import BaseModel
class ReportRequest(BaseModel):
    brand_name: str
    notes: str
    followers_growth_fb: int
    followers_growth_ig: int
    followers_growth_threads: int = 0

@app.get("/api/posts/week")
def api_posts_week(brand_name: str, start_date: str, end_date: str, refresh: bool = False):
    try:
        from fb_api import fetch_weekly_posts
        from posts_repo import get_cached_posts, save_posts

        if not refresh:
            cached = get_cached_posts(brand_name, start_date, end_date)
            if cached and (cached.get("fb") or cached.get("ig")):
                # Need matched_page hint too; reuse a lightweight lookup
                from fb_api import find_page_by_brand
                page = find_page_by_brand(brand_name)
                matched = None
                if page:
                    matched = {"page_id": page["page_id"], "name": page["name"], "ig_user_id": page.get("ig_user_id")}
                return {
                    "matched_page": matched,
                    "fb": cached["fb"],
                    "ig": cached["ig"],
                    "fetched_at": cached.get("fetched_at"),
                    "from_cache": True,
                }

        live = fetch_weekly_posts(brand_name, start_date, end_date)
        try:
            save_posts(brand_name, start_date, end_date, live.get("fb") or [], live.get("ig") or [])
        except Exception as save_err:
            print(f"posts cache save failed: {save_err}")
        live["from_cache"] = False
        return live
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brand/meta")
def api_brand_meta(brand_name: str):
    try:
        from fb_api import fetch_brand_meta
        return fetch_brand_meta(brand_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fb/pages")
def api_fb_pages():
    try:
        from fb_api import list_managed_pages
        # Don't leak page_token to the frontend
        pages = [{"page_id": p["page_id"], "name": p["name"], "ig_user_id": p.get("ig_user_id")} for p in list_managed_pages()]
        return pages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ReportRequestExt(ReportRequest):
    start_date: str | None = None
    end_date: str | None = None
    refresh: bool = False


@app.post("/api/generate-report")
def api_generate_report(req: ReportRequestExt):
    try:
        from reports_repo import get_cached_report, save_report

        # Cache hit short-circuits the LLM call (saves tokens)
        if req.start_date and req.end_date and not req.refresh:
            cached = get_cached_report(req.brand_name, req.start_date, req.end_date)
            if cached and cached.get("outline"):
                return {
                    "status": "success",
                    "report": cached["outline"],
                    "slides": cached.get("slides"),
                    "from_cache": True,
                    "generated_at": cached.get("generated_at"),
                }

        from ai_reporter import generate_weekly_report
        # Enrich notes with TOP posts if we can pull them
        notes = req.notes or ""
        if req.start_date and req.end_date:
            try:
                from fb_api import fetch_weekly_posts, top_posts_summary
                weekly = fetch_weekly_posts(req.brand_name, req.start_date, req.end_date)
                summary = top_posts_summary(weekly, top_n=3)
                if summary:
                    notes = (notes + "\n\n" if notes else "") + summary
            except Exception as fb_err:
                print(f"FB posts fetch failed: {fb_err}")

        result = generate_weekly_report(
            req.brand_name, notes,
            req.followers_growth_fb, req.followers_growth_ig, req.followers_growth_threads,
        )
        outline = result.get("outline", "")
        slides = result.get("slides")

        # Persist for next time (only if we actually got valid AI output)
        if req.start_date and req.end_date and outline and not result.get("error"):
            try:
                save_report(req.brand_name, req.start_date, req.end_date, outline, slides, req.notes)
            except Exception as save_err:
                print(f"reports cache save failed: {save_err}")

        return {
            "status": "success",
            "report": outline,
            "slides": slides,
            "from_cache": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PptRequest(BaseModel):
    brand_name: str
    week_range: str
    slides: dict | None = None


@app.post("/api/generate-ppt")
def api_generate_ppt(req: PptRequest):
    try:
        from ppt_generator import build_ppt
        data = build_ppt(req.brand_name, req.week_range, req.slides or {})
        filename = f"{req.brand_name}_週報_{req.week_range}.pptx"
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
