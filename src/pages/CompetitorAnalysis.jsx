import React, { useState, useMemo } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { Search, ExternalLink, Filter, TrendingUp, MessageCircle, ThumbsUp, Share2, RefreshCw, X } from 'lucide-react';
import { useEffect } from 'react';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const TAG_COLORS = [
  'bg-red-100 text-red-700',
  'bg-orange-100 text-orange-700',
  'bg-amber-100 text-amber-700',
  'bg-yellow-100 text-yellow-700',
  'bg-lime-100 text-lime-700',
  'bg-green-100 text-green-700',
  'bg-emerald-100 text-emerald-700',
  'bg-teal-100 text-teal-700',
  'bg-cyan-100 text-cyan-700',
  'bg-sky-100 text-sky-700',
  'bg-blue-100 text-blue-700',
  'bg-indigo-100 text-indigo-700',
  'bg-violet-100 text-violet-700',
  'bg-purple-100 text-purple-700',
  'bg-fuchsia-100 text-fuchsia-700',
  'bg-pink-100 text-pink-700',
  'bg-rose-100 text-rose-700',
  'bg-slate-100 text-slate-700',
  'bg-gray-100 text-gray-700',
  'bg-zinc-100 text-zinc-700'
];

// Predefined colors for common tags to avoid collisions
const TAG_COLOR_MAP = {
  '限時活動': 'bg-indigo-100 text-indigo-700',
  '抽獎活動': 'bg-fuchsia-100 text-fuchsia-700',
  '下載推廣': 'bg-sky-100 text-sky-700',
  '課金促銷': 'bg-rose-100 text-rose-700',
  '聯名合作': 'bg-amber-100 text-amber-700',
  '社群互動': 'bg-emerald-100 text-emerald-700',
  '節慶活動': 'bg-orange-100 text-orange-700',
  '節日時事': 'bg-orange-100 text-orange-700',
  '短影片': 'bg-red-100 text-red-700',
  '改版更新': 'bg-teal-100 text-teal-700',
  '系統公告': 'bg-slate-100 text-slate-700'
};

const BRAND_COLORS = {
  '包你發': '#5d7a8c',
  '星城': '#8a9fae',
  '老子有錢': '#d2a154',
  '預設': '#897bb8'
};

