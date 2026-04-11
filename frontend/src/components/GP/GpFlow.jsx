import React, { useState } from 'react';
import { 
  Steps, 
  Upload,
  Form, 
  Input, 
  Button, 
  Card, 
  message, 
  Spin, 
  Result,
  Radio,
  Table,
  Descriptions,
  Divider,
  Tag
} from 'antd';
import { 
  ArrowLeftOutlined, 
  FileTextOutlined,
  InboxOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { parsersApi, gradplanApi } from '../../services/api';
import './GpFlow.css';

const { Step } = Steps;
const { Dragger } = Upload;

const GpFlow = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Данные из парсеров
  const [applicationMode, setApplicationMode] = useState('file');
  const [applicationData, setApplicationData] = useState(null);
  const [egrnData, setEgrnData] = useState(null);
  const [spatialData, setSpatialData] = useState(null);
  
  // Результат
  const [generatedFile, setGeneratedFile] = useState(null);

  // ============================================
  // ШАГ 1: ОБРАБОТКА ЗАЯВЛЕНИЯ
  // ============================================
  const handleApplicationFile = async (file) => {
    setLoading(true);
    try {
      const response = await parsersApi.parseApplication(file);
      const data = response.data.data;
      
      setApplicationData({
        number: data.number || '',
        date: data.date_text || data.date || '',
        applicant: data.applicant || ''
      });
      
      message.success('Заявление успешно обработано');
      setCurrentStep(1);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка обработки заявления');
    } finally {
      setLoading(false);
    }
    return false;
  };

  const handleManualApplication = (values) => {
    setApplicationData({
      number: values.app_number,
      date: values.app_date,
      applicant: values.applicant
    });
    message.success('Данные заявления введены');
    setCurrentStep(1);
  };

  // ============================================
  // ШАГ 2: ОБРАБОТКА ЕГРН
  // ============================================
  const handleEgrnFile = async (file) => {
    setLoading(true);
    try {
      const response = await parsersApi.parseEgrn(file);
      const data = response.data.data;
      
      setEgrnData({
        cadnum: data.cadnum || '',
        address: data.address || '',
        area: data.area || '',
        region: data.region || '',
        municipality: data.municipality || '',
        settlement: data.settlement || '',
        permitted_use: data.permitted_use || '',
        coordinates: data.coordinates || []
      });
      
      message.success('ЕГРН успешно обработан');
      
      // Автоматически запускаем пространственный анализ
      await performSpatialAnalysis(data.cadnum, data.coordinates);
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка обработки ЕГРН');
      setLoading(false);
    }
    return false;
  };

  // ============================================
  // ШАГ 3: ПРОСТРАНСТВЕННЫЙ АНАЛИЗ
  // ============================================
  const performSpatialAnalysis = async (cadnum, coordinates) => {
    try {
      const response = await parsersApi.spatialAnalysis({
        cadnum: cadnum,
        coordinates: coordinates
      });
      
      const data = response.data.data;
      
      setSpatialData({
        zone: data.zone || { code: '', name: '' },
        district: data.district || { code: '', name: '' },
        capital_objects: data.capital_objects || [],
        zouit: data.zouit || [],
        planning_project: data.planning_project || {
          exists: false,
          decision_full: 'Документация по планировке территории не утверждена'
        },
        ago_index: data.ago_index || null
      });
      
      message.success('Пространственный анализ выполнен');
      setCurrentStep(2);
    } catch (error) {
      message.error('Ошибка пространственного анализа');
      console.error(error);
      
      // Устанавливаем пустые данные
      setSpatialData({
        zone: { code: '', name: '' },
        district: { code: '', name: '' },  // НОВОЕ: пустой район
        capital_objects: [],
        zouit: [],
        planning_project: {
          exists: false,
          decision_full: 'Документация по планировке территории не утверждена'
        }
      });
      setCurrentStep(2);
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // ШАГ 4: ГЕНЕРАЦИЯ ДОКУМЕНТА
  // ============================================
  const handleGenerate = async () => {
    setLoading(true);
    try {
      const requestData = {
        application: applicationData,
        parcel: egrnData,
        zone: spatialData.zone,
        district: spatialData.district,
        capital_objects: spatialData.capital_objects,
        planning_project: spatialData.planning_project,
        zouit: spatialData.zouit,
        ago_index: spatialData.ago_index || null
      };

      const response = await gradplanApi.generate(requestData);
      
      if (response.data.filename) {
        setGeneratedFile(response.data.filename);
        message.success('Градостроительный план успешно сформирован');
        setCurrentStep(3);
      } else {
        throw new Error('Не получено имя файла');
      }
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка генерации документа');
      console.error('Ошибка:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!generatedFile) return;
    
    setLoading(true);
    try {
      await gradplanApi.download(generatedFile);
      message.success('Файл успешно скачан');
    } catch (error) {
      message.error('Ошибка скачивания файла');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setApplicationData(null);
    setEgrnData(null);
    setSpatialData(null);
    setGeneratedFile(null);
    setApplicationMode('file');
    form.resetFields();
  };

  // ============================================
  // КОЛОНКИ ДЛЯ ТАБЛИЦ
  // ============================================
  const coordColumns = [
    { title: '№', dataIndex: 'num', key: 'num', width: 60 },
    { title: 'X', dataIndex: 'x', key: 'x' },
    { title: 'Y', dataIndex: 'y', key: 'y' }
  ];

  const oksColumns = [
    { title: '№', key: 'index', render: (_, __, index) => index + 1, width: 60 },
    { title: 'Кадастровый номер', dataIndex: 'cadnum', key: 'cadnum' }
  ];

  // ============================================
  // НОВОЕ: ФУНКЦИЯ ФОРМАТИРОВАНИЯ ПЛОЩАДЕЙ
  // ============================================
  const formatArea = (area) => {
    if (!area || area <= 0) return '—';
    
    const numArea = parseFloat(area);
    if (isNaN(numArea)) return '—';
    
    // Форматирование в русском стиле: 1024.46 → "1 024,46 кв.м"
    return numArea.toLocaleString('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }) + ' кв.м';
  };

  // ============================================
  // ОБНОВЛЁННЫЕ КОЛОНКИ ТАБЛИЦЫ ЗОУИТ (с площадями)
  // ============================================
  const zouitColumns = [
    { 
      title: 'Наименование', 
      dataIndex: 'name', 
      key: 'name',
      width: '45%'
    },
    { 
      title: 'Реестровый номер', 
      dataIndex: 'registry_number', 
      key: 'registry_number',
      width: '30%'
    },
    { 
      title: 'Площадь пересечения', 
      dataIndex: 'area', 
      key: 'area',
      width: '25%',
      render: (area) => formatArea(area),
      align: 'right'
    }
  ];

  // ============================================
  // ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ РАЙОНА
  // ============================================
  const getDistrictDisplay = (district) => {
    if (!district) return '—';
    if (district.name) {
      return district.code ? `${district.name} (${district.code})` : district.name;
    }
    if (district.code) {
      return `Район ${district.code}`;
    }
    return 'Район не определён';
  };

  // ============================================
  // РЕНДЕР
  // ============================================
  return (
    <div className="gpflow-container">
      <div className="gpflow-header">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/gp')} 
          size="large"
        >
          Назад
        </Button>
        <h1>Формирование градостроительного плана</h1>
      </div>

      <Card className="gpflow-card">
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Заявление" />
          <Step title="ЕГРН" />
          <Step title="Проверка данных" />
          <Step title="Готово" />
        </Steps>

        <Spin spinning={loading} size="large">
          
          {/* ШАГ 0: ЗАЯВЛЕНИЕ */}
          {currentStep === 0 && (
            <div>
              <Card title="📋 Данные заявления" style={{ marginBottom: 24 }}>
                <Radio.Group 
                  value={applicationMode} 
                  onChange={(e) => setApplicationMode(e.target.value)}
                  style={{ marginBottom: 24 }}
                >
                  <Radio.Button value="file">Загрузить файл DOCX</Radio.Button>
                  <Radio.Button value="manual">Ввести вручную</Radio.Button>
                </Radio.Group>

                {applicationMode === 'file' ? (
                  <Dragger
                    accept=".docx"
                    beforeUpload={handleApplicationFile}
                    showUploadList={false}
                    multiple={false}
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined style={{ fontSize: 64, color: '#722ed1' }} />
                    </p>
                    <p className="ant-upload-text">Перетащите заявление сюда или нажмите для выбора</p>
                    <p className="ant-upload-hint">Поддерживается только формат DOCX</p>
                  </Dragger>
                ) : (
                  <Form layout="vertical" onFinish={handleManualApplication}>
                    <Form.Item
                      label="Номер заявления"
                      name="app_number"
                      rules={[{ required: true, message: 'Введите номер' }]}
                    >
                      <Input placeholder="001/2025" />
                    </Form.Item>
                    <Form.Item
                      label="Дата заявления"
                      name="app_date"
                      rules={[{ required: true, message: 'Введите дату' }]}
                    >
                      <Input placeholder="01.12.2025" />
                    </Form.Item>
                    <Form.Item
                      label="Заявитель"
                      name="applicant"
                      rules={[{ required: true, message: 'Введите ФИО' }]}
                    >
                      <Input placeholder="Иванов Иван Иванович" />
                    </Form.Item>
                    <Form.Item>
                      <Button type="primary" htmlType="submit" block size="large">
                        Продолжить
                      </Button>
                    </Form.Item>
                  </Form>
                )}
              </Card>
            </div>
          )}

          {/* ШАГ 1: ЕГРН */}
          {currentStep === 1 && (
            <div>
              <Card title="📄 Данные заявления" style={{ marginBottom: 24 }}>
                <Descriptions column={3} bordered>
                  <Descriptions.Item label="Номер">{applicationData?.number}</Descriptions.Item>
                  <Descriptions.Item label="Дата">{applicationData?.date}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель">{applicationData?.applicant}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="🏞️ Выписка из ЕГРН" style={{ marginBottom: 24 }}>
                <Dragger
                  accept=".xml"
                  beforeUpload={handleEgrnFile}
                  showUploadList={false}
                  multiple={false}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined style={{ fontSize: 64, color: '#52c41a' }} />
                  </p>
                  <p className="ant-upload-text">Загрузите выписку ЕГРН</p>
                  <p className="ant-upload-hint">Поддерживается формат XML</p>
                </Dragger>
              </Card>
            </div>
          )}

          {/* ШАГ 2: ПРОВЕРКА ДАННЫХ */}
          {currentStep === 2 && egrnData && spatialData && (
            <div>
              <Card title="📄 Заявление" size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={3} size="small">
                  <Descriptions.Item label="Номер">{applicationData?.number}</Descriptions.Item>
                  <Descriptions.Item label="Дата">{applicationData?.date}</Descriptions.Item>
                  <Descriptions.Item label="Заявитель">{applicationData?.applicant}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="🏞️ Земельный участок" size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Кадастровый номер">{egrnData.cadnum}</Descriptions.Item>
                  <Descriptions.Item label="Площадь">{egrnData.area} кв.м</Descriptions.Item>
                  <Descriptions.Item label="Адрес" span={2}>{egrnData.address}</Descriptions.Item>
                  {/* НОВОЕ: Показываем район */}
                  <Descriptions.Item label="Район" span={2}>
                    <Tag icon={<EnvironmentOutlined />} color="blue">
                      {getDistrictDisplay(spatialData.district)}
                    </Tag>
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title={`📐 Координаты (${egrnData.coordinates?.length || 0} точек)`} size="small" style={{ marginBottom: 16 }}>
                <Table 
                  dataSource={egrnData.coordinates}
                  columns={coordColumns}
                  pagination={false}
                  size="small"
                  scroll={{ y: 200 }}
                  rowKey={(record) => record.num}
                />
              </Card>

              <Card title="📍 Территориальная зона" size="small" style={{ marginBottom: 16 }}>
                {spatialData.zone?.code ? (
                  <Descriptions column={2} size="small" bordered>
                    <Descriptions.Item label="Код">{spatialData.zone.code}</Descriptions.Item>
                    <Descriptions.Item label="Наименование">{spatialData.zone.name}</Descriptions.Item>
                  </Descriptions>
                ) : (
                  <p>Территориальная зона не определена</p>
                )}
              </Card>

              {/* НОВОЕ: ПРОЕКТ ПЛАНИРОВКИ */}
              <Card title="📋 Проект планировки территории" size="small" style={{ marginBottom: 16 }}>
                {spatialData.planning_project?.exists ? (
                  <Descriptions column={1} size="small" bordered>
                    {spatialData.planning_project.project_type && (
                      <Descriptions.Item label="Вид">
                        {spatialData.planning_project.project_type}
                      </Descriptions.Item>
                    )}
                    {spatialData.planning_project.project_name && (
                      <Descriptions.Item label="Название">
                        {spatialData.planning_project.project_name}
                      </Descriptions.Item>
                    )}
                    {(spatialData.planning_project.decision_date || spatialData.planning_project.decision_number) && (
                      <Descriptions.Item label="Распоряжение">
                        {spatialData.planning_project.decision_date && `от ${spatialData.planning_project.decision_date} `}
                        {spatialData.planning_project.decision_number && `№ ${spatialData.planning_project.decision_number}`}
                      </Descriptions.Item>
                    )}
                    {spatialData.planning_project.decision_full && (
                      <Descriptions.Item label="Для документа">
                        <span style={{ fontSize: '0.9em', color: '#595959' }}>
                          {spatialData.planning_project.decision_full}
                        </span>
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                ) : (
                  <p style={{ color: '#8c8c8c', fontStyle: 'italic' }}>
                    Документация по планировке территории не утверждена
                  </p>
                )}
              </Card>

              <Card title="🏗️ Объекты капитального строительства" size="small" style={{ marginBottom: 16 }}>
                {spatialData.capital_objects?.length > 0 ? (
                  <Table 
                    dataSource={spatialData.capital_objects}
                    columns={oksColumns}
                    pagination={false}
                    size="small"
                    rowKey={(record) => record.cadnum}
                  />
                ) : (
                  <p>Объекты не обнаружены</p>
                )}
              </Card>

              {/* АГО */}
              <Card title="🏛️ Архитектурно-градостроительный облик (АГО)" size="small" style={{ marginBottom: 16 }}>
                {spatialData.ago_index ? (
                  <Descriptions column={1} size="small" bordered>
                    <Descriptions.Item label="Пересечение">
                      <Tag color="orange">Участок входит в границы АГО</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Индекс зоны">
                      <strong>{spatialData.ago_index}</strong>
                    </Descriptions.Item>
                  </Descriptions>
                ) : (
                  <p style={{ color: '#8c8c8c', fontStyle: 'italic' }}>
                    Территория АГО не пересекается с земельным участком
                  </p>
                )}
              </Card>

              {/* ОБНОВЛЁННАЯ ТАБЛИЦА ЗОУИТ (с площадями) */}
              <Card title="⚠️ ЗОУИТ" size="small" style={{ marginBottom: 16 }}>
                {spatialData.zouit?.length > 0 ? (
                  <>
                    <Table 
                      dataSource={spatialData.zouit}
                      columns={zouitColumns}
                      pagination={false}
                      size="small"
                      rowKey={(record) => record.registry_number || record.name}
                    />
                    <p style={{ 
                      marginTop: 12, 
                      fontSize: '0.85rem', 
                      color: '#8c8c8c',
                      fontStyle: 'italic' 
                    }}>
                      * Площадь пересечения — часть земельного участка, попадающая в границы ЗОУИТ
                    </p>
                  </>
                ) : (
                  <p>ЗОУИТ не обнаружены</p>
                )}
              </Card>

              <Divider />

              <Button 
                type="primary" 
                size="large" 
                block
                icon={<FileTextOutlined />}
                onClick={handleGenerate}
              >
                Сформировать градостроительный план
              </Button>
            </div>
          )}

          {/* ШАГ 3: РЕЗУЛЬТАТ */}
          {currentStep === 3 && (
            <Result
              status="success"
              title="Градостроительный план успешно сформирован!"
              subTitle={`Файл: ${generatedFile}`}
              extra={[
                <Button 
                  type="primary" 
                  size="large" 
                  onClick={handleDownload}
                  key="download"
                >
                  Скачать документ
                </Button>,
                <Button 
                  key="reset" 
                  onClick={handleReset} 
                  size="large"
                >
                  Создать новый
                </Button>,
                <Button 
                  key="back" 
                  onClick={() => navigate('/gp')} 
                  size="large"
                >
                  К модулям
                </Button>
              ]}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default GpFlow;
