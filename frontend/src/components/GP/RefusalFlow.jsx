import React, { useState } from 'react';
import { 
  Steps, 
  Upload, 
  Button, 
  Card, 
  Descriptions, 
  message, 
  Spin, 
  Result,
  Select,
  Alert
} from 'antd';
import { 
  InboxOutlined, 
  ArrowLeftOutlined,
  CloseCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { parsersApi, refusalApi } from '../../services/api';
import './RefusalFlow.css';

const { Step } = Steps;
const { Dragger } = Upload;
const { Option } = Select;

// 5 причин отказа
const REFUSAL_REASONS = [
  {
    code: 'NO_RIGHTS',
    title: 'Отсутствие прав на земельный участок',
    description: 'Не представлены документы, подтверждающие право на земельный участок'
  },
  {
    code: 'NO_BORDERS',
    title: 'Земельный участок без границ',
    description: 'Границы земельного участка не установлены в ЕГРН'
  },
  {
    code: 'NOT_IN_CITY',
    title: 'Земельный участок не входит в границы города',
    description: 'Земельный участок расположен за пределами муниципального образования'
  },
  {
    code: 'OBJECT_NOT_EXISTS',
    title: 'Объект отсутствует на кадастровом учёте',
    description: 'Земельный участок с таким кадастровым номером отсутствует в ЕГРН'
  },
  {
    code: 'HAS_ACTIVE_GP',
    title: 'Имеется действующий градостроительный план',
    description: 'Ранее выданный градостроительный план не утратил силу'
  }
];

const RefusalFlow = () => {
  const navigate = useNavigate();
  
  // ========== STATE ========== //
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Данные из заявления
  const [applicationData, setApplicationData] = useState(null);
  
  // Данные из ЕГРН
  const [egrnData, setEgrnData] = useState(null);
  
  // Выбранная причина отказа
  const [selectedReason, setSelectedReason] = useState(null);
  
  // Результат генерации
  const [generatedFile, setGeneratedFile] = useState(null);

  // ========== ШАГ 1: ЗАГРУЗКА ЗАЯВЛЕНИЯ ========== //
  const handleApplicationUpload = async (file) => {
    setLoading(true);
    try {
      console.log('📄 Загрузка заявления:', file.name);
      
      const response = await parsersApi.parseApplication(file);
      const data = response.data.data;
      
      console.log('📄 Ответ от парсера заявления:', data);
      
      // === ИСПРАВЛЕНО: Сохраняем ВСЕ поля включая phone и email === //
      setApplicationData({
        number: data.number || '',
        date: data.date_formatted || data.date_text || data.date || '',
        applicant: data.applicant || '',
        cadnum: data.cadnum || '',
        purpose: data.purpose || '',
        phone: data.phone || '',    // === НОВОЕ === //
        email: data.email || ''     // === НОВОЕ === //
      });
      
      console.log('✅ Сохранены данные заявления:', {
        number: data.number,
        applicant: data.applicant,
        phone: data.phone,
        email: data.email
      });
      
      message.success('Заявление успешно обработано');
      setCurrentStep(1);
      
    } catch (error) {
      console.error('❌ Ошибка обработки заявления:', error);
      message.error(error.response?.data?.detail || 'Ошибка обработки заявления');
    } finally {
      setLoading(false);
    }
    return false;
  };

  // ========== ШАГ 2: ЗАГРУЗКА ЕГРН ========== //
  const handleEgrnUpload = async (file) => {
    setLoading(true);
    try {
      console.log('🗺️ Загрузка ЕГРН:', file.name);
      
      const response = await parsersApi.parseEgrn(file);
      const data = response.data.data;
      
      console.log('🗺️ Ответ от парсера ЕГРН:', data);
      
      setEgrnData({
        cadnum: data.cadnum || '',
        address: data.address || '',
        area: data.area || '',
        permitted_use: data.permitted_use || ''
      });
      
      message.success('ЕГРН успешно обработан');
      setCurrentStep(2);
      
    } catch (error) {
      console.error('❌ Ошибка обработки ЕГРН:', error);
      message.error(error.response?.data?.detail || 'Ошибка обработки ЕГРН');
    } finally {
      setLoading(false);
    }
    return false;
  };

  // ========== ШАГ 3: ВЫБОР ПРИЧИНЫ ========== //
  const handleReasonSelect = (reasonCode) => {
    const reason = REFUSAL_REASONS.find(r => r.code === reasonCode);
    setSelectedReason(reason);
  };

  const handleConfirmReason = () => {
    if (!selectedReason) {
      message.warning('Выберите причину отказа');
      return;
    }
    setCurrentStep(3);
  };

  // ========== ШАГ 4: ГЕНЕРАЦИЯ ДОКУМЕНТА ========== //
  const handleGenerate = async () => {
    if (!applicationData || !egrnData || !selectedReason) {
      message.error('Недостаточно данных для генерации');
      return;
    }
    
    setLoading(true);
    try {
      console.log('🔄 Отправка данных на генерацию отказа:');
      console.log('  Application:', applicationData);
      console.log('  EGRN:', egrnData);
      console.log('  Reason:', selectedReason.code);

      // Формируем дату в формате ДД.ММ.ГГГГ
      const today = new Date();
      const day = String(today.getDate()).padStart(2, '0');
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const year = today.getFullYear();
      const formattedDate = `${day}.${month}.${year}`;

      const requestData = {
        application: applicationData,
        egrn: egrnData,
        refusal: {
          date: formattedDate,  // Формат: 08.01.2026
          reason_code: selectedReason.code
        }
      };
      
      console.log('📤 Полный запрос:', JSON.stringify(requestData, null, 2));
      
      const response = await refusalApi.generate(requestData);
      
      // Извлекаем имя файла из заголовка
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'Otkaz.docx';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Скачиваем файл
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setGeneratedFile(filename);
      message.success('Отказ успешно сформирован');
      setCurrentStep(4);
      
    } catch (error) {
      console.error('❌ Ошибка генерации отказа:', error);
      console.error('❌ Ответ сервера:', error.response);
      message.error(error.response?.data?.detail || 'Ошибка генерации документа');
    } finally {
      setLoading(false);
    }
  };

  // ========== СБРОС ========== //
  const handleReset = () => {
    setCurrentStep(0);
    setApplicationData(null);
    setEgrnData(null);
    setSelectedReason(null);
    setGeneratedFile(null);
  };

  // ========== RENDER ========== //
  return (
    <div className="refusal-container">
      {/* Заголовок */}
      <div className="refusal-header">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/gp')} 
          size="large"
        >
          Назад
        </Button>
        <h1>Формирование отказа в выдаче ГПЗУ</h1>
      </div>

      {/* Основная карточка */}
      <Card className="refusal-card">
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Заявление" icon={<InboxOutlined />} />
          <Step title="ЕГРН" icon={<InboxOutlined />} />
          <Step title="Причина отказа" icon={<CloseCircleOutlined />} />
          <Step title="Проверка данных" icon={<WarningOutlined />} />
          <Step title="Готово" icon={<CloseCircleOutlined />} />
        </Steps>

        <Spin spinning={loading} size="large">
          
          {/* ШАГ 0: ЗАЯВЛЕНИЕ */}
          {currentStep === 0 && (
            <div className="upload-section">
              <Alert
                message="Шаг 1: Загрузите заявление"
                description="Из заявления будут извлечены: номер, дата, заявитель, телефон, email"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />
              <Dragger
                accept=".docx"
                beforeUpload={handleApplicationUpload}
                showUploadList={false}
                multiple={false}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />
                </p>
                <p className="ant-upload-text">
                  Перетащите файл заявления сюда или нажмите для выбора
                </p>
                <p className="ant-upload-hint">
                  Поддерживается только формат DOCX
                </p>
              </Dragger>
            </div>
          )}

          {/* ШАГ 1: ЕГРН */}
          {currentStep === 1 && (
            <div>
              <Card title="Данные заявления" size="small" style={{ marginBottom: 24 }}>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Номер">{applicationData?.number}</Descriptions.Item>
                  <Descriptions.Item label="Дата">{applicationData?.date}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель" span={2}>{applicationData?.applicant}</Descriptions.Item>
                  <Descriptions.Item label="Телефон">{applicationData?.phone || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Email">{applicationData?.email || '—'}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Alert
                message="Шаг 2: Загрузите выписку ЕГРН"
                description="Из ЕГРН будут извлечены: кадастровый номер, адрес, площадь, ВРИ"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Dragger
                accept=".xml"
                beforeUpload={handleEgrnUpload}
                showUploadList={false}
                multiple={false}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 64, color: '#52c41a' }} />
                </p>
                <p className="ant-upload-text">
                  Перетащите выписку ЕГРН сюда или нажмите для выбора
                </p>
                <p className="ant-upload-hint">
                  Поддерживается только формат XML
                </p>
              </Dragger>
            </div>
          )}

          {/* ШАГ 2: ВЫБОР ПРИЧИНЫ */}
          {currentStep === 2 && (
            <div>
              <Card title="Данные заявления" size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Номер">{applicationData?.number}</Descriptions.Item>
                  <Descriptions.Item label="Дата">{applicationData?.date}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель" span={2}>{applicationData?.applicant}</Descriptions.Item>
                  <Descriptions.Item label="Телефон">{applicationData?.phone || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Email">{applicationData?.email || '—'}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="Данные земельного участка" size="small" style={{ marginBottom: 24 }}>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Кадастровый номер" span={2}>{egrnData?.cadnum}</Descriptions.Item>
                  <Descriptions.Item label="Адрес" span={2}>{egrnData?.address}</Descriptions.Item>
                  <Descriptions.Item label="Площадь">{egrnData?.area} кв.м</Descriptions.Item>
                  <Descriptions.Item label="ВРИ">{egrnData?.permitted_use}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Alert
                message="Шаг 3: Выберите причину отказа"
                type="warning"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Select
                placeholder="Выберите причину отказа"
                style={{ width: '100%', marginBottom: 24 }}
                size="large"
                onChange={handleReasonSelect}
              >
                {REFUSAL_REASONS.map(reason => (
                  <Option key={reason.code} value={reason.code}>
                    <strong>{reason.title}</strong>
                    <div style={{ fontSize: '0.85rem', color: '#8c8c8c' }}>
                      {reason.description}
                    </div>
                  </Option>
                ))}
              </Select>

              <Button
                type="primary"
                size="large"
                block
                onClick={handleConfirmReason}
                disabled={!selectedReason}
              >
                Продолжить
              </Button>
            </div>
          )}

          {/* ШАГ 3: ПРОВЕРКА ДАННЫХ */}
          {currentStep === 3 && selectedReason && (
            <div>
              <Alert
                message="Проверьте данные перед формированием отказа"
                type="warning"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Card title="Данные заявления" size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Номер">{applicationData?.number}</Descriptions.Item>
                  <Descriptions.Item label="Дата">{applicationData?.date}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель" span={2}>{applicationData?.applicant}</Descriptions.Item>
                  <Descriptions.Item label="Телефон">{applicationData?.phone || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Email">{applicationData?.email || '—'}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="Данные земельного участка" size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Кадастровый номер" span={2}>{egrnData?.cadnum}</Descriptions.Item>
                  <Descriptions.Item label="Адрес" span={2}>{egrnData?.address}</Descriptions.Item>
                  <Descriptions.Item label="Площадь">{egrnData?.area} кв.м</Descriptions.Item>
                  <Descriptions.Item label="ВРИ">{egrnData?.permitted_use}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Card 
                title="Причина отказа" 
                size="small" 
                style={{ marginBottom: 24 }}
                headStyle={{ backgroundColor: '#fff1f0', color: '#cf1322' }}
              >
                <p style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>
                  {selectedReason.title}
                </p>
                <p style={{ color: '#8c8c8c', marginBottom: 0 }}>
                  {selectedReason.description}
                </p>
              </Card>

              <Button
                type="primary"
                danger
                size="large"
                block
                icon={<CloseCircleOutlined />}
                onClick={handleGenerate}
              >
                Сформировать отказ
              </Button>
            </div>
          )}

          {/* ШАГ 4: РЕЗУЛЬТАТ */}
          {currentStep === 4 && generatedFile && (
            <Result
              status="warning"
              title="Отказ успешно сформирован"
              subTitle={
                <div>
                  <p style={{ fontSize: '1.05rem', marginBottom: 16 }}>
                    Файл: <strong>{generatedFile}</strong>
                  </p>
                  <p style={{ color: '#8c8c8c' }}>
                    Документ автоматически загружен на ваш компьютер
                  </p>
                </div>
              }
              extra={[
                <Button 
                  key="reset" 
                  onClick={handleReset}
                  size="large"
                >
                  Создать ещё один отказ
                </Button>,
                <Button 
                  key="back" 
                  onClick={() => navigate('/gp')}
                  size="large"
                >
                  Вернуться к модулям
                </Button>
              ]}
            />
          )}

        </Spin>
      </Card>
    </div>
  );
};

export default RefusalFlow;