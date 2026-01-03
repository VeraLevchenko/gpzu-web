// frontend/src/pages/GP.jsx
import React from 'react';
import { Card, Row, Col, Button } from 'antd';
import { 
  ThunderboltOutlined, 
  DatabaseOutlined, 
  FileSearchOutlined, 
  FileTextOutlined,
  CloseCircleOutlined,
  FolderOpenOutlined,
  BookOutlined 
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
        {/* КНОПКА ЖУРНАЛОВ - ВВЕРХУ */}
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <Button 
            type="primary"
            size="large" 
            icon={<BookOutlined />}
            onClick={() => navigate('/journals')}
            style={{ 
              height: 56,
              fontSize: 18,
              fontWeight: 500,
              padding: '0 48px',
              borderRadius: 8,
            }}
          >
            Просмотреть журналы
          </Button>
        </div>

        {/* Карточки модулей */}
        <Row gutter={[24, 24]}>
          {/* KAITEN */}
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
              <Button type="primary" block size="large" style={{ marginTop: 16 }}>
                Открыть
              </Button>
            </Card>
          </Col>

          {/* MID/MIF */}
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
                Преобразование данных для работы в MapInfo
              </p>
              <Button type="primary" block size="large" style={{ marginTop: 16, backgroundColor: '#52c41a', borderColor: '#52c41a' }}>
                Открыть
              </Button>
            </Card>
          </Col>

          {/* ТУ */}
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
                Формирование запросов технических условий в РСО
              </p>
              <Button type="primary" block size="large" style={{ marginTop: 16, backgroundColor: '#fa8c16', borderColor: '#fa8c16' }}>
                Открыть
              </Button>
            </Card>
          </Col>

          {/* Градплан */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/gradplan')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#722ed1' }}>
                <FileTextOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Подготовить ГПЗУ</h2>
              <p className="module-description">
                Генерация градостроительного плана земельного участка
              </p>
              <Button type="primary" block size="large" style={{ marginTop: 16, backgroundColor: '#722ed1', borderColor: '#722ed1' }}>
                Открыть
              </Button>
            </Card>
          </Col>

          {/* Отказ */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/refusal')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#f5222d' }}>
                <CloseCircleOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Сформировать отказ</h2>
              <p className="module-description">
                Подготовка письма об отказе в выдаче ГПЗУ
              </p>
              <Button type="primary" block size="large" style={{ marginTop: 16, backgroundColor: '#f5222d', borderColor: '#f5222d' }}>
                Открыть
              </Button>
            </Card>
          </Col>

          {/* Рабочий набор */}
          <Col xs={24} sm={12} lg={8}>
            <Card 
              hoverable 
              className="gp-module-card" 
              onClick={() => navigate('/gp/workspace')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#13c2c2' }}>
                <FolderOpenOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Рабочий набор</h2>
              <p className="module-description">
                Создание рабочего набора MapInfo для градплана
              </p>
              <Button type="primary" block size="large" style={{ marginTop: 16, backgroundColor: '#13c2c2', borderColor: '#13c2c2' }}>
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