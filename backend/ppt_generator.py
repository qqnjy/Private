"""Build the weekly social-media report PPT using the IGS master template."""
import os
from io import BytesIO
from copy import deepcopy
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "igs_master.pptx")

# Layout indices in the IGS master
LAYOUT_COVER = 0       # TITLE + SUBTITLE
LAYOUT_CONTENT = 1     # TITLE + OBJECT body
LAYOUT_CLOSING = 4     # TITLE only

BRAND_ACCENT = RGBColor(0xE8, 0x7A, 0x5D)
TEXT_DARK = RGBColor(0x2C, 0x3E, 0x50)


def _clear_existing_slides(prs):
    """Remove all example slides shipped in the template."""
    sld_id_lst = prs.slides._sldIdLst
    rId_to_drop = []
    for sld in list(sld_id_lst):
        rId_to_drop.append(sld.rId)
        sld_id_lst.remove(sld)
    # Also drop the relationships so the parts don't linger
    for rId in rId_to_drop:
        try:
            prs.part.drop_rel(rId)
        except Exception:
            pass


def _set_placeholder_text(slide, idx, text):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            ph.text = text
            return ph
    return None


def _fill_body_paragraphs(placeholder, paragraphs):
    """Replace a body placeholder's content with multiple paragraphs.

    Each paragraph is dict: {text, bold?, size?, color?, level?}.
    """
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


def _add_cover(prs, brand_name, week_range):
    layout = prs.slide_layouts[LAYOUT_COVER]
    slide = prs.slides.add_slide(layout)
    _set_placeholder_text(slide, 0, f"{brand_name} 社群週報")
    _set_placeholder_text(slide, 1, week_range)


def _add_summary(prs, slides_data, week_range):
    layout = prs.slide_layouts[LAYOUT_CONTENT]
    slide = prs.slides.add_slide(layout)
    _set_placeholder_text(slide, 0, "一、整體表現總結")
    body = next((ph for ph in slide.placeholders if ph.placeholder_format.idx == 1), None)
    if body is None:
        return

    summary = (slides_data or {}).get("summary", {}) or {}
    paragraphs = []
    for label, text in (("FB", summary.get("fb")), ("IG", summary.get("ig")), ("Threads", summary.get("threads"))):
        if not text:
            continue
        paragraphs.append({"text": label, "bold": True, "size": 22, "color": BRAND_ACCENT})
        paragraphs.append({"text": text, "size": 16, "color": TEXT_DARK})
        paragraphs.append({"text": "", "size": 8})
    if not paragraphs:
        paragraphs = [{"text": "本週無資料", "size": 16, "color": TEXT_DARK}]
    _fill_body_paragraphs(body, paragraphs)


def _add_platform(prs, platform_label, key, slides_data):
    info = (slides_data or {}).get(key) or {}
    if not info or (not info.get("data") and not info.get("highlights")):
        return
    layout = prs.slide_layouts[LAYOUT_CONTENT]
    slide = prs.slides.add_slide(layout)
    status = info.get("status", "")
    title = platform_label + (f"（{status}）" if status and status != "無資料" else "")
    _set_placeholder_text(slide, 0, title)

    body = next((ph for ph in slide.placeholders if ph.placeholder_format.idx == 1), None)
    if body is None:
        return

    paragraphs = []
    if info.get("data"):
        paragraphs.append({"text": "數據", "bold": True, "size": 20, "color": BRAND_ACCENT})
        paragraphs.append({"text": info["data"], "size": 16, "color": TEXT_DARK})
        paragraphs.append({"text": "", "size": 8})
    highlights = info.get("highlights") or []
    if highlights:
        paragraphs.append({"text": "亮點 / 重點", "bold": True, "size": 20, "color": BRAND_ACCENT})
        for h in highlights:
            paragraphs.append({"text": f"• {h}", "size": 16, "color": TEXT_DARK})
    _fill_body_paragraphs(body, paragraphs)


def _add_plans(prs, slides_data):
    plans = (slides_data or {}).get("plans") or []
    if not plans:
        return
    layout = prs.slide_layouts[LAYOUT_CONTENT]
    slide = prs.slides.add_slide(layout)
    _set_placeholder_text(slide, 0, "三、後續規劃")

    body = next((ph for ph in slide.placeholders if ph.placeholder_format.idx == 1), None)
    if body is None:
        return

    paragraphs = []
    for i, p in enumerate(plans, 1):
        platform = p.get("platform", "")
        title = p.get("title", "")
        detail = p.get("detail", "")
        head = f"{i}. {platform}  {title}".strip()
        paragraphs.append({"text": head, "bold": True, "size": 20, "color": BRAND_ACCENT})
        if detail:
            paragraphs.append({"text": detail, "size": 15, "color": TEXT_DARK})
        paragraphs.append({"text": "", "size": 6})
    _fill_body_paragraphs(body, paragraphs)


def _add_closing(prs):
    layout = prs.slide_layouts[LAYOUT_CLOSING]
    slide = prs.slides.add_slide(layout)
    _set_placeholder_text(slide, 0, "Thank You")


def build_ppt(brand_name: str, week_range: str, slides_data: dict) -> bytes:
    prs = Presentation(TEMPLATE_PATH)
    _clear_existing_slides(prs)

    _add_cover(prs, brand_name, week_range)
    _add_summary(prs, slides_data or {}, week_range)
    _add_platform(prs, "Facebook", "fb", slides_data or {})
    _add_platform(prs, "Instagram", "ig", slides_data or {})
    _add_platform(prs, "Threads", "threads", slides_data or {})
    _add_plans(prs, slides_data or {})
    _add_closing(prs)

    bio = BytesIO()
    prs.save(bio)
    bio.seek(0)
    return bio.read()
