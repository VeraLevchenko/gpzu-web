// frontend/src/components/GP/WorkspaceFlow.jsx
import React, { useState } from 'react';
import { 
  Steps, 
  Upload, 
  Button, 
  Card, 
  message, 
  Spin, 
  Result,
  Alert
} from 'antd';
import { 
  InboxOutlined, 
  ArrowLeftOutlined,
  DownloadOutlined,
  FolderOpenOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './WorkspaceFlow.css';

const { Dragger } = Upload;
const { Step } = Steps;

/**
 * Компонент для генерации рабочего набора MapInfo из ЕГРН
 */
const WorkspaceFlow = () => {
  const navigate = useNavigate();
  
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [egrnFile, setEgrnFile] = useState(null);
  const [generatedFileName, setGeneratedFileName] = useState(null);

  // ========== Загрузка ЕГРН ========== //
  const handleEgrnUpload = (file) => {
    if (!file.name.toLowerCase().endsWith('.xml')) {
      message.error('Пожалуйста, загрузите XML файл выписки ЕГРН');
      return false;
    }
    
    setEgrnFile(file);
    message.success('Файл ЕГРН загружен');
    return false;
  };

  const handleRemoveEgrn = () => {
    setEgrnFile(null);
  };

  const handleNextStep = () => {
    if (!egrnFile) {
      message.warning('Загрузите файл ЕГРН');
      return;
    }
    setCurrentStep(1);
  };

  // ========== Генерация архива ========== //
  const handleGenerate = async () => {
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('egrn_file', egrnFile);

      const response = await fetch('/api/gp/workspace/generate', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Basic ${btoa(
            `${JSON.parse(localStorage.getItem('auth')).username}:${JSON.parse(localStorage.getItem('auth')).password}`
          )}`
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка генерации');
      }

      // Извлекаем имя файла из заголовка
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'workspace.zip';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Скачиваем файл
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setGeneratedFileName(filename);
      message.success('Рабочий набор успешно сгенерирован');
      setCurrentStep(2);

    } catch (error) {
      console.error('❌ Ошибка генерации:', error);
      message.error(error.message || 'Ошибка генерации рабочего набора');
    } finally {
      setLoading(false);
    }
  };

  // ========== Сброс ========== //
  const handleReset = () => {
    setCurrentStep(0);
    setEgrnFile(null);
    setGeneratedFileName(null);
  };

  // ========== RENDER ========== //
  return (
    <div className="workspace-container">
      {/* Заголовок */}
      <div className="workspace-header">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/gp')} 
          size="large"
        >
          Назад
        </Button>
        <h1>Генерация рабочего набора MapInfo</h1>
      </div>

      {/* Основная карточка */}
      <Card className="workspace-card">
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="Загрузка ЕГРН" description="XML файл выписки" />
          <Step title="Генерация" description="Создание рабочего набора" />
          <Step title="Готово" description="Скачивание архива" />
        </Steps>

        <Spin spinning={loading} tip="Генерация рабочего набора...">

          {/* ШАГ 0: ЗАГРУЗКА ЕГРН */}
          {currentStep === 0 && (
            <div>
              <Alert
                message="Шаг 1: Загрузите выписку ЕГРН"
                description="Загрузите XML файл выписки ЕГРН для автоматической генерации рабочего набора MapInfo"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Dragger
                accept=".xml"
                beforeUpload={handleEgrnUpload}
                onRemove={handleRemoveEgrn}
                fileList={egrnFile ? [egrnFile] : []}
                maxCount={1}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">
                  Нажмите или перетащите XML файл ЕГРН
                </p>
                <p className="ant-upload-hint">
                  Поддерживаются только XML файлы выписки из ЕГРН
                </p>
              </Dragger>

              <Button
                type="primary"
                size="large"
                block
                onClick={handleNextStep}
                disabled={!egrnFile}
                style={{ marginTop: 24 }}
              >
                Продолжить
              </Button>
            </div>
          )}

          {/* ШАГ 1: ГЕНЕРАЦИЯ */}
          {currentStep === 1 && (
            <div>
              <Alert
                message="Шаг 2: Генерация рабочего набора"
                description="Будет создан архив со структурой папок, слоями MapInfo (TAB) и рабочим набором (WOR)"
                type="warning"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Card 
                title="Что будет создано:"
                size="small"
                style={{ marginBottom: 24 }}
              >
                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                  <li>📁 Структура папок GP_Graphics_[кадастровый_номер]/</li>
                  <li>📄 README.txt с инструкцией</li>
                  <li>🗺️ Рабочий набор MapInfo (WOR файл)</li>
                  <li>📊 Все слои в формате TAB:</li>
                  <ul>
                    <li>Участок</li>
                    <li>Точки участка</li>
                    <li>Зона строительства</li>
                    <li>ОКС (если найдены)</li>
                    <li>ЗОУИТ (если найдены)</li>
                    <li>Красные линии</li>
                  </ul>
                  <li>📦 ZIP архив для скачивания</li>
                </ul>
              </Card>

              <div style={{ display: 'flex', gap: 16 }}>
                <Button
                  size="large"
                  onClick={() => setCurrentStep(0)}
                  style={{ flex: 1 }}
                >
                  Назад
                </Button>
                <Button
                  type="primary"
                  size="large"
                  icon={<FolderOpenOutlined />}
                  onClick={handleGenerate}
                  style={{ flex: 2 }}
                >
                  Сгенерировать рабочий набор
                </Button>
              </div>
            </div>
          )}

          {/* ШАГ 2: РЕЗУЛЬТАТ */}
          {currentStep === 2 && generatedFileName && (
            <Result
              status="success"
              title="Рабочий набор успешно сгенерирован!"
              subTitle={
                <div>
                  <p style={{ fontSize: '1.05rem', marginBottom: 16 }}>
                    Файл: <strong>{generatedFileName}</strong>
                  </p>
                  <p style={{ color: '#8c8c8c' }}>
                    Архив автоматически загружен на ваш компьютер
                  </p>
                  <div style={{ 
                    marginTop: 24, 
                    padding: 16, 
                    background: '#f5f5f5', 
                    borderRadius: 8,
                    textAlign: 'left'
                  }}>
                    <p style={{ fontWeight: 600, marginBottom: 8 }}>
                      📝 Что дальше:
                    </p>
                    <ol style={{ marginBottom: 0, paddingLeft: 20 }}>
                      <li>Распакуйте ZIP архив</li>
                      <li>Откройте файл <code>рабочий_набор.WOR</code> в MapInfo</li>
                      <li>Автоматически откроются 2 карты с масштабами 1:500 и 1:2000</li>
                    </ol>
                  </div>
                </div>
              }
              extra={[
                <Button 
                  key="reset" 
                  onClick={handleReset}
                  size="large"
                >
                  Создать ещё один набор
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

export default WorkspaceFlow;
