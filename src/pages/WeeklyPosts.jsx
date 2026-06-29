import React, { useState, useEffect, useMemo } from 'react';
import { Sparkles, MessageSquare, Heart, Share2, Eye, ExternalLink, Loader2, Bookmark, Play, Clock, RefreshCw, ClipboardCopy } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function WeeklyPosts() {
  const [brands, setBrands] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState('');
  const [weekString, setWeekString] = useState(() => {
    const now = new Date();
    const d = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    return `${d.getUTCFullYear()}-W${weekNo.toString().padStart(2, '0')}`;
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [platformFilter, setPlatformFilter] = useState('all');

  useEffect(() => {
    fetch(`${API_BASE}/targets`)
      .then(r => r.json())
      .then(rows => {
        const set = new Set();
        rows.forEach(t => {
          const cleaned = t.name
            .replace(/\(THREADS\)$/i, '')
            .replace(/粉絲團/i, '')
            .replace(/_IG/i, '')
            .replace(/\(FB\)$/i, '')
            .replace(/\(IG\)$/i, '')
            .trim();
          set.add(cleaned);
        });
        const list = Array.from(set);
        setBrands(list);
        if (list.length > 0) setSelectedBrand(list[0]);
      });
  }, []);

  const weekRange = useMemo(() => {
    const [year, week] = weekString.split('-W').map(Number);
    const jan4 = new Date(year, 0, 4);
    const jan4Day = jan4.getDay() || 7;
    const week1Monday = new Date(jan4);
    week1Monday.setDate(jan4.getDate() - (jan4Day - 1));
    const start = new Date(week1Monday);
    start.setDate(week1Monday.getDate() + (week - 1) * 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    const fmt = (dt) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
    return { start: fmt(start), end: fmt(end) };
  }, [weekString]);

  const [copied, setCopied] = useState(false);

  const buildAiPrompt = () => {
    if (!data) return '';
    const lines = [];
    lines.push(`# ${selectedBrand} — 本週貼文成效（${weekRange.start} ~ ${weekRange.end}）`);
    if (data.matched_page) {
      lines.push(`> 粉專：${data.matched_page.name}${data.matched_page.ig_user_id ? '（含 IG 商業帳號）' : ''}`);
    }
    if (data.fetched_at) {
      lines.push(`> 抓取時間：${new Date(data.fetched_at).toLocaleString('zh-TW')}`);
    }
    lines.push('');

    const writePlatform = (label, posts, platform) => {
      if (!posts || !posts.length) return;
      lines.push(`## ${label}（共 ${posts.length} 篇）`);
      lines.push('');
      posts.forEach((p, idx) => {
        const ts = p.created_at ? new Date(p.created_at).toLocaleString('zh-TW') : '';
        const liveTag = p.is_live ? ' 🔴 LIVE' : '';
        const type = p.post_type || (p.media_type === 'video' ? '影片' : p.media_type === 'photo' ? '圖片' : p.media_type === 'album' ? '圖文' : p.media_type === 'VIDEO' ? '影片' : p.media_type === 'IMAGE' ? '圖片' : p.media_type === 'CAROUSEL_ALBUM' ? '圖文' : '其他');
        lines.push(`### #${idx + 1} ${type}${liveTag} — ${ts}`);

        const metrics = [];
        if (platform === 'fb') {
          const views = p.total_views || p.video_views;
          if (views) metrics.push(`觀看 ${views.toLocaleString()}`);
          if (p.is_live && p.live_views) metrics.push(`直播即時 ${p.live_views.toLocaleString()}`);
          if (p.video_views && p.video_views !== p.total_views) metrics.push(`3s+ ${p.video_views.toLocaleString()}`);
          if (p.video_views_15s) metrics.push(`15s ${p.video_views_15s.toLocaleString()}`);
          metrics.push(`讚 ${p.reactions || 0}`);
          metrics.push(`留言 ${p.comments || 0}`);
          metrics.push(`分享 ${p.shares || 0}`);
          if (p.clicks != null) metrics.push(`點擊 ${p.clicks}`);
          if (p.avg_watch_ms) metrics.push(`平均觀看 ${(p.avg_watch_ms / 1000).toFixed(1)}s`);
        } else {
          if (p.views) metrics.push(`觀看 ${p.views.toLocaleString()}`);
          if (p.reach != null) metrics.push(`觸及 ${p.reach.toLocaleString()}`);
          metrics.push(`讚 ${p.likes || 0}`);
          metrics.push(`留言 ${p.comments || 0}`);
          if (p.saved) metrics.push(`儲存 ${p.saved}`);
          if (p.avg_watch_time_ms) metrics.push(`平均觀看 ${(p.avg_watch_time_ms / 1000).toFixed(1)}s`);
        }
        lines.push(metrics.join(' | '));

        const text = (p.message || p.live_title || '').trim();
        if (text) lines.push(text);
        lines.push('');
      });
    };

    writePlatform('FB', data.fb, 'fb');
    writePlatform('IG', data.ig, 'ig');
    return lines.join('\n');
  };

  const handleCopyForAi = async () => {
    const text = buildAiPrompt();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setError('複製失敗：' + (err.message || err));
    }
  };

  const handleFetch = async (refresh = false) => {
    if (!selectedBrand) return;
    setLoading(true);
    setError(null);
    if (refresh) setData(null);
    try {
      const url = `${API_BASE}/posts/week?brand_name=${encodeURIComponent(selectedBrand)}&start_date=${weekRange.start}&end_date=${weekRange.end}${refresh ? '&refresh=true' : ''}`;
      const r = await fetch(url);
      if (!r.ok) throw new Error('抓取失敗');
      const j = await r.json();
      setData(j);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Auto-load cached data when brand or week changes
  useEffect(() => {
    if (!selectedBrand) return;
    handleFetch(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBrand, weekRange.start, weekRange.end]);

  const allPosts = useMemo(() => {
    if (!data) return [];
    const fb = (data.fb || []).map(p => ({ ...p, _platform: 'fb', _views: p.total_views || p.video_views || p.live_views || 0 }));
    const ig = (data.ig || []).map(p => ({ ...p, _platform: 'ig', _views: p.views || 0 }));
    let combined = [...fb, ...ig];
    if (platformFilter !== 'all') combined = combined.filter(p => p._platform === platformFilter);
    return combined.sort((a, b) => (b._views || 0) - (a._views || 0) || (b.engagement || 0) - (a.engagement || 0));
  }, [data, platformFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-3 bg-[var(--accent)]/10 rounded-xl">
          <Sparkles className="text-[var(--accent)]" size={24} />
        </div>
        <div>
          <h2 className="text-2xl font-black text-[var(--text-primary)]">本週貼文成效</h2>
          <p className="text-sm text-[var(--text-muted)] font-medium">自動抓取選定週次的 FB / IG 貼文，依互動排序</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-5 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-bold text-[var(--text-secondary)] mb-2">專案</label>
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            >
              {brands.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-bold text-[var(--text-secondary)] mb-2">哪一週</label>
            <input
              type="week"
              value={weekString}
              onChange={(e) => setWeekString(e.target.value)}
              className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">{weekRange.start} ~ {weekRange.end}</p>
          </div>
          <div>
            <label className="block text-sm font-bold text-[var(--text-secondary)] mb-2">平台</label>
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            >
              <option value="all">全部</option>
              <option value="fb">只看 FB</option>
              <option value="ig">只看 IG</option>
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={() => handleFetch(true)}
              disabled={loading || !selectedBrand}
              className="flex-1 py-2 bg-[var(--accent)] hover:opacity-90 text-[var(--bg-base)] rounded-xl font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={16} />}
              {loading ? '抓取中...' : '重新抓取'}
            </button>
          </div>
        </div>
        {data && (data.fb?.length > 0 || data.ig?.length > 0) && (
          <div className="mt-3 flex justify-end">
            <button
              onClick={handleCopyForAi}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold border border-[var(--border-color)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-primary)] rounded-lg transition"
              title="把所有貼文整理成 Markdown 複製，可貼給其他 AI 工具分析"
            >
              <ClipboardCopy size={14} />
              {copied ? '已複製 ✓' : '複製給其他 AI 分析'}
            </button>
          </div>
        )}
        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-sm font-bold">
            {error}
          </div>
        )}
        {data && !data.matched_page && (
          <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-700 text-sm">
            找不到對應的 FB 粉專。請確認專案名稱「{selectedBrand}」與授權的粉專名稱一致。
          </div>
        )}
        {data?.matched_page && (
          <div className="mt-3 text-xs text-[var(--text-muted)] flex flex-wrap items-center gap-3">
            <span>
              已連結粉專：<span className="font-bold text-[var(--text-primary)]">{data.matched_page.name}</span>
              {data.matched_page.ig_user_id ? '（含 IG 商業帳號）' : '（無 IG 連動）'}
            </span>
            {data.fetched_at && (
              <span className={`px-2 py-0.5 rounded-md ${data.from_cache ? 'bg-emerald-500/10 text-emerald-600' : 'bg-blue-500/10 text-blue-600'}`}>
                {data.from_cache ? '已快取' : '剛抓取'}：{new Date(data.fetched_at).toLocaleString('zh-TW')}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Posts */}
      {data && (
        <div className="space-y-3">
          {allPosts.length === 0 && (
            <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-8 text-center text-[var(--text-muted)]">
              本週沒有抓到符合條件的貼文
            </div>
          )}
          {allPosts.map((p, idx) => (
            <div key={`${p._platform}-${p.id}`} className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-4 shadow-sm flex gap-4">
              <div className="flex-shrink-0 w-32 h-32 rounded-xl overflow-hidden bg-[var(--bg-base)] flex items-center justify-center">
                {p.media_url ? (
                  <img src={p.media_url} alt="" className="w-full h-full object-cover" />
                ) : (
                  <span className="text-xs text-[var(--text-muted)]">無圖</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className={`px-2 py-0.5 rounded-md text-xs font-bold ${p._platform === 'fb' ? 'bg-blue-500/10 text-blue-600' : 'bg-pink-500/10 text-pink-600'}`}>
                    {p._platform.toUpperCase()}
                  </span>
                  {p.is_live && (
                    <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-red-500/10 text-red-600 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" /> LIVE 直播
                    </span>
                  )}
                  <span className="text-xs text-[var(--text-muted)]">{new Date(p.created_at).toLocaleString('zh-TW')}</span>
                  <span className="ml-auto text-xs font-bold text-[var(--accent)]">#{idx + 1}</span>
                </div>
                <p className="text-sm text-[var(--text-primary)] line-clamp-3 mb-3 whitespace-pre-wrap">{p.message || p.live_title || '(無文字)'}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-bold text-[var(--text-secondary)]">
                  {/* Views shown most prominently */}
                  {p._views > 0 && (
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-[var(--accent)]/10 text-[var(--accent)] rounded-md">
                      <Play size={14} /> 觀看 {p._views.toLocaleString()}
                    </span>
                  )}
                  {p._platform === 'fb' ? (
                    <>
                      {p.is_live && p.live_views > 0 && (
                        <span className="flex items-center gap-1 text-red-600">直播即時 {p.live_views.toLocaleString()}</span>
                      )}
                      {p.video_views > 0 && p.video_views !== p.total_views && (
                        <span className="flex items-center gap-1 text-[var(--text-muted)]" title="≥3 秒觀看數">3s+ {p.video_views.toLocaleString()}</span>
                      )}
                      {p.video_views_15s > 0 && (
                        <span className="flex items-center gap-1 text-[var(--text-muted)]" title="≥15 秒觀看數">15s {p.video_views_15s.toLocaleString()}</span>
                      )}
                      <span className="flex items-center gap-1"><Heart size={14} /> {p.reactions}</span>
                      <span className="flex items-center gap-1"><MessageSquare size={14} /> {p.comments}</span>
                      <span className="flex items-center gap-1"><Share2 size={14} /> {p.shares}</span>
                      {p.clicks != null && <span className="flex items-center gap-1">點擊 {p.clicks}</span>}
                      {p.avg_watch_ms > 0 && (
                        <span className="flex items-center gap-1"><Clock size={14} /> 平均 {(p.avg_watch_ms / 1000).toFixed(1)}s</span>
                      )}
                    </>
                  ) : (
                    <>
                      {p.reach != null && <span className="flex items-center gap-1"><Eye size={14} /> 觸及 {p.reach}</span>}
                      <span className="flex items-center gap-1"><Heart size={14} /> {p.likes}</span>
                      <span className="flex items-center gap-1"><MessageSquare size={14} /> {p.comments}</span>
                      {p.saved > 0 && <span className="flex items-center gap-1"><Bookmark size={14} /> {p.saved}</span>}
                      {p.avg_watch_time_ms > 0 && (
                        <span className="flex items-center gap-1"><Clock size={14} /> 平均觀看 {(p.avg_watch_time_ms / 1000).toFixed(1)}s</span>
                      )}
                    </>
                  )}
                  {p.permalink && (
                    <a href={p.permalink} target="_blank" rel="noopener noreferrer" className="ml-auto flex items-center gap-1 text-[var(--accent)] hover:underline">
                      <ExternalLink size={14} /> 開啟原文
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