const CompetitorAnalysis = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('All');
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });
  const [isUpdating, setIsUpdating] = useState(false);
  const [dateRangeType, setDateRangeType] = useState('30');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [competitorData, setCompetitorData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [videoFilter, setVideoFilter] = useState('All'); // 'All', 'ShortVideo', 'Normal'
  const [selectedTags, setSelectedTags] = useState([]);

  // Dynamically assign unique colors to all tags that are not in the predefined map
  const dynamicTagColorMap = useMemo(() => {
    const map = { ...TAG_COLOR_MAP };
    let colorIndex = 0;
    
    const allTags = new Set();
    competitorData.forEach(item => {
      if (item.tags) {
        item.tags.forEach(tag => allTags.add(tag));
      }
    });

    Array.from(allTags).forEach(tag => {
      if (!map[tag]) {
        map[tag] = TAG_COLORS[colorIndex % TAG_COLORS.length];
        colorIndex++;
      }
    });
    
    return map;
  }, [competitorData]);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  const fetchCompetitorsData = async () => {
    try {
      // Use full URL if backend is running on different port in dev
      const res = await fetch(`${API_BASE}/competitors`);
      if (res.ok) {
        const data = await res.json();
        setCompetitorData(data);
      }
    } catch (e) {
      console.error('Failed to fetch competitors data', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCompetitorsData();
  }, []);

  const handleUpdate = async () => {
    try {
      setIsUpdating(true);
      const res = await fetch(`${API_BASE}/competitors/fetch`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        alert('資料更新成功！畫面已同步為最新資料。');
        await fetchCompetitorsData();
      } else {
        alert('更新失敗：' + data.detail);
      }
    } catch (err) {
      alert('更新發生錯誤，請稍後再試。');
    } finally {
      setIsUpdating(false);
    }
  };

  const brands = ['All', ...new Set(competitorData.map(item => item.brand))];

  // Filter and sort logic
  const filteredData = useMemo(() => {
    let result = [...competitorData];

    // Date Range Filter
    const today = new Date();
    let filterStart = null;
    let filterEnd = null;

    if (dateRangeType === 'custom') {
      if (startDate) filterStart = new Date(startDate);
      if (endDate) {
        filterEnd = new Date(endDate);
        filterEnd.setHours(23, 59, 59, 999);
      }
    } else if (dateRangeType === 'this_year') {
      filterStart = new Date(today.getFullYear(), 0, 1);
    } else if (dateRangeType === 'all') {
      filterStart = null;
    } else {
      const days = parseInt(dateRangeType, 10);
      if (!isNaN(days)) {
        filterStart = new Date();
        filterStart.setDate(today.getDate() - days);
      }
    }

    if (filterStart || filterEnd) {
      result = result.filter(item => {
        const itemDate = new Date(item.post_date);
        if (filterStart && itemDate < filterStart) return false;
        if (filterEnd && itemDate > filterEnd) return false;
        return true;
      });
    }
    
    if (selectedBrand !== 'All') {
      result = result.filter(item => item.brand === selectedBrand);
    }
    
    if (searchTerm) {
      const lowerSearch = searchTerm.toLowerCase();
      result = result.filter(item => 
        item.content.toLowerCase().includes(lowerSearch) ||
        item.tags.some(tag => tag.toLowerCase().includes(lowerSearch))
      );
    }

    if (videoFilter === 'ShortVideo') {
      result = result.filter(item => item.tags.includes('短影片'));
    } else if (videoFilter === 'Normal') {
      result = result.filter(item => !item.tags.includes('短影片'));
    }

    if (selectedTags.length > 0) {
      result = result.filter(item => 
        selectedTags.every(tag => item.tags.includes(tag))
      );
    }

    result.sort((a, b) => {
      if (a[sortConfig.key] < b[sortConfig.key]) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (a[sortConfig.key] > b[sortConfig.key]) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });

    return result;
  }, [searchTerm, selectedBrand, sortConfig, dateRangeType, startDate, endDate, competitorData, videoFilter, selectedTags]);

  const requestSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  const toggleTag = (tag) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  // Aggregation for Charts
  const brandStats = useMemo(() => {
    const stats = {};
    filteredData.forEach(item => {
      if (!stats[item.brand]) {
        stats[item.brand] = { name: item.brand, posts: 0, likes: 0, comments: 0, shares: 0, engagement: 0 };
      }
      stats[item.brand].posts += 1;
      stats[item.brand].likes += item.likes;
      stats[item.brand].comments += item.comments;
      stats[item.brand].shares += item.shares;
      stats[item.brand].engagement += item.engagement;
    });
    return Object.values(stats);
  }, [filteredData]);

  const tagStats = useMemo(() => {
    const stats = {};
    filteredData.forEach(item => {
      item.tags.forEach(tag => {
        if (!stats[tag]) {
          stats[tag] = { name: tag, count: 0, totalEngagement: 0 };
        }
        stats[tag].count += 1;
        stats[tag].totalEngagement += item.engagement;
      });
    });

    return Object.values(stats)
      .map(t => ({
        ...t,
        avgEngagement: Math.round(t.totalEngagement / t.count)
      }))
      .sort((a, b) => b.avgEngagement - a.avgEngagement)
      .slice(0, 10); // Top 10 tags
  }, [filteredData]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] p-4 rounded-xl shadow-2xl">
          <p className="text-[var(--text-primary)] font-medium mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {entry.name}: {entry.value.toLocaleString()}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">
            競品分析觀測站
          </h1>
          <p className="text-[var(--text-secondary)] mt-1">追蹤各品牌社群發文策略與互動成效</p>
        </div>
        <button
          onClick={handleUpdate}
          disabled={isUpdating}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            isUpdating 
              ? 'bg-[var(--border-color)] text-[var(--text-primary)] cursor-not-allowed' 
              : 'bg-[var(--accent)] hover:opacity-90 text-white shadow-sm'
          }`}
        >
          <RefreshCw size={18} className={isUpdating ? 'animate-spin' : ''} />
          {isUpdating ? '正在從 Google Sheet 抓取最新資料...' : '同步最新資料'}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] p-6 rounded-2xl ">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#5d7a8c]/10 text-[#5d7a8c] flex items-center justify-center">
              <MessageCircle size={24} />
            </div>
            <div>
              <p className="text-[var(--text-secondary)] text-sm">總貼文數</p>
              <h3 className="text-2xl font-bold text-[var(--text-primary)]">{filteredData.length}</h3>
            </div>
          </div>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] p-6 rounded-2xl ">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#8a9fae]/10 text-[#8a9fae] flex items-center justify-center">
              <TrendingUp size={24} />
            </div>
            <div>
              <p className="text-[var(--text-secondary)] text-sm">總互動量</p>
              <h3 className="text-2xl font-bold text-[var(--text-primary)]">
                {brandStats.reduce((sum, b) => sum + b.engagement, 0).toLocaleString()}
              </h3>
            </div>
          </div>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] p-6 rounded-2xl ">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#79a69e]/10 text-[#79a69e] flex items-center justify-center">
              <ThumbsUp size={24} />
            </div>
            <div>
              <p className="text-[var(--text-secondary)] text-sm">總按讚數</p>
              <h3 className="text-2xl font-bold text-[var(--text-primary)]">
                {brandStats.reduce((sum, b) => sum + b.likes, 0).toLocaleString()}
              </h3>
            </div>
          </div>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] p-6 rounded-2xl ">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#d2a154]/10 text-[#d2a154] flex items-center justify-center">
              <Share2 size={24} />
            </div>
            <div>
              <p className="text-[var(--text-secondary)] text-sm">總分享數</p>
              <h3 className="text-2xl font-bold text-[var(--text-primary)]">
                {brandStats.reduce((sum, b) => sum + b.shares, 0).toLocaleString()}
              </h3>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Brand Comparison Chart */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 ">
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-6 flex items-center gap-2">
            各品牌總互動對比
          </h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={brandStats} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Bar dataKey="likes" name="按讚" stackId="a" fill="#5d7a8c" radius={[0, 0, 4, 4]} />
                <Bar dataKey="comments" name="留言" stackId="a" fill="#b0c4de" />
                <Bar dataKey="shares" name="分享" stackId="a" fill="#8a9fae" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tag Performance Chart */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 ">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
              熱門標籤平均互動率 (Top 10)
            </h2>
            {selectedBrand !== 'All' && (
              <span className="text-xs font-medium px-2 py-1 bg-[#5d7a8c]/10 text-[#5d7a8c] rounded-lg">
                {selectedBrand}
              </span>
            )}
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tagStats} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={false} />
                <XAxis type="number" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                <YAxis dataKey="name" type="category" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} width={80} />
                <RechartsTooltip content={<CustomTooltip />} />
                <Bar dataKey="avgEngagement" name="平均互動數" fill="#5d7a8c" radius={[0, 4, 4, 0]}>
                  {tagStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Data Table Section */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 ">
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 gap-4">
          <h2 className="text-xl font-bold text-[var(--text-primary)]">競品貼文總覽</h2>
          <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto">
            {/* Date Range Filter */}
            <div className="flex items-center gap-2 text-sm w-full md:w-auto">
              <select
                value={dateRangeType}
                onChange={(e) => setDateRangeType(e.target.value)}
                className="bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 appearance-none min-w-[120px]"
              >
                <option value="7">過去 7 天</option>
                <option value="30">過去 30 天</option>
                <option value="90">過去 90 天</option>
                <option value="this_year">今年</option>
                <option value="all">所有時間</option>
                <option value="custom">自訂</option>
              </select>

              {dateRangeType === 'custom' && (
                <>
                  <input 
                    type="date" 
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[var(--text-secondary)]">至</span>
                  <input 
                    type="date" 
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
                  />
                </>
              )}
            </div>

            {/* Brand Filter */}
            <div className="relative flex-1 md:w-48">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" size={18} />
              <select
                className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:border-indigo-500 appearance-none"
                value={selectedBrand}
                onChange={(e) => setSelectedBrand(e.target.value)}
              >
                {brands.map(brand => (
                  <option key={brand} value={brand}>{brand === 'All' ? '所有品牌' : brand}</option>
                ))}
              </select>
            </div>

            {/* Video Filter */}
            <div className="relative flex-1 md:w-32">
              <select
                className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl px-4 py-2.5 focus:outline-none focus:border-indigo-500 appearance-none"
                value={videoFilter}
                onChange={(e) => setVideoFilter(e.target.value)}
              >
                <option value="All">所有類型</option>
                <option value="ShortVideo">僅短影音</option>
                <option value="Normal">一般貼文</option>
              </select>
            </div>
            
            {/* Search */}
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" size={18} />
              <input
                type="text"
                placeholder="搜尋貼文內容或標籤..."
                className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:border-indigo-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>

        {selectedTags.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-sm text-[var(--text-secondary)] font-medium">已選標籤：</span>
            {selectedTags.map(tag => (
              <span 
                key={tag} 
                className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-full shadow-sm ${dynamicTagColorMap[tag] || 'bg-gray-100 text-gray-700'}`}
              >
                {tag}
                <button 
                  onClick={() => toggleTag(tag)}
                  className="hover:bg-black/20 dark:hover:bg-white/20 rounded-full p-0.5 transition-colors"
                >
                  <X size={14} />
                </button>
              </span>
            ))}
            <button 
              onClick={() => setSelectedTags([])}
              className="text-xs text-[var(--text-secondary)] hover:text-indigo-500 font-medium ml-1 px-2 py-1 transition-colors"
            >
              清除全部
            </button>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)] text-sm">
                <th className="pb-3 font-medium px-4 whitespace-nowrap">品牌</th>
                <th className="pb-3 font-medium px-4 whitespace-nowrap cursor-pointer hover:text-indigo-400" onClick={() => requestSort('post_date')}>發文日期 {sortConfig.key === 'post_date' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
                <th className="pb-3 font-medium px-4 w-1/3">貼文內容 (前60字)</th>
                <th className="pb-3 font-medium px-4">標籤</th>
                <th className="pb-3 font-medium px-4 whitespace-nowrap text-right cursor-pointer hover:text-indigo-400" onClick={() => requestSort('engagement')}>總互動 {sortConfig.key === 'engagement' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
                <th className="pb-3 font-medium px-4 whitespace-nowrap text-right cursor-pointer hover:text-indigo-400" onClick={() => requestSort('likes')}>讚 {sortConfig.key === 'likes' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
                <th className="pb-3 font-medium px-4 whitespace-nowrap text-right cursor-pointer hover:text-indigo-400" onClick={() => requestSort('comments')}>留言 {sortConfig.key === 'comments' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
                <th className="pb-3 font-medium px-4 whitespace-nowrap text-center">連結</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {filteredData.map((item, index) => (
                <tr key={index} className="hover:bg-[var(--bg-base)] transition-colors group">
                  <td className="py-4 px-4 whitespace-nowrap">
                    <span className="font-medium" style={{ color: BRAND_COLORS[item.brand] || BRAND_COLORS['預設'] }}>
                      {item.brand}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-sm text-[var(--text-secondary)] whitespace-nowrap">
                    {new Date(item.post_date).toLocaleDateString()}
                  </td>
                  <td className="py-4 px-4 text-sm text-[var(--text-secondary)] max-w-xs truncate" title={item.content}>
                    {item.content.substring(0, 60)}{item.content.length > 60 ? '...' : ''}
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex flex-wrap gap-1">
                      {item.tags.map((tag, i) => (
                        <span 
                          key={i} 
                          onClick={() => toggleTag(tag)}
                          className={`text-xs px-2 py-0.5 rounded-full cursor-pointer hover:opacity-80 transition-all ${selectedTags.includes(tag) ? 'ring-2 ring-indigo-400 ring-offset-1 dark:ring-offset-[#1e1e2d]' : ''} ${dynamicTagColorMap[tag] || 'bg-gray-100 text-gray-700'}`}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right text-indigo-400 font-semibold whitespace-nowrap">{item.engagement.toLocaleString()}</td>
                  <td className="py-4 px-4 text-right text-[var(--text-secondary)] whitespace-nowrap">{item.likes.toLocaleString()}</td>
                  <td className="py-4 px-4 text-right text-[var(--text-secondary)] whitespace-nowrap">{item.comments.toLocaleString()}</td>
                  <td className="py-4 px-4 text-center whitespace-nowrap">
                    <a href={item.url} target="_blank" rel="noopener noreferrer" className="inline-block p-2 text-[var(--text-secondary)] hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors">
                      <ExternalLink size={18} />
                    </a>
                  </td>
                </tr>
              ))}
              {filteredData.length === 0 && (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-[var(--text-muted)]">
                    找不到符合條件的貼文
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CompetitorAnalysis;
