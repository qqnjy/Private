import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")

client = OpenAI(
    api_key=SILICONFLOW_API_KEY or "dummy_key_to_prevent_crash_on_import",
    base_url="https://api.siliconflow.cn/v1",
    timeout=120.0,  # fail fast rather than hanging the endpoint, but allow big decks
)

# 32K window — fine for the weekly report, whose input is just post summaries.
REPORT_MODEL = "Qwen/Qwen2.5-32B-Instruct"
# 128K window — needed by /api/summarize, which ingests whole PPT decks.
LONG_CONTEXT_MODEL = "Qwen/Qwen2.5-72B-Instruct-128K"

SYSTEM_PROMPT = """你是一位資深的社群行銷專家與數據分析師。
你的任務是根據提供的社群成效數據與筆記，產出一份只涵蓋 FB 與 IG 的社群週報，
並同時輸出「貼信件用的文字大綱」與「PPT 投影片內容」。

請務必輸出**純 JSON**（不要包 ```json 或任何前後說明文字），結構如下：

{
  "outline": "string，貼到信件用的完整文字大綱，必須完全遵照下方的範例格式",
  "slides": {
    "summary": {
      "fb": "FB 一句話總結（含關鍵成長數字）",
      "ig": "IG 一句話總結"
    },
    "fb": {
      "status": "本週狀態，例如：穩健成長 / 表現亮眼 / 待優化",
      "data": "粉絲數、觸及、互動等關鍵數據（一句話）",
      "overview": ["本週概況 bullet 1（含關鍵變化%）", "本週概況 bullet 2", "本週概況 bullet 3"],
      "top_posts": [
        {"rank": 1, "summary": "TOP1 貼文（標題或主題）", "comment": "為何表現好的分析"},
        {"rank": 2, "summary": "TOP2", "comment": "分析"},
        {"rank": 3, "summary": "TOP3", "comment": "分析"}
      ],
      "highlights": ["亮點或建議 1（用於概要頁）", "亮點或建議 2"]
    },
    "ig": {
      "status": "本週狀態",
      "data": "粉絲數與觸及等關鍵數據",
      "overview": ["本週概況 bullet 1", "bullet 2", "bullet 3"],
      "top_posts": [
        {"rank": 1, "summary": "...", "comment": "..."},
        {"rank": 2, "summary": "...", "comment": "..."},
        {"rank": 3, "summary": "...", "comment": "..."}
      ],
      "highlights": ["亮點或建議 1", "亮點或建議 2"]
    },
    "plans": [
      {"platform": "FB", "title": "規劃重點", "detail": "詳細作法"},
      {"platform": "IG", "title": "規劃重點", "detail": "詳細作法"}
    ]
  }
}

outline 欄位必須完全遵照以下範例格式（含三大段標題與條列符號），**不要包含任何 Threads 段落**：

【範例格式開始】
本週社群操作重點如下：

一、 整體表現總結
•\tFB：[2-4 句。帶總觀看與 WoW 變化率、互動率變化、粉絲數與淨增減；若觀看大幅波動要說明原因（例如上週有單篇爆量影片墊高基期）；點出「表面數字」與「實際品質」是否一致]
•\tIG：[2-3 句。發佈篇數、總觀看/觸及與變化率、互動狀況、粉絲數；若某指標連續數週異常要指明第幾週]

二、 各平台成效詳述
1. Facebook (依實際數據下的狀態標籤，例如 待優化)
•\t數據：粉絲數 [X]（[±N]）；發佈 [N] 篇，總觀看 [X]（[±%]）、平均觀看 [X]；總互動 [X]（[±%]），互動率 [X]%（[±%]）；讚 [X]（[±%]）、留言 [X]（[±%]）、分享 [X]（[±%]）。
•\t爆款貼文：
o\t觀看 TOP 1：影片「[標題]」——[N] 觀看，[為何有效的具體分析]
o\t觀看 TOP 2：圖片「[標題]」——[N] 觀看，[分析]
o\t互動王 / 點擊王：圖片「[標題]」——[N] 觀看卻拿下 [N] 則留言（占全週留言 [X]%）、[N] 次點擊，[換算單位效益，例如留言率 X%，並與其他貼文對比]
•\t結構觀察：[N] 支影片貢獻 [N] 觀看（[X]%）但只帶來 [N] 次互動（[X]%）；[N] 篇圖片僅 [N] 觀看（[X]%）卻貢獻 [N] 次互動（[X]%）。[這個分工說明什麼]
•\t粉絲流失／成長：[若為淨流失，寫明連續第幾週、累計數字，並判斷原因是內容不受歡迎還是演算法帶進的非目標受眾退追；若為淨成長，寫明成長來源]
2. Instagram
•\t數據：粉絲 [X]（[±N]）；發佈 [N] 篇，總觀看 [X]（[±%]）、總觸及 [X]（[±%]）；互動 [X]（讚 [X]、留言 [X]），互動率 [X]%。
•\tTOP 貼文：[逐則列出 標題 + 觀看 / 觸及]
•\t分析建議：[內容來源是否為 FB 同步素材、觀看區間、連續幾週的問題；若上週的規劃本週未執行要直接指出這是第幾次提出，並給出「再不執行就收攏資源」這類明確結論]

三、 後續規劃
1.\tFB【[規劃標題]】：[引用本週具體數字作為依據，說明要複製或修正什麼，拆解成可執行的作法與下週的量化目標]
2.\tFB【[規劃標題]】：[同上；若是重複提出的事項要標註「（第 N 次提出）」]
3.\tIG【[規劃標題]】：[同上，含具體規格例如 9:16 直式重剪、前 3 秒鉤子、字幕]

如有需要調整的地方再跟我說，謝謝！
【範例格式結束】

格式注意：範例中的方括號 [ ] 只是欄位說明，**輸出時必須換成實際內容並把方括號刪掉**，
成品裡不可出現任何 [ ] 符號。貼文前面要寫明「影片」或「圖片」，不要寫成 [影片]。

outline 長度要求：上面的範例是**深度與詳細度的標準**，不是字數上限。
每個小節都要寫滿，不可只寫一句話帶過。整份 outline 至少 1,200 字。

數據紀律（違反者視為錯誤報告）：
- status 必須與粉絲數變化一致。粉絲數為負**絕對不可**寫「穩健成長」或「表現亮眼」，
  小幅流失寫「待優化」，連續或大幅流失寫「流失警訊」；只有粉絲數為正才可用成長類字眼。
- 每個 bullet 都要帶實際數字，不要寫「有提升的空間」「表現不俗」這種沒有數據的空話。
- 資料中附有「貼文類型分佈」時，必須在 overview 指出**哪一類帶觀看、哪一類帶互動**
  （例：影片佔 82% 觀看但只佔 15% 互動，圖片反之），並讓「後續規劃」呼應這個落差。
- TOP 貼文與互動最高貼文要分別談；若兩者不是同一則，要說明差異代表什麼。
- 只根據提供的數據推論，不要自行編造未出現的數字或貼文。
- **所有百分比與比率都已在資料中算好，直接引用即可，絕對不要自己做除法**。
  資料裡沒有的比率就不要寫，寧可省略也不要推估。
- 「連續第 N 週」直接引用資料中的「連續淨流失週數」，不可自行推算或多報。
- 引用貼文標題時必須**一字不改照抄原文**（含繁體字與 emoji），不可改寫、翻譯或縮短成別的詞。
  例如「跑車之夜」不可寫成「赛车之夜」或「賽車之夜」。

語氣要求：
- 專業、客觀但具有行動力。
- 全文一律使用**台灣繁體中文**，絕對不可出現簡體字（例：互动→互動、内容→內容、点击→點擊、视频→影片、尽管→儘管、较低→較低、透过→透過），也不可夾雜英文單字。
- 不可使用中國慣用語，一律改為台灣用法：短視頻→短影音、視頻→影片、粉絲量→粉絲數、
  流量主→版主、點贊→按讚、爆款→熱門（「爆款貼文」為固定標題，可保留）、
  用戶→使用者或玩家、內卷／賦能／抓手等詞一律不得出現。
- 將數據轉化為有意義的商業洞察。
- 嚴格輸出 JSON，不要任何額外文字或 markdown 標記。
- 整份報告只談 FB 與 IG，**完全不要提到 Threads**。
"""


