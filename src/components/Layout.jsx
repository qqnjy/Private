import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Settings, Activity } from 'lucide-react';

export default function Layout({ children }) {
  const location = useLocation();

  const navItems = [
    { name: '總覽儀表板', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: '單一帳號分析', path: '/platforms', icon: <Activity size={20} /> },
    { name: '追蹤清單管理', path: '/manage', icon: <Users size={20} /> },
    { name: '系統設定', path: '/settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex font-sans dark">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-800/50 border-r border-slate-700/50 hidden md:flex flex-col backdrop-blur-xl">
        <div className="p-6">
          <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-500 tracking-tight">
            IGS 數據觀測站
          </h1>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-widest font-semibold">Social Media Analytics</p>
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-purple-500/10 text-purple-400 font-medium'
                    : 'text-slate-400 hover:bg-slate-700/30 hover:text-slate-200'
                }`}
              >
                <div className={`${isActive ? 'text-purple-400' : 'text-slate-500'}`}>
                  {item.icon}
                </div>
                {item.name}
              </Link>
            );
          })}
        </nav>
        
        <div className="p-6 border-t border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-pink-500 flex items-center justify-center font-bold text-sm">
              I
            </div>
            <div>
              <p className="text-sm font-medium">IGS Admin</p>
              <p className="text-xs text-slate-500">v2.0 Beta</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-slate-800/80 backdrop-blur-md border-b border-slate-700 p-4 flex items-center justify-between">
          <h1 className="text-xl font-black bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-500">
            IGS 數據觀測站
          </h1>
        </header>

        <div className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
