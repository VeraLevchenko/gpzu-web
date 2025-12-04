#!/bin/bash
echo "🚀 Создание всех компонентов Frontend..."
cd ~/gpzu-web/frontend

# ========== .env ==========
cat > .env << 'EOF'
REACT_APP_API_URL=http://localhost:8000
EOF
echo "✅ .env"

# ========== src/services/api.js ==========
mkdir -p src/services
cat > src/services/api.js << 'EOF'
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const auth = localStorage.getItem('auth');
  if (auth) {
    const { username, password } = JSON.parse(auth);
    config.auth = { username, password };
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

export const kaitenApi = {
  parseApplication: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/gp/kaiten/parse-application', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  createTask: (data) => api.post('/api/gp/kaiten/create-task', data),
};

export const authApi = {
  checkAuth: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout'),
};
EOF
echo "✅ api.js"

# ========== LoginForm ==========
mkdir -p src/components/Auth
cat > src/components/Auth/LoginForm.jsx << 'EOF'
import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../../services/api';
import './LoginForm.css';

const LoginForm = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      localStorage.setItem('auth', JSON.stringify({ username: values.username, password: values.password }));
      await authApi.checkAuth();
      message.success('Вход выполнен успешно');
      navigate('/');
    } catch (error) {
      message.error('Неверные учётные данные');
      localStorage.removeItem('auth');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card" title={<div className="login-title"><h2>ГПЗУ Web</h2><p>Система выдачи градостроительных планов</p></div>}>
        <Form name="login" onFinish={onFinish} autoComplete="off" size="large">
          <Form.Item name="username" rules={[{ required: true, message: 'Введите логин' }]}>
            <Input prefix={<UserOutlined />} placeholder="Логин" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: 'Введите пароль' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>Войти в систему</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default LoginForm;
EOF

cat > src/components/Auth/LoginForm.css << 'EOF'
.login-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
.login-card { width: 100%; max-width: 420px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
.login-card .ant-card-head { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px 16px 0 0; border-bottom: none; }
.login-title { text-align: center; color: white; }
.login-title h2 { color: white; margin: 0; font-size: 2rem; font-weight: 700; }
.login-title p { color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 0.95rem; }
.login-card .ant-card-body { padding: 32px; }
.login-card .ant-btn-primary { height: 48px; font-size: 1.05rem; font-weight: 600; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
.login-card .ant-btn-primary:hover { background: linear-gradient(135deg, #5568d3 0%, #6a3f94 100%); }
EOF
echo "✅ LoginForm"

# ========== Home Page ==========
mkdir -p src/pages
cat > src/pages/Home.jsx << 'EOF'
import React from 'react';
import { Card, Row, Col } from 'antd';
import { FileTextOutlined, LogoutOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/api';
import './Home.css';

const Home = () => {
  const navigate = useNavigate();
  const handleLogout = async () => {
    try { await authApi.logout(); } catch (error) { console.log('Logout error:', error); }
    finally { localStorage.removeItem('auth'); navigate('/login'); }
  };

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>Автоматизированная система выдачи документов</h1>
        <button className="logout-btn" onClick={handleLogout}><LogoutOutlined /> Выйти</button>
      </div>
      <Row gutter={[32, 32]} justify="center" style={{ marginTop: 60 }}>
        <Col xs={24} sm={12} lg={8}>
          <Card hoverable className="module-card" onClick={() => navigate('/gp')}>
            <div className="card-cover gradplan-cover"><FileTextOutlined className="card-icon" /></div>
            <div className="card-content">
              <h2>Градостроительные планы</h2>
              <p>Подготовка и выдача ГПЗУ: создание задач, генерация документов, пространственный анализ</p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Home;
EOF

cat > src/pages/Home.css << 'EOF'
.home-container { min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 40px 20px; }
.home-header { display: flex; justify-content: space-between; align-items: center; max-width: 1400px; margin: 0 auto 20px; flex-wrap: wrap; gap: 20px; }
.home-header h1 { font-size: 2rem; font-weight: 700; color: #1890ff; margin: 0; }
.logout-btn { padding: 10px 24px; font-size: 1rem; border: none; border-radius: 8px; background: #ff4d4f; color: white; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.3s ease; }
.logout-btn:hover { background: #ff7875; transform: translateY(-2px); }
.module-card { border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); transition: all 0.3s ease; border: none; }
.module-card:hover { transform: translateY(-8px); box-shadow: 0 12px 24px rgba(0,0,0,0.15); }
.card-cover { height: 280px; display: flex; align-items: center; justify-content: center; }
.gradplan-cover { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.card-icon { font-size: 120px; color: white; opacity: 0.9; }
.card-content { padding: 24px; text-align: center; }
.card-content h2 { font-size: 1.8rem; margin: 0 0 16px 0; color: #262626; }
.card-content p { font-size: 1rem; color: #595959; line-height: 1.6; margin: 0; }
EOF
echo "✅ Home"

# ========== GP Page ==========
cat > src/pages/GP.jsx << 'EOF'
import React from 'react';
import { Card, Row, Col, Button } from 'antd';
import { ApiOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './GP.css';

const GP = () => {
  const navigate = useNavigate();
  return (
    <div className="gp-container">
      <div className="gp-header">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} size="large">На главную</Button>
        <h1>Градостроительные планы</h1>
      </div>
      <Row gutter={[24, 24]} style={{ marginTop: 40 }}>
        <Col xs={24} sm={12} lg={8}>
          <Card hoverable className="gp-module-card" onClick={() => navigate('/gp/kaiten')}>
            <div className="module-icon-container" style={{ backgroundColor: '#1890ff' }}>
              <ApiOutlined style={{ fontSize: 64, color: 'white' }} />
            </div>
            <h2 className="module-title">Создать задачу Кайтен</h2>
            <p className="module-description">Автоматическое создание карточки в Kaiten из заявления</p>
            <Button type="primary" block size="large" style={{ backgroundColor: '#1890ff', marginTop: 16 }}>Открыть</Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default GP;
EOF

cat > src/pages/GP.css << 'EOF'
.gp-container { min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 40px 20px; }
.gp-header { display: flex; align-items: center; gap: 20px; max-width: 1400px; margin: 0 auto; flex-wrap: wrap; }
.gp-header h1 { font-size: 2.2rem; font-weight: 700; color: #262626; margin: 0; }
.gp-module-card { border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: all 0.3s ease; text-align: center; padding: 24px; border: none; }
.gp-module-card:hover { transform: translateY(-4px); box-shadow: 0 8px 16px rgba(0,0,0,0.12); }
.module-icon-container { width: 120px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; }
.module-title { font-size: 1.4rem; font-weight: 600; margin: 16px 0; color: #262626; }
.module-description { font-size: 0.95rem; color: #595959; margin-bottom: 24px; min-height: 48px; }
EOF
echo "✅ GP"

# ========== KaitenFlow ==========
mkdir -p src/components/GP
cat > src/components/GP/KaitenFlow.jsx << 'EOF'
import React, { useState } from 'react';
import { Steps, Upload, Button, Card, Descriptions, message, Spin, Result } from 'antd';
import { InboxOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { kaitenApi } from '../../services/api';
import './KaitenFlow.css';

const { Step } = Steps;
const { Dragger } = Upload;

const KaitenFlow = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [cardResult, setCardResult] = useState(null);

  const handleFileUpload = async (file) => {
    setLoading(true);
    try {
      const response = await kaitenApi.parseApplication(file);
      setParsedData(response.data.data);
      message.success('Заявление успешно обработано');
      setCurrentStep(1);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка обработки файла');
    } finally {
      setLoading(false);
    }
    return false;
  };

  const handleCreateTask = async () => {
    setLoading(true);
    try {
      const response = await kaitenApi.createTask({ application: parsedData });
      setCardResult(response.data);
      message.success('Задача успешно создана в Kaiten');
      setCurrentStep(2);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка создания задачи');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setParsedData(null);
    setCardResult(null);
  };

  return (
    <div className="kaiten-container">
      <div className="kaiten-header">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/gp')} size="large">Назад</Button>
        <h1>Создание задачи в Kaiten</h1>
      </div>
      <Card className="kaiten-card">
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Загрузка заявления" />
          <Step title="Подтверждение" />
          <Step title="Готово" />
        </Steps>
        <Spin spinning={loading} size="large">
          {currentStep === 0 && (
            <div className="upload-section">
              <Dragger accept=".docx" beforeUpload={handleFileUpload} showUploadList={false} multiple={false}>
                <p className="ant-upload-drag-icon"><InboxOutlined style={{ fontSize: 64, color: '#1890ff' }} /></p>
                <p className="ant-upload-text">Перетащите файл заявления сюда или нажмите для выбора</p>
                <p className="ant-upload-hint">Поддерживается только формат DOCX</p>
              </Dragger>
            </div>
          )}
          {currentStep === 1 && parsedData && (
            <div className="confirmation-section">
              <Card title="Проверьте данные заявления" style={{ marginBottom: 24 }}>
                <Descriptions column={1} bordered>
                  <Descriptions.Item label="Номер заявления">{parsedData.number || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Дата заявления">{parsedData.date_text || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель">{parsedData.applicant || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Кадастровый номер">{parsedData.cadnum || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Цель использования">{parsedData.purpose || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Срок (план)">{parsedData.service_date || '—'}</Descriptions.Item>
                </Descriptions>
              </Card>
              <Button type="primary" onClick={handleCreateTask} size="large" block>Создать задачу в Kaiten</Button>
            </div>
          )}
          {currentStep === 2 && cardResult && (
            <Result status="success" title="Задача успешно создана в Kaiten!"
              subTitle={<div><p style={{ fontSize: '1.1rem', marginBottom: 24 }}>ID карточки: <strong>{cardResult.card_id}</strong></p>
              <a href={cardResult.card_url} target="_blank" rel="noopener noreferrer"><Button type="primary" size="large">Открыть карточку в Kaiten</Button></a></div>}
              extra={[<Button key="reset" onClick={handleReset} size="large">Создать ещё одну задачу</Button>, <Button key="back" onClick={() => navigate('/gp')} size="large">Вернуться к модулям</Button>]} />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default KaitenFlow;
EOF

cat > src/components/GP/KaitenFlow.css << 'EOF'
.kaiten-container { min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 40px 20px; }
.kaiten-header { display: flex; align-items: center; gap: 20px; max-width: 1000px; margin: 0 auto 32px; }
.kaiten-header h1 { font-size: 2rem; font-weight: 700; color: #262626; margin: 0; }
.kaiten-card { max-width: 1000px; margin: 0 auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.upload-section { padding: 40px 20px; }
.confirmation-section { padding: 20px; }
.ant-upload-drag { border: 2px dashed #1890ff !important; border-radius: 12px; background: #f0f5ff !important; transition: all 0.3s ease; }
.ant-upload-drag:hover { border-color: #40a9ff !important; background: #e6f7ff !important; }
.ant-upload-text { font-size: 1.1rem; color: #262626; font-weight: 500; }
.ant-upload-hint { color: #8c8c8c; }
EOF
echo "✅ KaitenFlow"

# ========== App.js ==========
cat > src/App.js << 'EOF'
import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import LoginForm from './components/Auth/LoginForm';
import Home from './pages/Home';
import GP from './pages/GP';
import KaitenFlow from './components/GP/KaitenFlow';
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
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
EOF
echo "✅ App.js"

# ========== index.css ==========
cat > src/index.css << 'EOF'
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; -webkit-font-smoothing: antialiased; }
EOF
echo "✅ index.css"

echo ""
echo "🎉 ВСЕ ФАЙЛЫ FRONTEND СОЗДАНЫ!"
echo ""
echo "Теперь запускайте: npm start"