def _extract_json(raw: str) -> dict | None:
    """Pull a JSON object out of an LLM response that may wrap it in fences,
    prefix it with chatter, or append explanations afterward. Returns the
    parsed dict, or None if nothing parses."""
    s = (raw or "").strip()
    # Drop any ```json / ``` fences anywhere
    s = re.sub(r"```[a-zA-Z]*\s*", "", s)
    s = s.replace("```", "")

    # strict=False lets us accept raw tabs/newlines inside string values
    # (the LLM sometimes emits literal control chars instead of \t / \n escapes)
    try:
        return json.loads(s, strict=False)
    except json.JSONDecodeError:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end > start:
        candidate = s[start:end + 1]
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            pass

    # Last resort: pull the outline field out by regex. Decode JSON escapes
    # (e.g. \n, 本) properly — using json.loads on the captured string
    # avoids the unicode_escape pitfall that mangles raw UTF-8 Chinese bytes.
    m = re.search(r'"outline"\s*:\s*"((?:[^"\\]|\\.)*)"', s, re.DOTALL)
    if m:
        try:
            outline_str = json.loads('"' + m.group(1) + '"', strict=False)
        except Exception:
            outline_str = m.group(1)
        return {"outline": outline_str, "slides": None}
    return None


def _looks_like_raw_json(text: str) -> bool:
    """Heuristic — outline shouldn't start with { or contain "outline": near the start."""
    if not text:
        return False
    t = text.strip()[:200]
    if t.startswith("{") or t.startswith("```") or '"outline"' in t:
        return True
    # Detect mojibake (UTF-8 decoded as Latin-1) by sampling for the giveaway
    # characters that latin-1 → utf-8 produces from common Chinese codepoints.
    mojibake_markers = ("Ã©", "Ã¨", "Ã¦", "æ¬", "ä¸", "ç¤¾", "ä½")
    return any(m in t for m in mojibake_markers)


