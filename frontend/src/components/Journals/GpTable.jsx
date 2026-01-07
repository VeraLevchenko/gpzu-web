// frontend/src/components/Journals/GpTable.jsx
import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Select, message, Tag } from 'antd';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons';

const { Option } = Select;

const GpTable = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [filters, setFilters] = useState({ year: new Date().getFullYear() });

  const columns = [
    { title: 'Исх. №', dataIndex: 'out_number', key: 'out_number', width: 100, fixed: 'left' },
    { title: 'Исх. дата', dataIndex: 'out_date', key: 'out_date', width: 120 },
    { title: 'Номер заявления', key: 'app_number', width: 150, render: (_, record) => record.application?.number || '—' },
    { title: 'Заявитель', key: 'applicant', width: 250, ellipsis: true, render: (_, record) => record.application?.applicant || '—' },
    { title: 'Кадастровый номер', key: 'cadnum', width: 180, render: (_, record) => record.application?.cadnum || '—' },
    { title: 'Адрес', key: 'address', width: 300, ellipsis: true, render: (_, record) => record.application?.address || '—' },
    { title: 'XML данные', dataIndex: 'xml_data', key: 'xml_data', width: 120, render: (xml) => <Tag color={xml ? 'green' : 'default'}>{xml ? 'Есть' : 'Нет'}</Tag> },
    { title: 'Действия', key: 'actions', width: 120, fixed: 'right', render: (_, record) => record.attachment && <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => window.open(record.attachment, '_blank')}>Скачать</Button> },
  ];

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      setData([]);
      setPagination({ current: page, pageSize: pageSize, total: 0 });
      message.info('API для градпланов в разработке');
    } catch (error) {
      console.error('Ошибка загрузки градпланов:', error);
      message.error('Не удалось загрузить градпланы');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters]);

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Select value={filters.year} onChange={(value) => setFilters({ ...filters, year: value })} style={{ width: 150 }}>
          {[2024, 2025, 2026].map(year => <Option key={year} value={year}>{year}</Option>)}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={() => fetchData(pagination.current, pagination.pageSize)}>Обновить</Button>
        <Button type="primary" icon={<DownloadOutlined />} disabled title="Функция экспорта в разработке">Экспорт в Excel</Button>
      </Space>
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={pagination} onChange={(newPagination) => fetchData(newPagination.current, newPagination.pageSize)} scroll={{ x: 1300 }} size="middle" locale={{ emptyText: 'API для градпланов в разработке' }} />
    </div>
  );
};

export default GpTable;