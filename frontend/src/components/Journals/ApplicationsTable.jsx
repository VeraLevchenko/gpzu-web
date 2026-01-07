// frontend/src/components/Journals/ApplicationsTable.jsx
import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, Input, Select, message } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Search } = Input;
const { Option } = Select;

const ApplicationsTable = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [filters, setFilters] = useState({
    status: null,
    cadnum: null,
  });

  const statusColors = {
    new: 'blue',
    in_progress: 'orange',
    gp_issued: 'green',
    refused: 'red',
  };

  const statusLabels = {
    new: 'Новое',
    in_progress: 'В работе',
    gp_issued: 'ГП выдан',
    refused: 'Отказ',
  };

  const columns = [
    {
      title: 'Номер',
      dataIndex: 'number',
      key: 'number',
      width: 150,
      fixed: 'left',
    },
    {
      title: 'Дата',
      dataIndex: 'date',
      key: 'date',
      width: 120,
    },
    {
      title: 'Заявитель',
      dataIndex: 'applicant',
      key: 'applicant',
      width: 250,
      ellipsis: true,
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
      width: 150,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Кадастровый номер',
      dataIndex: 'cadnum',
      key: 'cadnum',
      width: 180,
    },
    {
      title: 'Адрес',
      dataIndex: 'address',
      key: 'address',
      width: 300,
      ellipsis: true,
    },
    {
      title: 'Площадь',
      dataIndex: 'area',
      key: 'area',
      width: 100,
      render: (area) => area ? `${area} м²` : '—',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      fixed: 'right',
      render: (status) => (
        <Tag color={statusColors[status]}>
          {statusLabels[status] || status}
        </Tag>
      ),
    },
  ];

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const params = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...filters,
      };

      const response = await axios.get('/api/gp/applications', { params });
      
      setData(response.data.items);
      setPagination({
        current: page,
        pageSize: pageSize,
        total: response.data.total,
      });
    } catch (error) {
      console.error('Ошибка загрузки заявлений:', error);
      message.error('Не удалось загрузить заявления');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters]);

  const handleTableChange = (newPagination) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleSearch = (value) => {
    setFilters({ ...filters, cadnum: value || null });
  };

  const handleStatusChange = (value) => {
    setFilters({ ...filters, status: value || null });
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="Поиск по кадастровому номеру"
          allowClear
          onSearch={handleSearch}
          style={{ width: 300 }}
          prefix={<SearchOutlined />}
        />
        
        <Select
          placeholder="Фильтр по статусу"
          allowClear
          onChange={handleStatusChange}
          style={{ width: 200 }}
        >
          <Option value="new">Новое</Option>
          <Option value="in_progress">В работе</Option>
          <Option value="gp_issued">ГП выдан</Option>
          <Option value="refused">Отказ</Option>
        </Select>

        <Button 
          icon={<ReloadOutlined />} 
          onClick={() => fetchData(pagination.current, pagination.pageSize)}
        >
          Обновить
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={pagination}
        onChange={handleTableChange}
        scroll={{ x: 1500 }}
        size="middle"
      />
    </div>
  );
};

export default ApplicationsTable;
