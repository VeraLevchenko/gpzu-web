// frontend/src/components/GP/MidMifFlow.jsx
import React, { useState } from 'react';
import { Steps, Upload, Button, Card, Table, message, Spin, Result } from 'antd';
import { InboxOutlined, ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { midmifApi } from '../../services/api';
import './MidMifFlow.css';

const { Step } = Steps;
const { Dragger } = Upload;

const MidMifFlow = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [downloadReady, setDownloadReady] = useState(false);

  // ========== ШАГ 1: Загрузка и предпросмотр ========== //
  const handleFileUpload = async (file) => {
    setLoading(true);
    setUploadedFile(file);
    
    try {
      const response = await midmifApi.previewCoordinates(file);
      const data = response.data;
      
      setPreviewData(data);
      message.success('Координаты успешно извлечены');
      setCurrentStep(1);
      
    } catch (error) {
      message.error(
        error.response?.data?.detail || 'Ошибка обработки файла'
      );
      setUploadedFile(null);
    } finally {
      setLoading(false);
    }
    
    return false; // Предотвращаем автоматическую загрузку
  };

  // ========== ШАГ 2: Генерация и скачивание ========== //
  const handleGenerate = async () => {
    if (!uploadedFile) {
      message.error('Файл не загружен');
      return;
    }
    
    setLoading(true);
    
    try {
      const response = await midmifApi.generateMidMif(uploadedFile);
      
      // Скачиваем файл
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Имя файла из заголовка или fallback
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'coordinates.zip';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      message.success('Файлы MID/MIF успешно сгенерированы');
      setDownloadReady(true);
      setCurrentStep(2);
      
    } catch (error) {
      message.error(
        error.response?.data?.detail || 'Ошибка генерации файлов'
      );
    } finally {
      setLoading(false);
    }
  };

  // ========== СБРОС ========== //
  const handleReset = () => {
    setCurrentStep(0);
    setUploadedFile(null);
    setPreviewData(null);
    setDownloadReady(false);
  };

  // ========== КОЛОНКИ ТАБЛИЦЫ КООРДИНАТ ========== //
  const columns = [
    {
      title: '№',
      dataIndex: 'num',
      key: 'num',
      width: 80,
      align: 'center',
    },
    {
      title: 'Y (восток)',
      dataIndex: 'y',
      key: 'y',
      width: 200,
      align: 'right',
    },
    {
      title: 'X (север)',
      dataIndex: 'x',
      key: 'x',
      width: 200,
      align: 'right',
    },
  ];

  return (
    <div className="midmif-container">
      <div className="midmif-header">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/gp')} 
          size="large"
        >
          Назад
        </Button>
        <h1>Подготовка MID/MIF</h1>
      </div>

      <Card className="midmif-card">
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Загрузка ЕГРН" />
          <Step title="Предпросмотр" />
          <Step title="Готово" />
        </Steps>

        <Spin spinning={loading} size="large" tip="Обработка...">
          
          {/* ========== ШАГ 0: ЗАГРУЗКА ФАЙЛА ========== */}
          {currentStep === 0 && (
            <div className="upload-section">
              <Dragger
                accept=".xml,.zip"
                beforeUpload={handleFileUpload}
                showUploadList={false}
                multiple={false}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 64, color: '#1890ff' }} />
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

          {/* ========== ШАГ 1: ПРЕДПРОСМОТР КООРДИНАТ ========== */}
          {currentStep === 1 && previewData && (
            <div className="preview-section">
              <Card 
                title="Координаты земельного участка" 
                style={{ marginBottom: 24 }}
                extra={
                  <div style={{ color: '#8c8c8c', fontSize: '0.9rem' }}>
                    Кадастровый номер: <strong>{previewData.cadnum}</strong>
                  </div>
                }
              >
                <div style={{ marginBottom: 16, color: '#8c8c8c' }}>
                  ⚠️ {previewData.note}
                </div>
                
                <Table
                  columns={columns}
                  dataSource={previewData.coordinates.map((coord, idx) => ({
                    ...coord,
                    key: idx,
                  }))}
                  pagination={false}
                  size="small"
                  scroll={{ y: 400 }}
                  bordered
                />
                
                <div style={{ 
                  marginTop: 16, 
                  textAlign: 'center',
                  fontSize: '0.95rem',
                  color: '#595959'
                }}>
                  Всего точек: <strong>{previewData.total_points}</strong>
                </div>
              </Card>

              <Button
                type="primary"
                onClick={handleGenerate}
                size="large"
                block
                icon={<DownloadOutlined />}
              >
                Сформировать и скачать MID/MIF
              </Button>
            </div>
          )}

          {/* ========== ШАГ 2: ГОТОВО ========== */}
          {currentStep === 2 && downloadReady && (
            <Result
              status="success"
              title="Файлы MID/MIF успешно сформированы!"
              subTitle={
                <div style={{ fontSize: '1.05rem' }}>
                  <p>
                    Файлы автоматически загружены на ваш компьютер
                  </p>
                  <p style={{ color: '#8c8c8c', marginTop: 12 }}>
                    Кадастровый номер: <strong>{previewData?.cadnum}</strong>
                  </p>
                </div>
              }
              extra={[
                <Button 
                  key="again" 
                  onClick={handleReset}
                  size="large"
                >
                  Подготовить ещё
                </Button>,
                <Button 
                  key="back" 
                  onClick={() => navigate('/gp')}
                  size="large"
                >
                  Вернуться к модулям
                </Button>,
              ]}
            />
          )}

        </Spin>
      </Card>
    </div>
  );
};

export default MidMifFlow;