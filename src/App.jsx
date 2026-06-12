import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import PlatformAnalysis from './pages/PlatformAnalysis';
import ManageList from './pages/ManageList';
import Calendar from './pages/Calendar';
import CompetitorAnalysis from './pages/CompetitorAnalysis';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/platforms" element={<PlatformAnalysis />} />
          <Route path="/competitors" element={<CompetitorAnalysis />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/manage" element={<ManageList />} />
          <Route path="/settings" element={<div className="text-white p-8">系統設定開發中...</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
