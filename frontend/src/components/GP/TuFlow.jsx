// frontend/src/components/GP/TuFlow.jsx
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
  Radio,
  Form,
  Input,
  Space,
  Typography
} from 'antd';
import { 
  InboxOutlined, 
  ArrowLeftOutlined,
  FileTextOutlined,
  FormOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { tuApi } from '../../services/api';
import './TuFlow.css';

const { Step } = Steps;
const { Dragger } = Upload;
const { Title, Text } = Typography;

/**
 * Компонент для подготовки запросов технических условий (ТУ)
 * 
 * Функционал:
 * 1. Выбор режима ввода (через заявление или вручную)
 * 2. Парсинг заявления DOCX (автоматическое извлечение данных)
 * 3. Парсинг выписки ЕГРН (получение КН, адреса, площади, ВРИ)
 * 4. Предпросмотр данных перед генерацией
 * 5. Генерация 3 запросов ТУ с автоматической регистрацией
 * 6. Скачивание ZIP архива с документами
 */
const TuFlow = () => {
  const navigate = useNavigate();
  
  // ========== STATE ========== //
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [inputMode, setInputMode] = useState(null); // 'auto' или 'manual'
  
  // Данные из заявления (режим 'auto')
  const [applicationData, setApplicationData] = useState(null);
  
  // Данные из ЕГРН
  const [egrnData, setEgrnData] = useState(null);
  
  // Данные для ручного ввода (режим 'manual')
  const [manualData, setManualData] = useState({
    app_number: '',
    app_date: '',
    applicant: '',
  });
  
  // Объединённые данные для генерации
  const [finalData, setFinalData] = useState(null);
  
  // Результат генерации
  const [downloadReady, setDownloadReady] = useState(false);

  // ========== ОБРАБОТЧИКИ ========== //

  /**
   * Выбор режима ввода данных
   */
  const handleModeSelect = (mode) => {
    setInputMode(mode);
    setCurrentStep(1);
  };

  /**
   * Загрузка и парсинг заявления (режим 'auto')
   */
  const handleApplicationUpload = async (file) => {
    setLoading(true);
    try {
      const response = await tuApi.parseApplication(file);
      setApplicationData(response.data.data);
      message.success('Заявление успешно обработано');
      setCurrentStep(2);
    } catch (error) {
      message.error(
        error.response?.data?.detail || 
        'Ошибка обработки заявления'
      );
    } finally {
      setLoading(false);
    }
    return false; // Предотвращаем автозагрузку
  };

  /**
   * Отправка формы ручного ввода (режим 'manual')
   */
  const handleManualSubmit = (values) => {
    setManualData(values);
    message.success('Данные заявления сохранены');
    setCurrentStep(2);
  };

  /**
   * Загрузка и парсинг выписки ЕГРН
   */
  const handleEgrnUpload = async (file) => {
    setLoading(true);
    try {
      const response = await tuApi.parseEgrn(file);
      const egrn = response.data.data;
      setEgrnData(egrn);
      
      // Объединяем данные заявления и ЕГРН
      const combined = {
        cadnum: egrn.cadnum || '',
        address: egrn.address || '',
        area: egrn.area || '',
        vri: egrn.permitted_use || '',
        app_number: inputMode === 'auto' 
          ? (applicationData?.number || '') 
          : manualData.app_number,
        app_date: inputMode === 'auto'
          ? (applicationData?.date_text || '')
          : manualData.app_date,
        applicant: inputMode === 'auto'
          ? (applicationData?.applicant || '')
          : manualData.applicant,
      };
      
      setFinalData(combined);
      message.success('Выписка ЕГРН успешно обработана');
      setCurrentStep(3);
    } catch (error) {
      message.error(
        error.response?.data?.detail || 
        'Ошибка обработки выписки ЕГРН'
      );
    } finally {
      setLoading(false);
    }
    return false;
  };

  /**
   * Генерация запросов ТУ и скачивание ZIP
   */
  const handleGenerate = async () => {
    if (!finalData) {
      message.error('Данные не готовы для генерации');
      return;
    }

    setLoading(true);
    try {
      const response = await tuApi.generateTu(finalData);
      
      // Извлекаем имя файла из заголовка Content-Disposition
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'TU_documents.zip';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Создаём blob и скачиваем
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      message.success('Запросы ТУ успешно сформированы и зарегистрированы!');
      setDownloadReady(true);
      setCurrentStep(4);
    } catch (error) {
      message.error(
        error.response?.data?.detail || 
        'Ошибка генерации запросов ТУ'
      );
    } finally {
      setLoading(false);
    }
  };

  /**
   * Сброс состояния (начать заново)
   */
  const handleReset = () => {
    setCurrentStep(0);
    setInputMode(null);
    setApplicationData(null);
    setEgrnData(null);
    setManualData({ app_number: '', app_date: '', applicant: '' });
    setFinalData(null);
    setDownloadReady(false);
  };

  // ========== RENDER ========== //

  return (
    <div className="tu-container">
      {/* Шапка */}
      <div className="tu-header">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/gp')} 
          size="large"
        >
          Назад
        </Button>
        <h1>Подготовка запросов ТУ</h1>
      </div>

      {/* Основная карточка */}
      <Card className="tu-card">
        {/* Steps индикатор */}
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Режим ввода" icon={<FormOutlined />} />
          <Step title="Данные заявления" icon={<FileTextOutlined />} />
          <Step title="Выписка ЕГРН" icon={<InboxOutlined />} />
          <Step title="Подтверждение" icon={<CheckCircleOutlined />} />
          <Step title="Готово" icon={<CheckCircleOutlined />} />
        </Steps>

        <Spin spinning={loading} size="large">
          {/* ШАГ 0: Выбор режима */}
          {currentStep === 0 && (
            <div className="mode-selection">
              <Title level={3} style={{ textAlign: 'center', marginBottom: 32 }}>
                Выберите способ ввода данных
              </Title>
              
              <div className="mode-cards">
                {/* Режим: Через заявление */}
                <Card 
                  hoverable
                  className="mode-card"
                  onClick={() => handleModeSelect('auto')}
                >
                  <FileTextOutlined style={{ fontSize: 64, color: '#1890ff' }} />
                  <Title level={4}>Через файл заявления</Title>
                  <Text type="secondary">
                    Автоматическое извлечение данных из DOCX файла заявления
                  </Text>
                  <ul style={{ textAlign: 'left', marginTop: 16 }}>
                    <li>Номер заявления</li>
                    <li>Дата заявления</li>
                    <li>Заявитель</li>
                    <li>Кадастровый номер</li>
                  </ul>
                </Card>

                {/* Режим: Ручной ввод */}
                <Card 
                  hoverable
                  className="mode-card"
                  onClick={() => handleModeSelect('manual')}
                >
                  <FormOutlined style={{ fontSize: 64, color: '#52c41a' }} />
                  <Title level={4}>Ручной ввод</Title>
                  <Text type="secondary">
                    Заполнение данных вручную через форму
                  </Text>
                  <ul style={{ textAlign: 'left', marginTop: 16 }}>
                    <li>Номер заявления</li>
                    <li>Дата заявления</li>
                    <li>Заявитель</li>
                  </ul>
                </Card>
              </div>
            </div>
          )}

          {/* ШАГ 1: Данные заявления */}
          {currentStep === 1 && inputMode === 'auto' && (
            <div className="upload-section">
              <Title level={4} style={{ marginBottom: 24 }}>
                Шаг 1: Загрузите файл заявления
              </Title>
              <Dragger
                accept=".docx"
                beforeUpload={handleApplicationUpload}
                showUploadList={false}
                multiple={false}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 64, color: '#1890ff' }} />
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

          {currentStep === 1 && inputMode === 'manual' && (
            <div className="manual-form-section">
              <Title level={4} style={{ marginBottom: 24 }}>
                Шаг 1: Введите данные заявления вручную
              </Title>
              <Form
                layout="vertical"
                onFinish={handleManualSubmit}
                initialValues={manualData}
                size="large"
              >
                <Form.Item
                  label="Номер заявления"
                  name="app_number"
                  rules={[{ required: true, message: 'Введите номер заявления' }]}
                >
                  <Input placeholder="Например: 6422028095" />
                </Form.Item>

                <Form.Item
                  label="Дата заявления"
                  name="app_date"
                  rules={[{ required: true, message: 'Введите дату заявления' }]}
                >
                  <Input placeholder="Например: 15.11.2025" />
                </Form.Item>

                <Form.Item
                  label="Заявитель"
                  name="applicant"
                  rules={[{ required: true, message: 'Введите заявителя' }]}
                >
                  <Input placeholder="ФИО или наименование организации" />
                </Form.Item>

                <Form.Item>
                  <Button type="primary" htmlType="submit" block size="large">
                    Продолжить
                  </Button>
                </Form.Item>
              </Form>
            </div>
          )}

          {/* ШАГ 2: Выписка ЕГРН */}
          {currentStep === 2 && (
            <div className="upload-section">
              <Title level={4} style={{ marginBottom: 24 }}>
                Шаг 2: Загрузите выписку ЕГРН
              </Title>
              <Dragger
                accept=".xml,.zip"
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
                  Поддерживаются форматы XML и ZIP
                </p>
              </Dragger>
            </div>
          )}

          {/* ШАГ 3: Подтверждение */}
          {currentStep === 3 && finalData && (
            <div className="confirmation-section">
              <Title level={4} style={{ marginBottom: 24 }}>
                Проверьте данные перед формированием запросов
              </Title>
              
              <Card title="Данные заявления" style={{ marginBottom: 16 }}>
                <Descriptions column={1} bordered>
                  <Descriptions.Item label="Номер заявления">
                    {finalData.app_number || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Дата заявления">
                    {finalData.app_date || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Заявитель">
                    {finalData.applicant || '—'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="Данные земельного участка" style={{ marginBottom: 24 }}>
                <Descriptions column={1} bordered>
                  <Descriptions.Item label="Кадастровый номер">
                    {finalData.cadnum || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Адрес">
                    {finalData.address || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Площадь">
                    {finalData.area ? `${finalData.area} кв.м` : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="ВРИ">
                    {finalData.vri || '—'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Card 
                style={{ 
                  marginBottom: 24,
                  backgroundColor: '#e6f7ff',
                  borderColor: '#1890ff'
                }}
              >
                <Space direction="vertical" size={8}>
                  <Text strong style={{ fontSize: 16 }}>
                    📋 Будут сформированы 3 запроса ТУ:
                  </Text>
                  <Text>1. Запрос в ООО «Водоканал»</Text>
                  <Text>2. Запрос в филиал ООО «Газпром газораспределение Сибирь»</Text>
                  <Text>3. Запрос в ООО «ЭнергоТранзит», ООО «НТСК»</Text>
                  <Text type="secondary" style={{ marginTop: 8 }}>
                    Каждому запросу будет автоматически присвоен исходящий номер 
                    и внесена запись в журнал регистрации.
                  </Text>
                </Space>
              </Card>

              <Button 
                type="primary" 
                onClick={handleGenerate}
                size="large"
                block
              >
                Сформировать и скачать запросы ТУ
              </Button>
            </div>
          )}

          {/* ШАГ 4: Результат */}
          {currentStep === 4 && downloadReady && (
            <Result
              status="success"
              title="Запросы ТУ успешно сформированы!"
              subTitle={
                <div>
                  <p style={{ fontSize: '1.1rem', marginBottom: 24 }}>
                    ZIP архив с 3 документами скачан на ваш компьютер.
                  </p>
                  <Space direction="vertical" size={8}>
                    <Text>✅ Документы зарегистрированы в журнале Excel</Text>
                    <Text>✅ Присвоены уникальные исходящие номера</Text>
                    <Text>✅ Готовы к отправке в РСО</Text>
                  </Space>
                </div>
              }
              extra={[
                <Button 
                  key="reset" 
                  onClick={handleReset}
                  size="large"
                >
                  Подготовить ещё запросы
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

export default TuFlow;