import React, { useState } from 'react';
import { Steps, Upload, Button, Card, Descriptions, message, Spin, Result } from 'antd';
import { InboxOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { kaitenApi } from '../../services/api';
import './KaitenFlow.css';

const { Step } = Steps;
const { Dragger } = Upload;

const KaitenFlow = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [cardResult, setCardResult] = useState(null);

  const handleFileUpload = async (file) => {
    setLoading(true);
    try {
      const response = await kaitenApi.parseApplication(file);
      setParsedData(response.data.data);
      message.success('Заявление успешно обработано');
      setCurrentStep(1);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка обработки файла');
    } finally {
      setLoading(false);
    }
    return false;
  };

  const handleCreateTask = async () => {
    setLoading(true);
    try {
      const response = await kaitenApi.createTask({ application: parsedData });
      setCardResult(response.data);
      message.success('Задача успешно создана в Kaiten');
      setCurrentStep(2);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка создания задачи');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setParsedData(null);
    setCardResult(null);
  };

  return (
    <div className="kaiten-container">
      <div className="kaiten-header">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/gp')} size="large">Назад</Button>
        <h1>Создание задачи в Kaiten</h1>
      </div>
      <Card className="kaiten-card">
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Загрузка заявления" />
          <Step title="Подтверждение" />
          <Step title="Готово" />
        </Steps>
        <Spin spinning={loading} size="large">
          {currentStep === 0 && (
            <div className="upload-section">
              <Dragger accept=".docx" beforeUpload={handleFileUpload} showUploadList={false} multiple={false}>
                <p className="ant-upload-drag-icon"><InboxOutlined style={{ fontSize: 64, color: '#1890ff' }} /></p>
                <p className="ant-upload-text">Перетащите файл заявления сюда или нажмите для выбора</p>
                <p className="ant-upload-hint">Поддерживается только формат DOCX</p>
              </Dragger>
            </div>
          )}
          {currentStep === 1 && parsedData && (
            <div className="confirmation-section">
              <Card title="Проверьте данные заявления" style={{ marginBottom: 24 }}>
                <Descriptions column={1} bordered>
                  <Descriptions.Item label="Номер заявления">{parsedData.number || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Дата заявления">{parsedData.date_text || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель">{parsedData.applicant || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Кадастровый номер">{parsedData.cadnum || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Цель использования">{parsedData.purpose || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Срок (план)">{parsedData.service_date || '—'}</Descriptions.Item>
                </Descriptions>
              </Card>
              <Button type="primary" onClick={handleCreateTask} size="large" block>Создать задачу в Kaiten</Button>
            </div>
          )}
          {currentStep === 2 && cardResult && (
            <Result status="success" title="Задача успешно создана в Kaiten!"
              subTitle={<div><p style={{ fontSize: '1.1rem', marginBottom: 24 }}>ID карточки: <strong>{cardResult.card_id}</strong></p>
              <a href={cardResult.card_url} target="_blank" rel="noopener noreferrer"><Button type="primary" size="large">Открыть карточку в Kaiten</Button></a></div>}
              extra={[<Button key="reset" onClick={handleReset} size="large">Создать ещё одну задачу</Button>, <Button key="back" onClick={() => navigate('/gp')} size="large">Вернуться к модулям</Button>]} />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default KaitenFlow;
