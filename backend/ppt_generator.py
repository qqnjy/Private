"""Build the weekly social-media report PPT using the IGS master template.

Layout usage (template `templates/igs_master.pptx`):
  [0] 標題投影片        — WHITE cover  → cover slide
  [1] 標題及內容        — RED bg       → DO NOT USE
  [2] 14_標題及內容     — WHITE, title + subtitle + 2 body + picture → all content slides
  [3] 2_標題及內容      — WHITE, title only → closing slide

Layout 2 placeholders:
  idx=0  TITLE     (x=0.66 y=0.54 w=4.07 h=0.48)
  idx=1  SUBTITLE  (x=0.66 y=1.20 w=4.07 h=0.79)
  idx=11 BODY      (x=0.66 y=2.08 w=4.07 h=1.51)
  idx=12 BODY      (x=0.66 y=3.68 w=4.07 h=1.51)
  idx=10 PICTURE   (x=5.27 y=0.70 w=4.37 h=4.29)
"""
import io
import os
import httpx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "igs_master.pptx")

LAYOUT_COVER = 0
LAYOUT_CONTENT = 2   # title + subtitle + 2 body + optional picture
LAYOUT_CLOSING = 3

# Placeholder indices for the content layout
PH_TITLE = 0
PH_SUBTITLE = 1
PH_BODY1 = 11
PH_BODY2 = 12
PH_PICTURE = 10

BRAND_ACCENT = RGBColor(0xE5, 0x01, 0x12)  # match the red used in the template logo
TEXT_DARK = RGBColor(0x2C, 0x3E, 0x50)
TEXT_MUTED = RGBColor(0x7F, 0x8C, 0x8D)


def _clear_existing_slides(prs):
    sld_id_lst = prs.slides._sldIdLst
    for sld in list(sld_id_lst):
        rId = sld.rId
        sld_id_lst.remove(sld)
        try:
            prs.part.drop_rel(rId)
        except Exception:
            pass


def _ph(slide, idx):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            return ph
    return None


def _remove_placeholder(slide, idx):
    ph = _ph(slide, idx)
    if ph is not None:
        sp = ph._element
        sp.getparent().remove(sp)


def _set_text(slide, idx, text):
    ph = _ph(slide, idx)
    if ph is not None:
        ph.text = text or ""
        return ph
    return None


def _fill_body(placeholder, paragraphs):
    if placeholder is None:
        return
    tf = placeholder.text_frame
    tf.clear()
    tf.word_wrap = True
    for i, item in enumerate(paragraphs):
        text = item.get("text", "")
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if "level" in item:
            p.level = item["level"]
        r = p.add_run()
        r.text = text
        if "size" in item:
            r.font.size = Pt(item["size"])
        if item.get("bold"):
            r.font.bold = True
        if "color" in item:
            r.font.color.rgb = item["color"]


def _download_image(url):
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=10.0, follow_redirects=True)
        r.raise_for_status()
        return io.BytesIO(r.content)
    except Exception:
        return None


# ---------- slide builders ----------

def _add_cover(prs, brand_name, week_range):
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_COVER])
    _set_text(slide, PH_TITLE, f"{brand_name} 社群週報")
    _set_text(slide, PH_SUBTITLE, week_range)


