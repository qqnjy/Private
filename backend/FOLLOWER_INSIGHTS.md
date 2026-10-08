# 滿貫每日追蹤增減

- 網頁：`/followers`；查詢：`GET /api/followers/month?month=2026-09`。
- FB：`page_daily_follows`、`page_daily_unfollows`；日期是 Meta 區間結束時間的前一日。
- IG：每日台灣時間 00:00 至次日 00:00，以 `follows_and_unfollows` / `follow_type` 的 FOLLOWER、NON_FOLLOWER 分項取得。
- API 值為平台回報數量，不能當成追蹤總數快照差，也不能歸因於當日某篇貼文。
- 每日台灣時間 16:00 的 GitHub Actions 排程重取最近七個已結束的每日區間，允許平台延遲補數；僅提交追蹤數據檔並觸發 Git 自動部署。
- 資料儲存在目前專案 `backend/data/follower_daily.json`，沿用 Vercel / Render 的 Git 自動部署，無須新增 Supabase 表。
- 收集程式從 `FB_GRAPH_TOKEN` 環境變數讀取權杖；資料檔與前端不含權杖。
- 收集失敗不覆寫既有檔案；頁面顯示上次更新時間。缺值保留 null，不製造 0。
- 本月排除今天，與上月相同已過天數比較；前月較短則僅比較共通天數。完整月份比較完整月份。
- 暫未蒐集逐篇追蹤數：FB 及 IG 影片指標支援不完整，不使用每日增減代替逐篇歸因。

本機回補：在 backend 執行 `python collect_follower_insights.py --start 2026-08-01 --end 2026-10-07`。
驗證：`python -m unittest test_follower_insights -v`。
