import React, { useState, useEffect } from 'react';
import { Bot, FileText, Send, Loader2, Download } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function AiReporter() {
  const [brands, setBrands] = useState({});
  const [selectedBrand, setSelectedBrand] = useState('');
  
  // ISO week string e.g. "2026-W26"
  const [weekString, setWeekString] = useState(() => {
    const now = new Date();
    const d = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    return `${d.getUTCFullYear()}-W${weekNo.toString().padStart(2, '0')}`;
  });

  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState('');
  const [slidesData, setSlidesData] = useState(null);
  const [downloadingPpt, setDownloadingPpt] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/targets`)
      .then(res => res.json())
      .then(data => {
        const grouped = {};
        data.forEach(t => {
          // Normalize brand name by removing platform suffixes
          let brand = t.name
             .replace(/\(THREADS\)$/i, '')
             .replace(/粉絲團/i, '')
             .replace(/_IG/i, '')
             .replace(/\(FB\)$/i, '')
             .replace(/\(IG\)$/i, '')
             .trim();
          
          if (!grouped[brand]) grouped[brand] = {};
          if (t.platform === 'fb') grouped[brand].fb = t.id;
          if (t.platform === 'ig') grouped[brand].ig = t.id;
          if (t.platform === 'threads' || t.name.toLowerCase().includes('threads')) {
              grouped[brand].threads = t.id;
          }
        });
        setBrands(grouped);
        if (Object.keys(grouped).length > 0) {
          setSelectedBrand(Object.keys(grouped)[0]);
        }
      });
  }, []);

  // Given an ISO week string "YYYY-Www", return Mon~Sun range
  const getWeekDateRange = (weekStr) => {
    const [year, week] = weekStr.split('-W').map(Number);
    // ISO week 1 contains Jan 4th. Compute Monday of given week.
    const jan4 = new Date(year, 0, 4);
    const jan4Day = jan4.getDay() || 7; // Mon=1..Sun=7
    const week1Monday = new Date(jan4);
    week1Monday.setDate(jan4.getDate() - (jan4Day - 1));
    const start = new Date(week1Monday);
    start.setDate(week1Monday.getDate() + (week - 1) * 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    const fmt = (dt) => {
      const yy = dt.getFullYear();
      const mm = String(dt.getMonth() + 1).padStart(2, '0');
      const dd = String(dt.getDate()).padStart(2, '0');
      return `${yy}-${mm}-${dd}`;
    };
    return { start: fmt(start), end: fmt(end) };
  };

  const weekRange = getWeekDateRange(weekString);

  const [fromCache, setFromCache] = useState(false);
  const [generatedAt, setGeneratedAt] = useState(null);

  // Silently look up cached report when brand or week changes — no LLM, no Graph API.
  useEffect(() => {
    if (!selectedBrand || !weekString) return;
    const { start, end } = getWeekDateRange(weekString);
    let cancelled = false;
    setError(null);
    fetch(`${API_BASE}/report/cached?brand_name=${encodeURIComponent(selectedBrand)}&start_date=${start}&end_date=${end}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (cancelled) return;
        if (data && data.status === 'success') {
          setReport(data.report);
          setSlidesData(data.slides || null);
          setFromCache(true);
          setGeneratedAt(data.generated_at || null);
        } else {
          // No cache for this brand+week — clear stale display
          setReport('');
          setSlidesData(null);
          setFromCache(false);
          setGeneratedAt(null);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBrand, weekString]);

  const handleGenerate = async (eOrRefresh) => {
    const refresh = eOrRefresh === true;
    if (eOrRefresh && eOrRefresh.preventDefault) eOrRefresh.preventDefault();
    if (!selectedBrand) {
      setError('請選擇專案');
      return;
    }
    if (!weekString) {
      setError('請選擇週次');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { start, end } = getWeekDateRange(weekString);
      const brandData = brands[selectedBrand];
      const tids = [];
      if (brandData.fb) tids.push(brandData.fb);
      if (brandData.ig) tids.push(brandData.ig);
      if (brandData.threads) tids.push(brandData.threads);

      // Fetch trend data for the selected week
      const trendRes = await fetch(`${API_BASE}/stats/trend?start_date=${start}&end_date=${end}&target_ids=${tids.join(',')}`);
      const trendData = await trendRes.json();
      
      let growthFb = 0;
      let growthIg = 0;
      let growthThreads = 0;

      if (trendData && trendData.length > 0) {
         const firstDay = trendData[0];
         const lastDay = trendData[trendData.length - 1];
         
         if (firstDay.fb !== undefined && lastDay.fb !== undefined) {
             growthFb = lastDay.fb - firstDay.fb;
         }
         if (firstDay.ig !== undefined && lastDay.ig !== undefined) {
             growthIg = lastDay.ig - firstDay.ig;
         }
         if (firstDay.threads !== undefined && lastDay.threads !== undefined) {
             growthThreads = lastDay.threads - firstDay.threads;
         }
      }

      // Automatically construct the notes including growth details
      const defaultNotes = `本週(${start} ~ ${end})數據自動結算：\n- FB 粉絲成長：${growthFb} 人\n- IG 粉絲成長：${growthIg} 人\n- Threads 粉絲成長：${growthThreads} 人\n\n其他重點補充：\n${notes || '無'}`;

      const response = await fetch(`${API_BASE}/generate-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: selectedBrand,
          notes: defaultNotes,
          followers_growth_fb: growthFb,
          followers_growth_ig: growthIg,
          followers_growth_threads: growthThreads,
          start_date: start,
          end_date: end,
          refresh,
        }),
      });
      
      if (!response.ok) {
        throw new Error('伺服器錯誤');
      }
      
      const data = await response.json();
      if (data.status === 'success') {
        setReport(data.report);
        setSlidesData(data.slides || null);
        setFromCache(!!data.from_cache);
        setGeneratedAt(data.generated_at || null);
      } else {
        throw new Error(data.message || '產生失敗');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPpt = async () => {
    setDownloadingPpt(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/generate-ppt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: selectedBrand,
          week_range: `${weekRange.start} ~ ${weekRange.end}`,
          slides: slidesData || {},
        }),
      });
      if (!res.ok) throw new Error('產生 PPT 失敗');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedBrand}_週報_${weekRange.start}_${weekRange.end}.pptx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloadingPpt(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-3 bg-[var(--accent)]/10 rounded-xl">
          <Bot className="text-[var(--accent)]" size={24} />
        </div>
        <div>
          <h2 className="text-2xl font-black text-[var(--text-primary)]">AI 自動產週報</h2>
          <p className="text-sm text-[var(--text-muted)] font-medium">選好專案與週次，系統自動為你計算各平台(FB/IG/Threads)粉絲成長並產出專業週報</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Form */}
        <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-6 shadow-sm">
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-[var(--text-secondary)] mb-2">專案名稱</label>
              <select
                value={selectedBrand}
                onChange={(e) => setSelectedBrand(e.target.value)}
                className="w-full px-4 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl focus:border-[var(--accent)] focus:outline-none transition-colors text-[var(--text-primary)]"
              >
                {Object.keys(brands).map(brand => (
                  <option key={brand} value={brand}>{brand}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-bold text-[var(--text-secondary)] mb-2">哪一週</label>
              <input
                type="week"
                value={weekString}
                onChange={(e) => setWeekString(e.target.value)}
                className="w-full px-4 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl focus:border-[var(--accent)] focus:outline-none transition-colors text-[var(--text-primary)]"
              />
              <p className="mt-2 text-xs font-medium text-[var(--text-muted)]">
                日期區間：<span className="font-bold text-[var(--accent)]">{weekRange.start} ~ {weekRange.end}</span>（週一 ~ 週日）
              </p>
            </div>

            <div>
              <label className="block text-sm font-bold text-[var(--text-secondary)] mb-2">其他備註 (選填，例如這週發了什麼爆款貼文)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows="4"
                placeholder="例如：這週發了端午節活動，留言數破千。"
                className="w-full px-4 py-3 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl focus:border-[var(--accent)] focus:outline-none transition-colors text-[var(--text-primary)] resize-none"
              ></textarea>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-sm font-bold">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[var(--accent)] hover:opacity-90 text-[var(--bg-base)] rounded-xl font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
              {loading ? '系統正在抓資料與 AI 撰寫中...' : '自動產生週報'}
            </button>
            {report && (
              <button
                type="button"
                onClick={() => handleGenerate(true)}
                disabled={loading}
                className="w-full py-2 bg-[var(--bg-base)] border border-[var(--border-color)] hover:border-[var(--accent)] text-[var(--text-primary)] rounded-xl text-sm font-bold transition disabled:opacity-50"
              >
                重新生成（強制呼叫 AI，會消耗 token）
              </button>
            )}
          </form>
        </div>

        {/* Output Area */}
        <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] p-6 shadow-sm flex flex-col h-[600px] lg:h-auto">
          <div className="flex items-center gap-2 mb-4 text-[var(--text-secondary)]">
            <FileText size={20} />
            <h3 className="font-bold">產出結果</h3>
          </div>
          
          {report && generatedAt && (
            <div className="mb-2 flex items-center gap-2 text-xs">
              <span className={`px-2 py-0.5 rounded-md font-bold ${fromCache ? 'bg-emerald-500/10 text-emerald-600' : 'bg-blue-500/10 text-blue-600'}`}>
                {fromCache ? '已快取' : '剛生成'}
              </span>
              <span className="text-[var(--text-muted)]">{new Date(generatedAt).toLocaleString('zh-TW')}</span>
            </div>
          )}
          <div className="flex-1 bg-[var(--bg-base)] rounded-xl border border-[var(--border-color)] p-4 overflow-y-auto">
            {report ? (
              <div className="whitespace-pre-wrap text-[var(--text-primary)] text-sm leading-relaxed">
                {report}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-[var(--text-muted)] space-y-3">
                <Bot size={48} className="opacity-20" />
                <p className="text-sm font-medium">選好專案與週次，AI 會自動幫你結算並寫出報告</p>
              </div>
            )}
          </div>
          
          {report && (
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(report);
                  alert('已複製到剪貼簿！');
                }}
                className="py-2 bg-[var(--bg-base)] border border-[var(--border-color)] hover:border-[var(--accent)] text-[var(--text-primary)] rounded-xl font-bold transition"
              >
                複製文字大綱
              </button>
              <button
                onClick={handleDownloadPpt}
                disabled={!report || downloadingPpt}
                className="py-2 bg-[var(--accent)] hover:opacity-90 text-[var(--bg-base)] rounded-xl font-bold transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {downloadingPpt ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                {downloadingPpt ? '產生中...' : '下載 PPT'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