def _add_content_slide(prs, title: str, subtitle: str | None,
                       body1_paragraphs: list[dict] | None,
                       body2_paragraphs: list[dict] | None,
                       image_url: str | None = None):
    """Add a slide using Layout 2 (white, with optional picture).

    Unused placeholders are removed so they don't render as visible 'click to add' hints.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_CONTENT])
    _set_text(slide, PH_TITLE, title)

    if subtitle:
        _set_text(slide, PH_SUBTITLE, subtitle)
    else:
        _remove_placeholder(slide, PH_SUBTITLE)

    if body1_paragraphs:
        _fill_body(_ph(slide, PH_BODY1), body1_paragraphs)
    else:
        _remove_placeholder(slide, PH_BODY1)

    if body2_paragraphs:
        _fill_body(_ph(slide, PH_BODY2), body2_paragraphs)
    else:
        _remove_placeholder(slide, PH_BODY2)

    img_stream = _download_image(image_url) if image_url else None
    if img_stream:
        pic_ph = _ph(slide, PH_PICTURE)
        if pic_ph:
            try:
                pic_ph.insert_picture(img_stream)
            except Exception:
                _remove_placeholder(slide, PH_PICTURE)
    else:
        _remove_placeholder(slide, PH_PICTURE)
    return slide


def _add_summary(prs, slides_data):
    summary = (slides_data or {}).get("summary", {}) or {}
    body1 = []
    body2 = []
    if summary.get("fb"):
        body1.append({"text": "Facebook", "bold": True, "size": 18, "color": BRAND_ACCENT})
        body1.append({"text": summary["fb"], "size": 14, "color": TEXT_DARK})
    if summary.get("ig"):
        body2.append({"text": "Instagram", "bold": True, "size": 18, "color": BRAND_ACCENT})
        body2.append({"text": summary["ig"], "size": 14, "color": TEXT_DARK})

    _add_content_slide(prs,
        title="一、整體表現總結",
        subtitle=None,
        body1_paragraphs=body1 or [{"text": "本週無資料", "size": 14, "color": TEXT_MUTED}],
        body2_paragraphs=body2 or None,
    )


def _add_platform(prs, platform_label: str, key: str, slides_data: dict,
                  top_post: dict | None):
    info = (slides_data or {}).get(key) or {}
    if not info or (not info.get("data") and not info.get("highlights")):
        return

    status = info.get("status", "")
    title = platform_label + (f"（{status}）" if status and status != "無資料" else "")
    subtitle = info.get("data") or ""

    highlights = info.get("highlights") or []
    body1 = [{"text": "亮點 / 重點", "bold": True, "size": 16, "color": BRAND_ACCENT}]
    for h in highlights:
        body1.append({"text": "• " + h, "size": 13, "color": TEXT_DARK})

    # Body 2 shows top post snapshot (image goes into PICTURE on the right)
    body2 = None
    image_url = None
    if top_post:
        body2 = [{"text": "TOP 貼文", "bold": True, "size": 16, "color": BRAND_ACCENT}]
        if top_post.get("is_live"):
            body2.append({"text": "🔴 直播", "bold": True, "size": 12, "color": BRAND_ACCENT})
        msg = (top_post.get("message") or top_post.get("live_title") or "(無文字)").strip().replace("\n", " ")
        body2.append({"text": msg[:60] + ("…" if len(msg) > 60 else ""), "size": 12, "color": TEXT_DARK})
        # Add inline metric line
        metric_bits = []
        if key == "fb":
            views = top_post.get("total_views") or top_post.get("video_views")
            if views:
                metric_bits.append(f"觀看 {views:,}")
            if top_post.get("live_views"):
                metric_bits.append(f"直播即時 {top_post['live_views']:,}")
            metric_bits.append(f"讚 {top_post.get('reactions', 0)}")
            metric_bits.append(f"留言 {top_post.get('comments', 0)}")
            metric_bits.append(f"分享 {top_post.get('shares', 0)}")
        else:
            if top_post.get("views"):
                metric_bits.append(f"觀看 {top_post['views']:,}")
            if top_post.get("reach"):
                metric_bits.append(f"觸及 {top_post['reach']:,}")
            metric_bits.append(f"讚 {top_post.get('likes', 0)}")
            metric_bits.append(f"留言 {top_post.get('comments', 0)}")
        body2.append({"text": "、".join(metric_bits), "size": 12, "color": TEXT_DARK})
        image_url = top_post.get("media_url")

    _add_content_slide(prs,
        title=title,
        subtitle=subtitle,
        body1_paragraphs=body1,
        body2_paragraphs=body2,
        image_url=image_url,
    )


def _add_plans(prs, slides_data):
    plans = (slides_data or {}).get("plans") or []
    if not plans:
        return

    # Split plans across body1 (FB / 前半) and body2 (IG / 後半)
    half = (len(plans) + 1) // 2
    body1 = []
    body2 = []
    for i, p in enumerate(plans, 1):
        head = f"{i}. {p.get('platform', '')}  {p.get('title', '')}".strip()
        target = body1 if i <= half else body2
        target.append({"text": head, "bold": True, "size": 16, "color": BRAND_ACCENT})
        if p.get("detail"):
            target.append({"text": p["detail"], "size": 12, "color": TEXT_DARK})
        target.append({"text": "", "size": 4})

    _add_content_slide(prs,
        title="三、後續規劃",
        subtitle=None,
        body1_paragraphs=body1 or None,
        body2_paragraphs=body2 or None,
    )


def _add_closing(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_CLOSING])
    _set_text(slide, PH_TITLE, "Thank You")


def _load_top_posts(brand_name, week_range):
    try:
        if " ~ " not in week_range:
            return None, None
        start, end = [s.strip() for s in week_range.split(" ~ ", 1)]
        from posts_repo import get_cached_posts
        cached = get_cached_posts(brand_name, start, end)
        if not cached:
            return None, None
        fb = cached.get("fb") or []
        ig = cached.get("ig") or []
        return (fb[0] if fb else None), (ig[0] if ig else None)
    except Exception as e:
        print(f"load_top_posts failed: {e}")
        return None, None


def build_ppt(brand_name: str, week_range: str, slides_data: dict) -> bytes:
    prs = Presentation(TEMPLATE_PATH)
    _clear_existing_slides(prs)

    top_fb, top_ig = _load_top_posts(brand_name, week_range)

    _add_cover(prs, brand_name, week_range)
    _add_summary(prs, slides_data or {})
    _add_platform(prs, "Facebook", "fb", slides_data or {}, top_fb)
    _add_platform(prs, "Instagram", "ig", slides_data or {}, top_ig)
    _add_plans(prs, slides_data or {})
    _add_closing(prs)

    bio = io.BytesIO()
    prs.save(bio)
    bio.seek(0)
    return bio.read()
