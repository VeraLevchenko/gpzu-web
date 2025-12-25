// frontend/src/pages/GP.jsx
import React from 'react';
import { Card, Row, Col, Button } from 'antd';
import { 
  ThunderboltOutlined, 
  DatabaseOutlined, 
  FileSearchOutlined, 
  FileTextOutlined,
  CloseCircleOutlined,
  FolderOpenOutlined 
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import UserHeader from '../components/Common/UserHeader';
import './GP.css';

const GP = () => {
  const navigate = useNavigate();

  return (
    <div className="gp-container">
      <UserHeader 
        title="Градостроительные планы" 
        showBackButton={true}
      />
      
      <div className="gp-content">
        <Row gutter={[24, 24]}>
          {/* KAITEN - Синяя карточка */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/kaiten')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#1890ff' }}>
                <ThunderboltOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Создать задачу</h2>
              <p className="module-description">
                Автоматическое создание задач в Kaiten из заявлений
              </p>
              <Button 
                type="primary" 
                block 
                size="large" 
                style={{ marginTop: 16 }}
              >
                Открыть
              </Button>
            </Card>
          </Col>

          {/* MID/MIF - Зелёная карточка */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/midmif')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#52c41a' }}>
                <DatabaseOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Подготовить MID/MIF</h2>
              <p className="module-description">
                Формирование файлов координат для MapInfo
              </p>
              <Button 
                type="primary" 
                block 
                size="large" 
                style={{ backgroundColor: '#52c41a', marginTop: 16 }}
              >
                Открыть
              </Button>
            </Card>
          </Col>

          {/* ТУ - Оранжевая карточка */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/tu')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#fa8c16' }}>
                <FileSearchOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Запросить ТУ</h2>
              <p className="module-description">
                Формирование запросов технических условий
              </p>
              <Button 
                type="primary" 
                block 
                size="large" 
                style={{ backgroundColor: '#fa8c16', marginTop: 16 }}
              >
                Открыть
              </Button>
            </Card>
          </Col>

          {/* ГПЗУ - Фиолетовая карточка */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/gradplan')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#722ed1' }}>
                <FileTextOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Сформировать ГПЗУ</h2>
              <p className="module-description">
                Автоматическое формирование градостроительного плана земельного участка
              </p>
              <Button 
                type="primary" 
                block 
                size="large" 
                style={{ backgroundColor: '#722ed1', marginTop: 16 }}
              >
                Открыть
              </Button>
            </Card>
          </Col>

          {/* ОТКАЗ - Красная карточка */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/refusal')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#f5222d' }}>
                <CloseCircleOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Отказ в выдаче ГПЗУ</h2>
              <p className="module-description">
                Формирование мотивированного отказа в предоставлении градостроительного плана
              </p>
              <Button 
                type="primary" 
                block 
                size="large" 
                style={{ backgroundColor: '#f5222d', marginTop: 16 }}
              >
                Открыть
              </Button>
            </Card>
          </Col>

          {/* РАБОЧИЙ НАБОР - Синяя карточка */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/workspace')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#1890ff' }}>
                <FolderOpenOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Рабочий набор MapInfo</h2>
              <p className="module-description">
                Автоматическая генерация рабочего набора MapInfo из выписки ЕГРН с архивом ZIP
              </p>
              <Button 
                type="primary" 
                block 
                size="large" 
                style={{ backgroundColor: '#1890ff', marginTop: 16 }}
              >
                Открыть
              </Button>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default GP;