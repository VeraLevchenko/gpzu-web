// frontend/src/pages/Journals.jsx
import React, { useState } from 'react';
import { Tabs } from 'antd';
import { 
  FileTextOutlined, 
  CloseCircleOutlined, 
  ThunderboltOutlined,
  EnvironmentOutlined 
} from '@ant-design/icons';
import UserHeader from '../components/Common/UserHeader';
import ApplicationsTable from '../components/Journals/ApplicationsTable';
import RefusalsTable from '../components/Journals/RefusalsTable';
import TuRequestsTable from '../components/Journals/TuRequestsTable';
import GpTable from '../components/Journals/GpTable';
import './Journals.css';

const Journals = () => {
  const [activeTab, setActiveTab] = useState('applications');

  const items = [
    {
      key: 'applications',
      label: (
        <span>
          <FileTextOutlined />
          Заявления
        </span>
      ),
      children: <ApplicationsTable />,
    },
    {
      key: 'gp',
      label: (
        <span>
          <EnvironmentOutlined />
          Градпланы
        </span>
      ),
      children: <GpTable />,
    },
    {
      key: 'refusals',
      label: (
        <span>
          <CloseCircleOutlined />
          Отказы
        </span>
      ),
      children: <RefusalsTable />,
    },
    {
      key: 'tu-requests',
      label: (
        <span>
          <ThunderboltOutlined />
          Запросы ТУ
        </span>
      ),
      children: <TuRequestsTable />,
    },
  ];

  return (
    <div className="journals-container">
      <UserHeader 
        title="Журналы ГПЗУ" 
        showBackButton={true}
        backPath="/gp"
      />
      
      <div className="journals-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={items}
          size="large"
          className="journals-tabs"
        />
      </div>
    </div>
  );
};

export default Journals;
