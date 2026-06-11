import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area
} from 'recharts';
import { Users, TrendingUp, Activity, Globe, Camera, Video, Hash, Download } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const COLORS = {
  fb: '#3b5998',
  ig: '#e1306c',
  threads: '#000000',
  yt: '#ff0000',
  primary: '#c084fc',
  secondary: '#38bdf8'
};

const PLATFORM_ICONS = {
  fb: <Globe size={18} />,
  ig: <Camera size={18} />,
  yt: <Video size={18} />,
  threads: <Hash size={18} />
};

export default function Dashboard() {
  const [targets, setTargets] = useState([]);
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState('');
  
  const [summary, setSummary] = useState({ total_followers: 0, platform_stats: {} });
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlatformChart, setSelectedPlatformChart] = useState('fb');
  const [dateRangeType, setDateRangeType] = useState('30');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // 初次載入目標列表以取得所有遊戲
  useEffect(() => {
    const fetchTargets = async () => {
      try {
        const res = await axios.get(`${API_BASE}/targets`);
        const data = res.data || [];
        setTargets(data);
        
        // 利用名稱推導出遊戲名稱，將「粉絲團」、「_IG」等字眼去除
        const uniqueGames = [...new Set(data.map(t => {
          return (t?.name || '').replace('粉絲團', '').replace('_IG', '').trim();
        }).filter(Boolean))];
        
        setGames(uniqueGames);
        if (uniqueGames.length > 0) {
          setSelectedGame(uniqueGames[0]);
        } else {
          setLoading(false);
        }
      } catch (err) {
        console.error("Fetch targets error", err);
        setLoading(false);
      }
    };
    fetchTargets();
  }, []);

  // 當選擇的遊戲改變時，載入該遊戲的數據
  useEffect(() => {
    if (!selectedGame || targets.length === 0) return;

    const gameTargets = targets.filter(t => {
      const n = (t?.name || '').replace('粉絲團', '').replace('_IG', '').trim();
      return n === selectedGame;
    });
    const targetIds = gameTargets.map(t => t.id).join(',');

    const fetchData = async () => {
      setLoading(true);
      try {
        let trendUrl = `${API_BASE}/stats/trend?target_ids=${targetIds}`;
        if (dateRangeType === 'custom') {
          if (startDate) trendUrl += `&start_date=${startDate}`;
          if (endDate) trendUrl += `&end_date=${endDate}`;
        } else if (dateRangeType === 'this_year') {
          const currentYear = new Date().getFullYear();
          const startYear = Math.max(2025, currentYear);
          trendUrl += `&start_date=${startYear}-01-01`;
        } else if (dateRangeType === 'all') {
          trendUrl += `&start_date=2025-01-01`;
        } else {
          trendUrl += `&days=${dateRangeType}`;
        }

        const [sumRes, trendRes] = await Promise.all([
          axios.get(`${API_BASE}/stats/summary?target_ids=${targetIds}`),
          axios.get(trendUrl)
        ]);
        setSummary(sumRes.data || { total_followers: 0, platform_stats: {} });
        
        // 計算每日增量 (diff)
        const rawTrend = trendRes.data || [];
        const processedTrendData = rawTrend.map((item, index, arr) => {
          const prevItem = index > 0 ? arr[index - 1] : null;
          return {
            ...item,
            fb_diff: prevItem && item.fb != null && prevItem.fb != null ? item.fb - prevItem.fb : 0,
            ig_diff: prevItem && item.ig != null && prevItem.ig != null ? item.ig - prevItem.ig : 0,
            threads_diff: prevItem && item.threads != null && prevItem.threads != null ? item.threads - prevItem.threads : 0,
            yt_diff: prevItem && item.yt != null && prevItem.yt != null ? item.yt - prevItem.yt : 0,
          };
        });
        setTrendData(processedTrendData);
      } catch (err) {
        console.error("Fetch stats error", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedGame, targets, startDate, endDate, dateRangeType]);

  if (loading && games.length === 0) {
    return <div className="animate-pulse flex space-x-4 p-8 text-slate-400">載入數據中...</div>;
  }

  const safePlatformStats = summary?.platform_stats || {};

  // Prepare Pie Chart Data
  const pieData = Object.keys(safePlatformStats).map(key => ({
    name: key.toUpperCase(),
    value: safePlatformStats[key] || 0,
    color: COLORS[key] || COLORS.primary
  }));

  // Helper to format large numbers
  const formatNum = (num) => {
    if (typeof num !== 'number') return num;
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num;
  };

  const exportCSV = () => {
    if (!trendData || trendData.length === 0) {
      alert("沒有可匯出的數據");
      return;
    }

    const headers = ["日期", "總數", "FB", "FB增減", "IG", "IG增減", "Threads", "Threads增減", "YT", "YT增減"];
    const csvRows = [headers.join(',')];

    for (const row of trendData) {
      const values = [
        row.date,
        row.total || 0,
        row.fb || 0,
        row.fb_diff || 0,
        row.ig || 0,
        row.ig_diff || 0,
        row.threads || 0,
        row.threads_diff || 0,
        row.yt || 0,
        row.yt_diff || 0
      ];
      csvRows.push(values.join(','));
    }

    // Add BOM for Excel UTF-8 compatibility
    const blob = new Blob(["\uFEFF" + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${selectedGame}_數據_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Custom Tooltip function to show daily diff
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const key = selectedPlatformChart;
      const value = data[key];
      const diff = data[`${key}_diff`];
      
      return (
        <div className="bg-slate-800 border border-slate-700 p-3 rounded-lg shadow-xl">
          <p className="text-slate-300 font-bold mb-2">{label}</p>
          <p className="text-white mb-1" style={{ color: COLORS[key] || COLORS.primary }}>
            <span className="uppercase font-bold">{key} : </span> 
            <span className="font-bold">{(value || 0).toLocaleString()}</span>
          </p>
          {diff !== undefined && diff !== 0 && (
            <p className={`text-sm font-bold flex items-center gap-1 ${diff > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {diff > 0 ? '▲' : '▼'} {Math.abs(diff).toLocaleString()} <span className="text-slate-500 font-normal text-xs ml-1">(較昨日)</span>
            </p>
          )}
          {diff === 0 && (
            <p className="text-sm font-bold text-slate-500 flex items-center gap-1">
              - 0 <span className="font-normal text-xs ml-1">(無增減)</span>
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-white">總覽儀表板</h2>
          <p className="text-slate-400 mt-1">依照不同遊戲分開呈現數據表現</p>
        </div>
        <button
          onClick={exportCSV}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold transition-all shadow-lg shadow-emerald-600/20"
        >
          <Download size={18} />
          匯出 CSV
        </button>
      </div>

      {/* 遊戲分頁 Tabs */}
      {games.length > 0 && (
        <div className="flex flex-wrap gap-2 border-b border-slate-700/50 pb-4">
          {games.map(game => (
            <button
              key={game}
              onClick={() => setSelectedGame(game)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                selectedGame === game 
                  ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/30' 
                  : 'bg-slate-800/60 text-slate-400 hover:bg-slate-700/60 hover:text-white'
              }`}
            >
              {game}
            </button>
          ))}
        </div>
      )}

      {loading && games.length > 0 ? (
        <div className="animate-pulse flex space-x-4 p-8 text-slate-400">載入遊戲數據中...</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 relative overflow-hidden backdrop-blur-sm">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <Users size={64} />
              </div>
              <p className="text-slate-400 text-sm font-medium mb-1">{selectedGame} 總粉絲數</p>
              <h3 className="text-4xl font-black text-white">{(summary?.total_followers || 0).toLocaleString()}</h3>
            </div>

            {Object.entries(safePlatformStats).map(([platform, count]) => {
              const platformTarget = targets.find(t => 
                t.platform === platform && 
                (t.name || '').replace('粉絲團', '').replace('_IG', '').trim() === selectedGame
              );
              
              return (
                <div key={platform} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm flex items-center justify-between group">
                  <div>
                    <p className="text-slate-400 text-sm font-medium mb-1 flex items-center gap-2 uppercase">
                      <span style={{color: COLORS[platform]}}>{PLATFORM_ICONS[platform]}</span>
                      {platform} 總數
                    </p>
                    <h3 className="text-2xl font-bold text-white">{(count || 0).toLocaleString()}</h3>
                  </div>
                  {platformTarget?.url && (
                    <a 
                      href={platformTarget.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-purple-400 transition-colors opacity-0 group-hover:opacity-100 p-2"
                      title={`前往 ${platformTarget.name}`}
                    >
                      <Globe size={20} />
                    </a>
                  )}
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Trend Chart */}
            <div className="lg:col-span-2 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm flex flex-col">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <TrendingUp size={20} className="text-purple-400" />
                  平台趨勢
                </h3>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2 text-sm">
                    <select
                      value={dateRangeType}
                      onChange={(e) => setDateRangeType(e.target.value)}
                      className="bg-slate-900 border border-slate-700 text-white rounded p-1.5 focus:outline-none focus:border-purple-500"
                    >
                      <option value="7">過去 7 天</option>
                      <option value="30">過去 30 天</option>
                      <option value="90">過去 90 天</option>
                      <option value="this_year">今年</option>
                      <option value="all">所有時間 (2025起)</option>
                      <option value="custom">自訂</option>
                    </select>

                    {dateRangeType === 'custom' && (
                      <>
                        <input 
                          type="date" 
                          min="2025-01-01"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          className="bg-slate-900 border border-slate-700 text-white rounded p-1.5 focus:outline-none focus:border-purple-500"
                        />
                        <span className="text-slate-400">至</span>
                        <input 
                          type="date" 
                          min="2025-01-01"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          className="bg-slate-900 border border-slate-700 text-white rounded p-1.5 focus:outline-none focus:border-purple-500"
                        />
                      </>
                    )}
                  </div>
                  <div className="flex bg-slate-900/50 p-1 rounded-lg border border-slate-700/50">
                    {['fb', 'ig', 'threads', 'yt'].map(p => (
                      <button
                        key={p}
                        onClick={() => setSelectedPlatformChart(p)}
                        className={`px-3 py-1.5 rounded-md text-sm font-bold uppercase transition-all ${
                          selectedPlatformChart === p 
                            ? 'bg-slate-700 text-white shadow-sm' 
                            : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="h-[350px] flex-1">
                {trendData && trendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="date" stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} tickMargin={10} minTickGap={20} />
                      <YAxis stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} tickFormatter={formatNum} domain={['dataMin', 'dataMax']} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line 
                        type="monotone" 
                        dataKey={selectedPlatformChart} 
                        name={selectedPlatformChart} 
                        stroke={COLORS[selectedPlatformChart] || COLORS.primary} 
                        strokeWidth={3} 
                        dot={false} 
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500">尚無足夠數據</div>
                )}
              </div>
            </div>

            {/* Platform Share Pie Chart */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm">
              <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                <Activity size={20} className="text-pink-400" />
                平台佔比分析
              </h3>
              <div className="h-[300px]">
                {pieData && pieData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                        itemStyle={{ fontWeight: 'bold' }}
                      />
                      <Legend verticalAlign="bottom" height={36}/>
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500">尚無足夠數據</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
