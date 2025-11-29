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
