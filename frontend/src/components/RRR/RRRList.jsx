// frontend/src/components/RRR/RRRList.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Table, Button, Input, Select, Tag, Space, message, Popconfirm } from 'antd';
import { PlusOutlined, ReloadOutlined, ArrowLeftOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { rrrApi } from '../../services/api';
import UserHeader from '../Common/UserHeader';
import './RRRList.css';

const { Search } = Input;
const { Option } = Select;

const RRRList = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState(null);
  const pageSize = 20;

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await rrrApi.getList({
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        search: searchText || undefined,
        status: statusFilter || undefined,
      });
      setData(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      message.error('Ошибка загрузки данных');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchText, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getRemainingDays = (record) => {
    if (!record.service_deadline_date) return null;
    const deadline = new Date(record.service_deadline_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.ceil((deadline - today) / (1000 * 60 * 60 * 24));
    return diff;
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    try {
      await rrrApi.delete(id);
      message.success('Заявление удалено');
      loadData();
    } catch (error) {
      message.error('Ошибка удаления');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'зарегистрировано': return 'blue';
      case 'в работе': return 'orange';
      case 'завершено': return 'green';
      default: return 'default';
    }
  };

  const columns = [
    {
      title: '№',
      dataIndex: 'app_number',
      key: 'app_number',
      width: 120,
      fixed: 'left',
    },
    {
      title: 'Дата',
      dataIndex: 'app_date',
      key: 'app_date',
      width: 110,
      render: (date) => {
        if (!date) return '-';
        const d = new Date(date);
        return d.toLocaleDateString('ru-RU');
      },
    },
    {
      title: 'Заявитель',
      key: 'applicant',
      width: 250,
      ellipsis: true,
      render: (_, record) => record.org_name || record.person_name || '-',
    },
    {
      title: 'Объект',
      dataIndex: 'object_name',
      key: 'object_name',
      width: 250,
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status) => (
        <Tag color={getStatusColor(status)}>{status || '-'}</Tag>
      ),
    },
    {
      title: 'Осталось',
      key: 'remaining',
      width: 110,
      fixed: 'right',
      render: (_, record) => {
        const days = getRemainingDays(record);
        if (days === null) return '-';
        let color = '#52c41a';
        if (days < 3) color = '#ff4d4f';
        else if (days <= 10) color = '#faad14';
        return (
          <span style={{ color, fontWeight: 600 }}>
            {days} дн.
          </span>
        );
      },
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      fixed: 'right',
      render: (_, record) => (
        <Popconfirm
          title="Удалить заявление?"
          description="Это действие нельзя отменить"
          onConfirm={(e) => handleDelete(record.id, e)}
          onCancel={(e) => e.stopPropagation()}
          okText="Удалить"
          cancelText="Отмена"
          icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
        >
          <Button
            danger
            type="text"
            size="small"
            icon={<DeleteOutlined />}
            onClick={(e) => e.stopPropagation()}
          />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="rrr-list-container">
      <UserHeader title="РРР — Разрешение на размещение объектов" />

      <div className="rrr-list-content">
        <div className="rrr-list-toolbar">
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
              На главную
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/rrr/new')}>
              Новое заявление
            </Button>
          </Space>

          <Space>
            <Search
              placeholder="Поиск по номеру/заявителю"
              allowClear
              style={{ width: 280 }}
              onSearch={(value) => { setSearchText(value); setCurrentPage(1); }}
            />
            <Select
              placeholder="Статус"
              allowClear
              style={{ width: 180 }}
              onChange={(value) => { setStatusFilter(value); setCurrentPage(1); }}
            >
              <Option value="зарегистрировано">Зарегистрировано</Option>
              <Option value="в работе">В работе</Option>
              <Option value="завершено">Завершено</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadData} />
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ x: 1100 }}
          onRow={(record) => ({
            onClick: () => navigate(`/rrr/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: (page) => setCurrentPage(page),
            showTotal: (total) => `Всего: ${total}`,
          }}
        />
      </div>
    </div>
  );
};

export default RRRList;
