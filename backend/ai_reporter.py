import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")

client = OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)

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
•\tFB：[總結 FB 亮點]
•\tIG：[總結 IG 亮點]

二、 各平台成效詳述
1. Facebook (狀態)
•\t數據：粉絲數 [X]。[其他相關數據]
•\t爆款貼文：
o\tTOP 1：[爆款貼文分析]
o\t時事梗：[其他亮點貼文]
2. Instagram
•\t數據：粉絲數 [X]。[其他相關數據]
•\t分析建議：[IG 表現分析與建議]

三、 後續規劃
1.\tFB [規劃重點]：[詳細作法]
2.\tIG [規劃重點]：[詳細作法]
【範例格式結束】

語氣要求：
- 專業、客觀但具有行動力。
- 使用繁體中文。
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
            return None
    return None


def generate_weekly_report(brand_name: str, notes: str, followers_growth_fb: int, followers_growth_ig: int, followers_growth_threads: int = 0) -> dict:
    user_prompt = f"""請幫我撰寫【{brand_name}】的本週社群週報（只涵蓋 FB 與 IG）。

【本週數據摘要】
- FB 粉絲成長：{followers_growth_fb} 人
- IG 粉絲成長：{followers_growth_ig} 人

【本週重要筆記與亮點】
{notes}

請輸出 JSON（含 outline 與 slides 兩欄位），不要任何前後說明。整份報告**不要出現 Threads**。
"""
    try:
        response = client.chat.completions.create(
            model="stepfun-ai/Step-3.5-Flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )
        raw = response.choices[0].message.content
        data = _extract_json(raw)
        if data is None:
            return {"outline": raw, "slides": None, "error": "JSON 解析失敗，僅回傳純文字"}
        # Ensure outline exists; if the model put the report under another key, try to find it
        if "outline" not in data and "report" in data:
            data["outline"] = data.pop("report")
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
