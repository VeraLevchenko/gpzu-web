// frontend/src/pages/Home.jsx
import React from 'react';
import { Card, Row, Col } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import UserHeader from '../components/Common/UserHeader';
import './Home.css';

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="home-container">
      <UserHeader title="Автоматизированная система выдачи документов" />
      
      <div className="home-content">
        <Row gutter={[32, 32]} justify="center">
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="module-card" 
              onClick={() => navigate('/gp')}
            >
              <div className="card-cover gradplan-cover">
                <FileTextOutlined className="card-icon" />
              </div>
              <div className="card-content">
                <h2>Градостроительные планы</h2>
                <p>
                  Подготовка и выдача ГПЗУ: создание задач, генерация документов, 
                  пространственный анализ
                </p>
              </div>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default Home;