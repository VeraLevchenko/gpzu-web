import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import LoginForm from './components/Auth/LoginForm';
import Home from './pages/Home';
import GP from './pages/GP';
import KaitenFlow from './components/GP/KaitenFlow';
import MidMifFlow from './components/GP/MidMifFlow';
import TuFlow from './components/GP/TuFlow';
import GpFlow from './components/GP/GpFlow';
import RefusalFlow from './components/GP/RefusalFlow';  // ← НОВОЕ
import { authApi } from './services/api';

const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  useEffect(() => {
    const checkAuth = async () => {
      const auth = localStorage.getItem('auth');
      if (!auth) { setIsAuthenticated(false); return; }
      try { await authApi.checkAuth(); setIsAuthenticated(true); }
      catch (error) { localStorage.removeItem('auth'); setIsAuthenticated(false); }
    };
    checkAuth();
  }, []);
  if (isAuthenticated === null) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>Загрузка...</div>;
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/gp" element={<ProtectedRoute><GP /></ProtectedRoute>} />
          <Route path="/gp/kaiten" element={<ProtectedRoute><KaitenFlow /></ProtectedRoute>} />
          <Route path="/gp/midmif" element={<ProtectedRoute><MidMifFlow /></ProtectedRoute>} />
          <Route path="/gp/tu" element={<ProtectedRoute><TuFlow /></ProtectedRoute>} />
          <Route path="/gp/gradplan" element={<ProtectedRoute><GpFlow /></ProtectedRoute>} />
          <Route path="/gp/refusal" element={<ProtectedRoute><RefusalFlow /></ProtectedRoute>} />  {/* ← НОВОЕ */}
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;