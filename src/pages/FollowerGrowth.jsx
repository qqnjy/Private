import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const taipeiMonth = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit' }).format(new Date());
const format = (value) => value == null ? '未取得' : value.toLocaleString('zh-TW');
const signed = (value) => value == null ? '無法比較' : `${value > 0 ? '+' : ''}${format(value)}`;

export default function FollowerGrowth() {
  const [month, setMonth] = useState(taipeiMonth);
  const [platform, setPlatform] = useState('fb');
  const [project, setProject] = useState('tmd');
  const [projects, setProjects] = useState([{ key: 'tmd', name: '滿貫大亨' }]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!/^\d{4}-\d{2}$/.test(month)) return;
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError('');
      setData(null);
      try {
        const response = await fetch(`${API_BASE}/followers/month?month=${encodeURIComponent(month)}&project=${encodeURIComponent(project)}`, { signal: controller.signal });
        const payload = await response.json();
        if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : '資料暫時無法載入');
        setData(payload);
        if (payload.projects) setProjects(payload.projects);
      } catch (e) {
        if (e.name !== 'AbortError') setError(e.message || '資料暫時無法載入');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [month, project, retry]);

  const report = data?.project_key === project ? data?.platforms?.[platform] : null;
  const projectName = projects.find((p) => p.key === project)?.name || '社群';
  const summary = report?.summary;
  const card = 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5';
  const cards = [
    { key: 'follows', title: '新增追蹤', color: '#79a69e' },
    { key: 'unfollows', title: '退追／取消追蹤', color: '#c87a7a' },
    { key: 'net', title: '淨變化', color: '#d2a154' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-[var(--text-primary)]">{projectName}｜追蹤增減</h2>
          <p className="mt-2 text-[var(--text-secondary)]">分開看新增與流失，作為內容規劃與每月檢討的依據。</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-[var(--text-secondary)]">專案
            <select aria-label="選擇專案" value={project} onChange={(e) => setProject(e.target.value)} className="block mt-1 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)]">
              {projects.map((p) => <option key={p.key} value={p.key}>{p.name}</option>)}
            </select>
          </label>
          <label className="text-sm text-[var(--text-secondary)]">月份
            <input aria-label="選擇月份" type="month" value={month} max={taipeiMonth()} onChange={(e) => setMonth(e.target.value)} className="block mt-1 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)]" />
          </label>
          <label className="text-sm text-[var(--text-secondary)]">平台
            <select aria-label="選擇平台" value={platform} onChange={(e) => setPlatform(e.target.value)} className="block mt-1 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)]">
              <option value="fb">Facebook</option><option value="ig">Instagram</option>
            </select>
          </label>
          <button type="button" onClick={() => setRetry((n) => n + 1)} className="self-end px-4 py-2 rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)]">重新載入</button>
        </div>
      </div>
      {loading && <div role="status" className={card}>載入追蹤增減資料中…</div>}
      {error && <div role="alert" className={`${card} text-red-400`}>{error}。請稍後重新載入。</div>}
      {report && <>
        {data.collection_error && <p role="status" className="text-sm text-amber-400">本專案最近一次更新未完成，顯示既有資料：{data.collection_error}</p>}
        <div className="text-sm text-[var(--text-secondary)] space-y-1">
          <p>統計區間：{data.period.start} 至 {data.period.end || '本月尚無已結束的每日區間'}</p>
          <p>資料更新：{data.updated_at ? new Date(data.updated_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }) : '未取得'}（台灣時間） · 完整資料 {summary.complete_days}／{summary.expected_days} 天</p>
          <p>比較區間：{report.previous_period.start} 至 {report.previous_period.end || '—'}；未結束月份比較兩月相同已過天數，較短月份以可比較天數為準。</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {cards.map(({ key, title, color }) => <div key={key} className={card}>
            <p className="text-sm text-[var(--text-secondary)]">{title}{!summary.is_complete && key !== 'net' ? '（已取得部分）' : ''}</p>
            <p className="text-3xl font-bold mt-2" style={{ color }}>{key === 'net' && summary[key] != null ? signed(summary[key]) : format(summary[key])}</p>
            <p className="mt-3 text-sm text-[var(--text-secondary)]">較上月：{signed(report.change[key])}</p>
          </div>)}
        </div>
        {!summary.is_complete && <p className="text-sm text-amber-400">本區間資料未完整；缺值不計為 0，淨變化與月比較暫不計算。</p>}
        <div className={card}>
          <h3 className="font-bold mb-4">每日新增、退追與淨變化</h3>
          {summary.complete_days > 0 ? <div className="h-80 w-full"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={report.rows} margin={{ top: 10, right: 15, bottom: 10, left: 0 }}>
              <CartesianGrid stroke="var(--border-color)" strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} stroke="var(--text-secondary)" />
              <YAxis stroke="var(--text-secondary)" allowDecimals={false} />
              <Tooltip formatter={(value) => format(value)} contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8 }} />
              <Legend />
              <Line type="linear" dataKey="follows" name="新增追蹤" stroke="#79a69e" strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="linear" dataKey="unfollows" name="退追" stroke="#c87a7a" strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="linear" dataKey="net" name="淨變化" stroke="#d2a154" strokeWidth={2} dot={false} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer></div> : <p className="py-12 text-center text-[var(--text-muted)]">此月份尚無完整每日數據，請選擇其他月份。</p>}
        </div>
        <div className={`${card} overflow-x-auto`}>
          <h3 className="font-bold mb-4">每日明細</h3>
          <table className="w-full text-sm text-right">
            <thead className="text-[var(--text-secondary)]"><tr><th className="text-left py-3">日期</th><th>新增追蹤</th><th>退追</th><th>淨變化</th></tr></thead>
            <tbody>{[...report.rows].reverse().map((r) => <tr key={r.date} className="border-t border-[var(--border-color)]"><td className="text-left py-3">{r.date}</td><td>{format(r.follows)}</td><td>{format(r.unfollows)}</td><td className={r.net < 0 ? 'text-red-400' : r.net > 0 ? 'text-emerald-400' : ''}>{r.net == null ? '未取得' : signed(r.net)}</td></tr>)}</tbody>
          </table>
        </div>
        <div className={`${card} text-sm text-[var(--text-secondary)] space-y-2`}>
          {data.notes.map((note) => <p key={note}>{note}</p>)}
          <p>退追高點不代表由當天貼文造成，需與題材、活動及較長期間的趨勢一起判讀。</p>
        </div>
      </>}
    </div>
  );
}