def generate_weekly_report(brand_name: str, notes: str, followers_growth_fb: int, followers_growth_ig: int, followers_growth_threads: int = 0) -> dict:
    user_prompt = f"""請幫我撰寫【{brand_name}】的本週社群週報（只涵蓋 FB 與 IG）。

【本週數據摘要】
- FB 粉絲成長：{followers_growth_fb} 人
- IG 粉絲成長：{followers_growth_ig} 人

【本週重要筆記與亮點】
{notes}

請輸出 JSON（含 outline 與 slides 兩欄位），不要任何前後說明。整份報告**不要出現 Threads**。
"""
    def _call(temperature: float):
        response = client.chat.completions.create(
            model=REPORT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=6000,   # 詳細版 outline (1,200+ 字) 加 slides JSON 會超過 2,500
        )
        return response.choices[0].message.content

    try:
        last_raw = ""
        # Up to 2 attempts: if the first call returns malformed JSON or no slides,
        # try once more with a lower temperature for a cleaner format.
        for attempt, temp in enumerate((0.7, 0.2)):
            raw = _call(temp)
            last_raw = raw
            data = _extract_json(raw)
            if data is None:
                continue
            if "outline" not in data and "report" in data:
                data["outline"] = data.pop("report")
            # Accept if we have BOTH outline and slides
            if data.get("outline") and data.get("slides"):
                return data
            # If only outline (no slides) but it's the second attempt, take it.
            if attempt == 1 and data.get("outline"):
                return data
        # All attempts failed — return whatever the last extraction gave us, or raw.
        data = _extract_json(last_raw) or {"outline": last_raw, "slides": None,
                                            "error": "JSON 解析失敗，僅回傳純文字"}
        return data
    except Exception as e:
        print(f"SiliconFlow API 錯誤: {e}")
        return {"outline": f"產生報告時發生錯誤：{str(e)}", "slides": None, "error": str(e)}


if __name__ == "__main__":
    mock_notes = '''
- FB 觸及成長大約 50%
- 爆款貼文是「保持聽牌不被胡牌」，留言討論很熱烈
- IG 表現很差，觸及掉很多
- 之後會測試更多與「生活情境」連結的高分享性短影音
    '''
    res = generate_weekly_report("測試專案", mock_notes, 120, -5, 10)
    print(json.dumps(res, ensure_ascii=False, indent=2))
