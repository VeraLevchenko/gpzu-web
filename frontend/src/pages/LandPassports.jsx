import React from 'react';
import { Card, Row, Col, Button } from 'antd';
import { FileExcelOutlined, FileDoneOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import UserHeader from '../components/Common/UserHeader';
import './GP.css';

const LandPassports = () => {
  const navigate = useNavigate();

  return (
    <div className="gp-container">
      <UserHeader
        title="Паспорта земельных участков"
        showBackButton={true}
      />

      <div className="gp-content">
        <Row gutter={[24, 24]} justify="center">
          <Col xs={24} sm={12} lg={8}>
            <Card
              hoverable
              className="gp-module-card"
              onClick={() => navigate('/land-passports/list')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#1890ff' }}>
                <FileExcelOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Подготовить перечень</h2>
              <p className="module-description">
                Загрузите ЕГРН XML/ZIP — получите xlsx с заполненными данными участков
              </p>
              <Button type="primary" block size="large" style={{ marginTop: 16 }}>
                Открыть
              </Button>
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={8}>
            <Card
              hoverable
              className="gp-module-card"
              onClick={() => navigate('/land-passports/passports')}
            >
              <div className="module-icon-container" style={{ backgroundColor: '#52c41a' }}>
                <FileDoneOutlined style={{ fontSize: 64, color: 'white' }} />
              </div>
              <h2 className="module-title">Подготовить паспорта</h2>
              <p className="module-description">
                Загрузите xlsx — получите zip с docx-паспортами для каждого участка
              </p>
              <Button
                type="primary"
                block
                size="large"
                style={{ marginTop: 16, backgroundColor: '#52c41a', borderColor: '#52c41a' }}
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

export default LandPassports;
