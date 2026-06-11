import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const COLORS = [
  '#c084fc', '#38bdf8', '#34d399', '#fbbf24', '#f87171', '#a78bfa'
];

export default function PlatformAnalysis() {
  const [targets, setTargets] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTargets();
  }, []);

  const fetchTargets = async () => {
    try {
      const res = await axios.get(`${API_BASE}/targets`);
      setTargets(res.data);
      // Auto select first target if available
      if (res.data.length > 0 && selectedIds.length === 0) {
        setSelectedIds([res.data[0].id]);
      }
    } catch (error) {
      console.error('Error fetching targets:', error);
    }
  };

  useEffect(() => {
    if (selectedIds.length > 0) {
      fetchHistory();
    } else {
      setChartData([]);
    }
  }, [selectedIds]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      // Fetch history for all selected targets
      const promises = selectedIds.map(id => axios.get(`${API_BASE}/targets/${id}/history`));
      const results = await Promise.all(promises);
      
      // Process into a combined timeseries format for Recharts
      // format: { date: 'YYYY-MM-DD', 'target1_name': 1234, 'target2_name': 5678 }
      const combined = {};
      
      results.forEach((res, index) => {
        const targetId = selectedIds[index];
        const target = targets.find(t => t.id === targetId);
        if (!target) return;
        
        res.data.forEach(record => {
          const d = new Date(record.scraped_at).toLocaleDateString();
          if (!combined[d]) combined[d] = { date: d };
          combined[d][target.name] = record.followers;
        });
      });
      
      // Sort chronologically
      const sorted = Object.values(combined).sort((a, b) => new Date(a.date) - new Date(b.date));
      setChartData(sorted);
      
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelection = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) 
        ? prev.filter(x => x !== id)
        : [...prev, id]
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">單一帳號分析與競品比較</h2>
        <p className="text-slate-400 mt-1">勾選多個帳號可進行疊加比較</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Selection Sidebar */}
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4 backdrop-blur-sm max-h-[600px] overflow-y-auto">
          <h3 className="font-bold text-white mb-4">選擇分析目標</h3>
          <div className="space-y-2">
            {targets.map(t => (
              <label key={t.id} className="flex items-center gap-3 p-2 rounded hover:bg-slate-700/50 cursor-pointer transition-colors">
                <input 
                  type="checkbox" 
                  checked={selectedIds.includes(t.id)}
                  onChange={() => toggleSelection(t.id)}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-purple-500 focus:ring-purple-500 focus:ring-offset-slate-900"
                />
                <span className="text-sm text-slate-300 flex-1 truncate">{t.name}</span>
                <span className="text-xs text-slate-500 uppercase">{t.platform}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Chart Area */}
        <div className="lg:col-span-3 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm flex flex-col min-h-[500px]">
          {loading ? (
            <div className="flex-1 flex items-center justify-center text-slate-400">載入數據中...</div>
          ) : chartData.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-slate-500">請從左側選擇要分析的目標，或目前尚無數據</div>
          ) : (
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} tickMargin={10} />
                  <YAxis stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} 
                         domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    itemStyle={{ fontWeight: 'medium' }}
                  />
                  <Legend verticalAlign="bottom" height={36}/>
                  
                  {/* Create a line for each selected target that exists in data */}
                  {selectedIds.map((id, index) => {
                    const target = targets.find(t => t.id === id);
                    if (!target) return null;
                    return (
                      <Line 
                        key={target.name}
                        type="monotone" 
                        dataKey={target.name} 
                        name={target.name}
                        stroke={COLORS[index % COLORS.length]} 
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                        connectNulls={true}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
