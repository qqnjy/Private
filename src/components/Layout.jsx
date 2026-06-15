import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Settings, Activity, CalendarDays, PieChart } from 'lucide-react';

export default function Layout({ children }) {
  const location = useLocation();

    { name: '總覽儀表板', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: '單一帳號分析', path: '/platforms', icon: <Activity size={20} /> },
    { name: '競品分析', path: '/competitors', icon: <PieChart size={20} /> },
    { name: '小編行事曆', path: '/calendar', icon: <CalendarDays size={20} /> },
    { name: '追蹤清單管理', path: '/manage', icon: <Users size={20} /> },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] flex font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-[var(--bg-card)] border-r border-[var(--border-color)] hidden md:flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-black text-[var(--accent)] tracking-tight">
            IGS社群數據觀測站
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1 uppercase tracking-widest font-semibold">Social Media Analytics</p>
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
                    ? 'bg-[var(--bg-base)] text-[var(--accent)] font-bold border border-[var(--border-color)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-base)] hover:text-[var(--text-primary)]'
                }`}
              >
                <div className={`${isActive ? 'text-[var(--accent)]' : 'text-[var(--text-secondary)]'}`}>
                  {item.icon}
                </div>
                {item.name}
              </Link>
            );
          })}
        </nav>
        
        <div className="p-6 border-t border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[var(--accent)] text-[var(--text-primary)] flex items-center justify-center font-bold text-sm">
              I
            </div>
            <div>
              <p className="text-sm font-bold text-[var(--text-primary)]">IGS Admin</p>
              <p className="text-xs text-[var(--text-muted)]">v2.0 Beta</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-[var(--bg-card)] border-b border-[var(--border-color)] p-4 flex items-center justify-between">
          <h1 className="text-xl font-black text-[var(--accent)]">
            IGS社群數據觀測站
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
