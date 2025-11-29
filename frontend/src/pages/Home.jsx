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
