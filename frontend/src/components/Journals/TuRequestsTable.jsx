// frontend/src/components/Journals/TuRequestsTable.jsx
import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, Select, message } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Option } = Select;

const TuRequestsTable = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [filters, setFilters] = useState({ year: new Date().getFullYear(), rso_type: null });

  const rsoColors = { vodokanal: 'blue', gaz: 'orange', teplo: 'red' };
  const rsoLabels = { vodokanal: 'Водоканал', gaz: 'Газоснабжение', teplo: 'Теплоснабжение' };

  const columns = [
    { title: 'Исх. №', dataIndex: 'out_number', key: 'out_number', width: 100, fixed: 'left' },
    { title: 'Исх. дата', dataIndex: 'out_date', key: 'out_date', width: 120 },
    { title: 'Номер заявления', key: 'app_number', width: 150, render: (_, record) => record.application?.number || '—' },
    { title: 'Заявитель', key: 'applicant', width: 250, ellipsis: true, render: (_, record) => record.application?.applicant || '—' },
    { title: 'Кадастровый номер', key: 'cadnum', width: 180, render: (_, record) => record.application?.cadnum || '—' },
    { title: 'РСО', dataIndex: 'rso_type', key: 'rso_type', width: 150, render: (type) => <Tag color={rsoColors[type]}>{rsoLabels[type] || type}</Tag> },
    { title: 'Организация', dataIndex: 'rso_name', key: 'rso_name', width: 300, ellipsis: true },
    { title: 'Действия', key: 'actions', width: 120, fixed: 'right', render: (_, record) => record.attachment && <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => window.open(record.attachment, '_blank')}>Скачать</Button> },
  ];

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const params = { skip: (page - 1) * pageSize, limit: pageSize, year: filters.year, ...(filters.rso_type && { rso_type: filters.rso_type }) };
      const response = await axios.get('/api/gp/tu-requests', { params });
      setData(response.data.items);
      setPagination({ current: page, pageSize: pageSize, total: response.data.total });
    } catch (error) {
      console.error('Ошибка загрузки запросов ТУ:', error);
      message.error('Не удалось загрузить запросы ТУ');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters]);

  const exportToExcel = async () => {
    try {
      const response = await axios.get('/api/gp/tu-requests/export/excel', { params: { year: filters.year }, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Журнал_запросов_ТУ_${filters.year}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('Файл успешно экспортирован');
    } catch (error) {
      console.error('Ошибка экспорта:', error);
      message.error('Не удалось экспортировать данные');
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Select value={filters.year} onChange={(value) => setFilters({ ...filters, year: value })} style={{ width: 150 }}>
          {[2024, 2025, 2026].map(year => <Option key={year} value={year}>{year}</Option>)}
        </Select>
        <Select placeholder="Фильтр по РСО" allowClear onChange={(value) => setFilters({ ...filters, rso_type: value || null })} style={{ width: 200 }}>
          <Option value="vodokanal">Водоканал</Option>
          <Option value="gaz">Газоснабжение</Option>
          <Option value="teplo">Теплоснабжение</Option>
        </Select>
        <Button icon={<ReloadOutlined />} onClick={() => fetchData(pagination.current, pagination.pageSize)}>Обновить</Button>
        <Button type="primary" icon={<DownloadOutlined />} onClick={exportToExcel}>Экспорт в Excel</Button>
      </Space>
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={pagination} onChange={(newPagination) => fetchData(newPagination.current, newPagination.pageSize)} scroll={{ x: 1400 }} size="middle" />
    </div>
  );
};

export default TuRequestsTable;