// frontend/src/components/Journals/RefusalsTable.jsx
import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, Select, message, Modal, Form, Input, Popconfirm, Descriptions, Upload, InputNumber } from 'antd';
import { ReloadOutlined, DownloadOutlined, EditOutlined, DeleteOutlined, UploadOutlined, CloseCircleOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Option } = Select;
const { TextArea } = Input;

const RefusalsTable = () => {
  const [data, setData] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [filters, setFilters] = useState({ year: new Date().getFullYear() });
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [form] = Form.useForm();

  const reasonLabels = {
    NO_RIGHTS: 'Нет прав на участок',
    NO_BORDERS: 'Границы не установлены',
    NOT_IN_CITY: 'Не в городе',
    OBJECT_NOT_EXISTS: 'Объект не существует',
    HAS_ACTIVE_GP: 'Есть действующий ГП',
  };

  const columns = [
    { title: 'Исх. №', dataIndex: 'out_number', key: 'out_number', width: 100 },
    { title: 'Исх. дата', dataIndex: 'out_date', key: 'out_date', width: 120 },
    { title: 'Номер заявления', key: 'app_number', width: 150, render: (_, record) => record.application?.number || '—' },
    { title: 'Дата заявления', key: 'app_date', width: 120, render: (_, record) => record.application?.date || '—' },
    { title: 'Заявитель', key: 'applicant', width: 250, ellipsis: true, render: (_, record) => record.application?.applicant || '—' },
    { title: 'Адрес', key: 'address', width: 300, ellipsis: true, render: (_, record) => record.application?.address || '—' },
    { title: 'Кадастровый номер', key: 'cadnum', width: 180, render: (_, record) => record.application?.cadnum || '—' },
    { 
      title: 'Причина отказа', 
      dataIndex: 'reason_code', 
      key: 'reason_code', 
      width: 200, 
      render: (code) => <Tag color="red">{reasonLabels[code] || code}</Tag> 
    },
  ];

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const params = { skip: (page - 1) * pageSize, limit: pageSize, year: filters.year };
      const response = await axios.get('/api/gp/refusals', { params });
      setData(response.data.items);
      setPagination({ current: page, pageSize: pageSize, total: response.data.total });
    } catch (error) {
      console.error('Ошибка загрузки отказов:', error);
      message.error('Не удалось загрузить отказы');
    } finally {
      setLoading(false);
    }
  };

  const fetchApplications = async () => {
    try {
      const response = await axios.get('/api/gp/applications', { params: { limit: 1000 } });
      setApplications(response.data.items);
    } catch (error) {
      console.error('Ошибка загрузки заявлений:', error);
    }
  };

  useEffect(() => {
    fetchData();
    fetchApplications();
  }, [filters]);

  const handleView = (record) => {
    setSelectedRecord(record);
    setIsEditing(false);
    form.setFieldsValue({
      out_number: record.out_number,
      out_date: record.out_date,
      reason_code: record.reason_code,
      reason_text: record.reason_text,
      application_id: record.application_id,
    });
    setViewModalVisible(true);
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const updateData = {
        out_number: values.out_number,
        out_date: values.out_date,
        out_year: parseInt(values.out_date.split('.')[2]),
        reason_code: values.reason_code,
        reason_text: values.reason_text,
        application_id: values.application_id,
      };
      await axios.put(`/api/gp/refusals/${selectedRecord.id}`, updateData);
      message.success('Отказ обновлен');
      setIsEditing(false);
      setViewModalVisible(false);
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Ошибка обновления:', error);
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('Не удалось обновить отказ');
      }
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    form.setFieldsValue({
      out_number: selectedRecord.out_number,
      out_date: selectedRecord.out_date,
      reason_code: selectedRecord.reason_code,
      reason_text: selectedRecord.reason_text,
      application_id: selectedRecord.application_id,
    });
  };

  const handleDelete = async () => {
    try {
      await axios.delete(`/api/gp/refusals/${selectedRecord.id}`);
      message.success('Отказ удален');
      setViewModalVisible(false);
      fetchData(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Ошибка удаления:', error);
      message.error('Не удалось удалить отказ');
    }
  };

  const handleDeleteAttachment = async () => {
    try {
      await axios.delete(`/api/gp/refusals/${selectedRecord.id}/attachment`);
      message.success('Вложение удалено');
      const updatedRecord = { ...selectedRecord, attachment: null };
      setSelectedRecord(updatedRecord);
    } catch (error) {
      console.error('Ошибка удаления вложения:', error);
      message.error('Не удалось удалить вложение');
    }
  };

  const handleUploadAttachment = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`/api/gp/refusals/${selectedRecord.id}/attachment`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      message.success('Вложение загружено');
      const updatedRecord = { ...selectedRecord, attachment: response.data.attachment };
      setSelectedRecord(updatedRecord);
    } catch (error) {
      console.error('Ошибка загрузки:', error);
      message.error('Не удалось загрузить вложение');
    }
    
    return false;
  };

  const exportToExcel = async () => {
    try {
      const response = await axios.get('/api/gp/refusals/export/excel', { params: { year: filters.year }, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Журнал_отказов_${filters.year}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('Файл успешно экспортирован');
    } catch (error) {
      console.error('Ошибка экспорта:', error);
      message.error('Не удалось экспортировать данные');
    }
  };

  const selectedApplication = applications.find(app => app.id === form.getFieldValue('application_id'));

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Select value={filters.year} onChange={(value) => setFilters({ ...filters, year: value })} style={{ width: 150 }}>
          {[2024, 2025, 2026].map(year => <Option key={year} value={year}>{year}</Option>)}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={() => fetchData(pagination.current, pagination.pageSize)}>Обновить</Button>
        <Button type="primary" icon={<DownloadOutlined />} onClick={exportToExcel}>Экспорт в Excel</Button>
      </Space>

      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="id" 
        loading={loading} 
        pagination={pagination} 
        onChange={(newPagination) => fetchData(newPagination.current, newPagination.pageSize)} 
        onRow={(record) => ({ onClick: () => handleView(record), style: { cursor: 'pointer' } })}
        scroll={{ x: 1600 }} 
        size="middle" 
      />

      <Modal
        title={`Отказ №${selectedRecord?.out_number} от ${selectedRecord?.out_date}`}
        open={viewModalVisible}
        onCancel={() => { setViewModalVisible(false); setIsEditing(false); }}
        width={900}
        footer={[
          isEditing ? (
            <Button key="cancel" onClick={handleCancel}>Отмена</Button>
          ) : (
            <Button key="edit" type="primary" icon={<EditOutlined />} onClick={handleEdit}>Редактировать</Button>
          ),
          isEditing ? (
            <Button key="save" type="primary" onClick={handleSave}>Сохранить</Button>
          ) : (
            <Popconfirm key="delete" title="Удалить отказ?" description="Это действие нельзя отменить" onConfirm={handleDelete} okText="Да" cancelText="Нет">
              <Button danger icon={<DeleteOutlined />}>Удалить</Button>
            </Popconfirm>
          ),
          <Button key="close" onClick={() => { setViewModalVisible(false); setIsEditing(false); }}>Закрыть</Button>
        ]}
      >
        {selectedRecord && (
          <Form form={form} layout="vertical">
            <Form.Item label="Исходящий номер" name="out_number" rules={[{ required: true }]}>
              <InputNumber disabled={!isEditing} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item label="Исходящая дата" name="out_date" rules={[{ required: true }]}>
              <Input disabled={!isEditing} placeholder="ДД.ММ.ГГГГ" />
            </Form.Item>

            <Form.Item label="Заявление" name="application_id" rules={[{ required: true }]}>
              <Select 
                disabled={!isEditing} 
                showSearch 
                optionFilterProp="children" 
                filterOption={(input, option) => {
                  const children = Array.isArray(option.children) ? option.children.join(' ') : (option.children || '');
                  return children.toLowerCase().includes(input.toLowerCase());
                }}
              >
                {applications.map(app => (
                  <Option key={app.id} value={app.id}>{app.number} - {app.applicant}</Option>
                ))}
              </Select>
            </Form.Item>

            {selectedApplication && (
              <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="Номер заявления">{selectedApplication.number}</Descriptions.Item>
                <Descriptions.Item label="Дата заявления">{selectedApplication.date}</Descriptions.Item>
                <Descriptions.Item label="Заявитель" span={2}>{selectedApplication.applicant}</Descriptions.Item>
                <Descriptions.Item label="Адрес" span={2}>{selectedApplication.address || '—'}</Descriptions.Item>
                <Descriptions.Item label="Кадастровый номер" span={2}>{selectedApplication.cadnum}</Descriptions.Item>
              </Descriptions>
            )}

            <Form.Item label="Причина отказа" name="reason_code" rules={[{ required: true }]}>
              <Select disabled={!isEditing}>
                <Option value="NO_RIGHTS">Нет прав на участок</Option>
                <Option value="NO_BORDERS">Границы не установлены</Option>
                <Option value="NOT_IN_CITY">Не в городе</Option>
                <Option value="OBJECT_NOT_EXISTS">Объект не существует</Option>
                <Option value="HAS_ACTIVE_GP">Есть действующий ГП</Option>
              </Select>
            </Form.Item>

            <Form.Item label="Текст причины" name="reason_text">
              <TextArea rows={4} disabled={!isEditing} />
            </Form.Item>

            <Form.Item label="Вложение">
              {selectedRecord.attachment ? (
                <Space>
                  <Button icon={<DownloadOutlined />} onClick={() => window.open(selectedRecord.attachment, '_blank')}>Скачать</Button>
                  {isEditing && <Button danger icon={<CloseCircleOutlined />} onClick={handleDeleteAttachment}>Удалить</Button>}
                </Space>
              ) : (
                isEditing && <Upload beforeUpload={handleUploadAttachment} maxCount={1}><Button icon={<UploadOutlined />}>Загрузить DOCX</Button></Upload>
              )}
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default RefusalsTable;