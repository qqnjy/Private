import { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Trash2, RefreshCw } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export default function ManageList() {
  const [targets, setTargets] = useState([]);
  const [form, setForm] = useState({ name: '', platform: 'fb', url: '' });

  useEffect(() => {
    fetchTargets();
  }, []);

  useEffect(() => {
    const hasScraping = targets.some(t => t.status === 'scraping');
    if (!hasScraping) return;

    const interval = setInterval(() => {
      fetchTargets();
    }, 2000);

    return () => clearInterval(interval);
  }, [targets]);

  const fetchTargets = async () => {
    try {
      const res = await axios.get(`${API_BASE}/targets`);
      setTargets(res.data);
    } catch (error) {
      console.error('Error fetching targets:', error);
    }
  };

  const addTarget = async (e) => {
    e.preventDefault();
    if (!form.name || !form.url) return;
    try {
      await axios.post(`${API_BASE}/targets`, form);
      setForm({ name: '', platform: 'fb', url: '' });
      fetchTargets();
    } catch (error) {
      console.error('Error adding target:', error);
    }
  };

  const deleteTarget = async (id) => {
    try {
      await axios.delete(`${API_BASE}/targets/${id}`);
      fetchTargets();
    } catch (error) {
      console.error('Error deleting target:', error);
    }
  };

  const triggerScrape = async (id) => {
    try {
      await axios.post(`${API_BASE}/targets/${id}/scrape`);
      fetchTargets();
    } catch (error) {
      console.error('Error triggering scrape:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">追蹤清單管理</h2>
        <p className="text-slate-400 mt-1">管理與新增你需要追蹤的社群帳號</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm h-fit">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
            <Plus className="w-5 h-5 text-emerald-400" />
            新增追蹤目標
          </h3>
          <form onSubmit={addTarget} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-300 mb-1 font-medium">名稱</label>
              <input
                className="w-full bg-slate-900 border border-slate-700 text-white placeholder-slate-500 rounded-lg px-4 py-2 focus:outline-none focus:border-purple-500 transition-colors"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="例如：官方粉絲團"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1 font-medium">平台</label>
              <select
                className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:border-purple-500 transition-colors"
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
              >
                <option value="fb">Facebook</option>
                <option value="ig">Instagram</option>
                <option value="threads">Threads</option>
                <option value="yt">YouTube</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1 font-medium">網址 (URL)</label>
              <input
                className="w-full bg-slate-900 border border-slate-700 text-white placeholder-slate-500 rounded-lg px-4 py-2 focus:outline-none focus:border-purple-500 transition-colors"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                placeholder="https://..."
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-400 hover:to-pink-500 text-white font-semibold py-2.5 rounded-lg shadow-lg shadow-purple-500/20 transition-all"
            >
              新增目標
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-white">現有清單</h3>
            <button onClick={fetchTargets} className="text-slate-400 hover:text-white transition-colors" title="重新整理">
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400 text-sm">
                  <th className="pb-3 px-4 font-medium">平台</th>
                  <th className="pb-3 px-4 font-medium">名稱</th>
                  <th className="pb-3 px-4 font-medium">最新粉絲數</th>
                  <th className="pb-3 px-4 font-medium">狀態</th>
                  <th className="pb-3 px-4 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {targets.map(t => (
                  <tr key={t.id} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                    <td className="py-3 px-4">
                      <span className="uppercase text-xs font-bold text-slate-400 bg-slate-800 px-2 py-1 rounded">
                        {t.platform}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium text-white">{t.name}</td>
                    <td className="py-3 px-4">{t.latest_followers?.toLocaleString() || '--'}</td>
                    <td className="py-3 px-4">
                      {t.status === 'scraping' ? (
                        <span className="text-blue-400 text-sm flex items-center gap-1">
                          <RefreshCw className="w-3 h-3 animate-spin" /> 更新中
                        </span>
                      ) : t.status === 'error' ? (
                        <span className="text-red-400 text-sm">失敗</span>
                      ) : (
                        <span className="text-emerald-400 text-sm">正常</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button 
                        onClick={() => triggerScrape(t.id)}
                        disabled={t.status === 'scraping'}
                        className="p-1.5 text-blue-400 hover:bg-blue-400/10 rounded mr-2"
                        title="手動更新"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => deleteTarget(t.id)}
                        className="p-1.5 text-red-400 hover:bg-red-400/10 rounded"
                        title="刪除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {targets.length === 0 && (
              <div className="text-center py-8 text-slate-500">尚無追蹤目標</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
