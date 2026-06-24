import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import React, { useState, useEffect } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import PlatformAnalysis from './pages/PlatformAnalysis';
import ManageList from './pages/ManageList';
import Calendar from './pages/Calendar';
import CompetitorAnalysis from './pages/CompetitorAnalysis';
import AiReporter from './pages/AiReporter';
import WeeklyPosts from './pages/WeeklyPosts';
import { Eye, EyeOff } from 'lucide-react';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (localStorage.getItem('site_auth') === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === 'igs2026win') {
      localStorage.setItem('site_auth', 'true');
      setIsAuthenticated(true);
    } else {
      alert('密碼錯誤！');
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center p-4 font-sans">
        <form onSubmit={handleLogin} className="bg-[var(--bg-card)] p-8 rounded-2xl border border-[var(--border-color)] shadow-xl w-full max-w-sm flex flex-col gap-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-black text-[var(--accent)] tracking-tight">IGS社群數據觀測站</h1>
            <p className="text-sm text-[var(--text-muted)] font-semibold uppercase tracking-widest">請輸入密碼以進入系統</p>
          </div>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="請輸入密碼"
              className="w-full px-4 py-3 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)] transition"
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition focus:outline-none"
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
          <button
            type="submit"
            className="w-full py-3 bg-[var(--accent)] hover:opacity-90 text-[var(--bg-base)] rounded-xl font-bold transition"
          >
            登入
          </button>
        </form>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/platforms" element={<PlatformAnalysis />} />
          <Route path="/competitors" element={<CompetitorAnalysis />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/manage" element={<ManageList />} />
          <Route path="/report" element={<AiReporter />} />
          <Route path="/posts" element={<WeeklyPosts />} />
          <Route path="/settings" element={<div className="text-white p-8">系統設定開發中...</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
