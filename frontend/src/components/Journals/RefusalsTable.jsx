// frontend/src/components/Journals/RefusalsTable.jsx
import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, message, Modal, Form, Input, Popconfirm, Descriptions, Upload, InputNumber, Select, Alert } from 'antd';
import { ReloadOutlined, DownloadOutlined, DeleteOutlined, UploadOutlined, CloseCircleOutlined, WarningOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Option } = Select;
const { TextArea } = Input;

const RefusalsTable = () => {
  const [data, setData] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [searchText, setSearchText] = useState('');
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [applicationWarning, setApplicationWarning] = useState(null);
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
    { title: 'Заявитель', key: 'applicant', width: 250, render: (_, record) => record.application?.applicant || '—' },
    { title: 'Адрес', key: 'address', width: 300, render: (_, record) => record.application?.address || '—' },
    { title: 'Кадастровый номер', key: 'cadnum', width: 180, render: (_, record) => record.application?.cadnum || '—' },
    { title: 'Причина отказа', key: 'reason', width: 200, render: (_, record) => <Tag color="red">{reasonLabels[record.reason_code] || record.reason_code}</Tag> },
  ];

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/gp/refusals/', {
        params: {
          page: pagination.current,
          page_size: pagination.pageSize,
          search: searchText || undefined
        }
      });
      
      if (response.data.success) {
        setData(response.data.data);
        setPagination(prev => ({
          ...prev,
          total: response.data.pagination.total
        }));
      }
    } catch (error) {
      message.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const fetchApplications = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/gp/applications/');
      console.log('Ответ API заявлений:', response.data);
      
      // API возвращает {total, items, skip, limit} вместо {success, data}
      if (response.data.items) {
        console.log('Загружено заявлений:', response.data.items.length);
        setApplications(response.data.items);
      }
    } catch (error) {
      console.error('Ошибка загрузки заявлений:', error);
      message.error('Ошибка загрузки списка заявлений');
    }
  };

  useEffect(() => {
    fetchData();
    fetchApplications();
  }, [pagination.current, pagination.pageSize]);

  const handleTableChange = (newPagination) => {
    setPagination(newPagination);
  };

  const handleView = (record) => {
    setSelectedRecord(record);
    form.setFieldsValue({
      application_id: record.application_id,
      out_number: record.out_number,
      out_date: record.out_date,
      out_year: record.out_year,
      reason_code: record.reason_code,
      reason_text: record.reason_text,
    });
    setIsEditing(false);
    setApplicationWarning(null);
    setViewModalVisible(true);
  };

  const handleApplicationChange = (applicationId) => {
    const app = applications.find(a => a.id === applicationId);
    if (!app) return;

    // Проверяем, есть ли у этого заявления уже отказ или градплан
    let warnings = [];
    if (app.status === 'refused') {
      warnings.push('У этого заявления уже есть отказ');
    }
    if (app.status === 'approved') {
      warnings.push('У этого заявления уже выдан градплан');
    }

    if (warnings.length > 0) {
      setApplicationWarning(warnings.join('. '));
    } else {
      setApplicationWarning(null);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      // Если есть предупреждение, требуем подтверждения
      if (applicationWarning) {
        Modal.confirm({
          title: 'Внимание!',
          content: applicationWarning + '. Вы уверены, что хотите продолжить?',
          okText: 'Да, продолжить',
          cancelText: 'Отмена',
          onOk: async () => {
            await saveRefusal(values);
          }
        });
      } else {
        await saveRefusal(values);
      }
    } catch (error) {
      message.error('Пожалуйста, заполните все обязательные поля');
    }
  };


  const saveRefusal = async (values) => {
    try {
      await axios.put(`http://localhost:8000/api/gp/refusals/${selectedRecord.id}`, values);
      message.success('Отказ обновлён');
      
      // Обновляем данные
      await fetchData();
      
      // Получаем обновленную запись
      const response = await axios.get('http://localhost:8000/api/gp/refusals/', {
        params: { page: pagination.current, page_size: pagination.pageSize, search: searchText || undefined }
      });
      
      if (response.data.success) {
        const updatedRecord = response.data.data.find(r => r.id === selectedRecord.id);
        if (updatedRecord) {
          setSelectedRecord(updatedRecord);
        }
      }
      
      setIsEditing(false);
      setApplicationWarning(null);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка сохранения');
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`http://localhost:8000/api/gp/refusals/${id}`);
      message.success('Отказ удалён');
      fetchData();
    } catch (error) {
      message.error('Ошибка удаления');
    }
  };

  const handleUploadAttachment = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post(`http://localhost:8000/api/gp/refusals/${selectedRecord.id}/attachment`, formData);
      message.success('Вложение загружено');
      fetchData();
      setViewModalVisible(false);
    } catch (error) {
      message.error('Ошибка загрузки вложения');
    }
    return false;
  };

  const handleDeleteAttachment = async () => {
    try {
      await axios.delete(`http://localhost:8000/api/gp/refusals/${selectedRecord.id}/attachment`);
      message.success('Вложение удалено');
      fetchData();
      setViewModalVisible(false);
    } catch (error) {
      message.error('Ошибка удаления вложения');
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/gp/refusals/export/excel', {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Refusals_${new Date().getFullYear()}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      message.success('Excel файл успешно скачан');
    } catch (error) {
      message.error('Ошибка экспорта');
    }
  };

  const selectedApplication = applications.find(app => app.id === form.getFieldValue('application_id'));
  const displayApplication = isEditing && selectedApplication ? selectedApplication : selectedRecord?.application;

  return (
    <div style={{ padding: 24 }}>
      <h2>Журнал отказов</h2>

      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="Поиск по всем полям..."
          allowClear
          enterButton="Найти"
          size="large"
          style={{ width: 400 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onSearch={fetchData}
        />
        <Button icon={<ReloadOutlined />} onClick={fetchData}>
          Обновить
        </Button>
        <Button 
          type="primary" 
          icon={<DownloadOutlined />}
          onClick={handleExport}
        >
          Экспорт в Excel
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
        onRow={(record) => ({
          onClick: () => handleView(record),
          style: { cursor: 'pointer' }
        })}
      />

      <Modal
        title="Детали отказа"
        open={viewModalVisible}
        onCancel={() => { setViewModalVisible(false); setIsEditing(false); setApplicationWarning(null); }}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => { setViewModalVisible(false); setIsEditing(false); setApplicationWarning(null); }}>
            Закрыть
          </Button>,
          !isEditing ? (
            <Button key="edit" type="primary" onClick={() => setIsEditing(true)}>
              Редактировать
            </Button>
          ) : (
            <Button key="save" type="primary" onClick={handleSave}>
              Сохранить
            </Button>
          ),
          <Popconfirm 
            key="delete"
            title="Удалить этот отказ?" 
            onConfirm={() => {
              handleDelete(selectedRecord.id);
              setViewModalVisible(false);
            }}
          >
            <Button danger icon={<DeleteOutlined />}>
              Удалить
            </Button>
          </Popconfirm>
        ]}
      >
        {selectedRecord && (
          <Form form={form} component={false}>
            {/* Предупреждение о конфликте */}
            {isEditing && applicationWarning && (
              <Alert
                message="Внимание!"
                description={applicationWarning}
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                style={{ marginBottom: 16 }}
              />
            )}

            <Descriptions bordered column={2} size="middle">
              {/* Исходящий номер */}
              <Descriptions.Item label="Исходящий номер">
                {!isEditing ? (
                  selectedRecord.out_number
                ) : (
                  <Form.Item name="out_number" rules={[{ required: true }]} style={{ margin: 0 }}>
                    <InputNumber style={{ width: '100%' }} />
                  </Form.Item>
                )}
              </Descriptions.Item>

              {/* Исходящая дата */}
              <Descriptions.Item label="Исходящая дата">
                {!isEditing ? (
                  selectedRecord.out_date
                ) : (
                  <Form.Item name="out_date" rules={[{ required: true }]} style={{ margin: 0 }}>
                    <Input placeholder="ДД.ММ.ГГГГ" />
                  </Form.Item>
                )}
              </Descriptions.Item>

              {/* Номер заявления - редактируемое поле */}
              <Descriptions.Item label="Номер заявления">
                {!isEditing ? (
                  displayApplication?.number || '—'
                ) : (
                  <Form.Item name="application_id" rules={[{ required: true }]} style={{ margin: 0 }}>
                    <Select
                      showSearch
                      placeholder="Выберите заявление"
                      style={{ width: '100%' }}
                      optionFilterProp="children"
                      onChange={handleApplicationChange}
                      filterOption={(input, option) => {
                        return option.children.toLowerCase().includes(input.toLowerCase());
                      }}
                    >
                      {applications.map(app => (
                        <Option key={app.id} value={app.id}>{app.number}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                )}
              </Descriptions.Item>

              {/* Дата заявления */}
              <Descriptions.Item label="Дата заявления">
                {displayApplication?.date || '—'}
              </Descriptions.Item>

              {/* Заявитель */}
              <Descriptions.Item label="Заявитель" span={2}>
                {displayApplication?.applicant || '—'}
              </Descriptions.Item>

              {/* Адрес */}
              <Descriptions.Item label="Адрес" span={2}>
                {displayApplication?.address || '—'}
              </Descriptions.Item>

              {/* Кадастровый номер */}
              <Descriptions.Item label="Кадастровый номер" span={2}>
                {displayApplication?.cadnum || '—'}
              </Descriptions.Item>

              {/* Причина отказа */}
              <Descriptions.Item label="Причина отказа" span={2}>
                {!isEditing ? (
                  <Tag color="red">{reasonLabels[selectedRecord.reason_code] || selectedRecord.reason_code}</Tag>
                ) : (
                  <Form.Item name="reason_code" rules={[{ required: true }]} style={{ margin: 0 }}>
                    <Select style={{ width: '100%' }}>
                      <Option value="NO_RIGHTS">Нет прав на участок</Option>
                      <Option value="NO_BORDERS">Границы не установлены</Option>
                      <Option value="NOT_IN_CITY">Не в городе</Option>
                      <Option value="OBJECT_NOT_EXISTS">Объект не существует</Option>
                      <Option value="HAS_ACTIVE_GP">Есть действующий ГП</Option>
                    </Select>
                  </Form.Item>
                )}
              </Descriptions.Item>

              {/* Вложение */}
              <Descriptions.Item label="Вложение" span={2}>
                {selectedRecord.attachment ? (
                  <Space>
                    <Button 
                      icon={<DownloadOutlined />} 
                      size="small"
                      onClick={() => {
                        const url = `http://localhost:8000/api/gp/refusals/${selectedRecord.id}/download`;
                        window.open(url, '_blank');
                      }}
                    >
                      Скачать документ отказа
                    </Button>
                    {isEditing && (
                      <Button danger size="small" icon={<CloseCircleOutlined />} onClick={handleDeleteAttachment}>
                        Удалить
                      </Button>
                    )}
                  </Space>
                ) : (
                  isEditing ? (
                    <Upload beforeUpload={handleUploadAttachment} maxCount={1}>
                      <Button icon={<UploadOutlined />} size="small">Загрузить DOCX</Button>
                    </Upload>
                  ) : (
                    <span style={{ color: '#999' }}>Вложение отсутствует</span>
                  )
                )}
              </Descriptions.Item>
            </Descriptions>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default RefusalsTable;