import React, { useState } from 'react';
import { Alert, Button, Card, List, Modal, Progress, Steps, Upload, message } from 'antd';
import { ExclamationCircleOutlined, InboxOutlined } from '@ant-design/icons';
import UserHeader from '../Common/UserHeader';
import { landPassportsApi } from '../../services/api';
import { useSmoothProgress } from '../../hooks/useSmoothProgress';

const { Dragger } = Upload;

const PreparePassportsFlow = () => {
  const [step, setStep] = useState(0);
  const [xlsxFile, setXlsxFile] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState('');
  const [currentJobId, setCurrentJobId] = useState(null);
  const { displayProgress, start: startProgress, update: updateProgress, reset: resetProgress } = useSmoothProgress();

  const proceedToStep1 = () => setStep(1);

  const showWarningsModal = (warnings) => {
    Modal.confirm({
      title: 'Не все поля заполнены',
      icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
      width: 520,
      content: (
        <div>
          <p style={{ marginBottom: 8 }}>
            Обнаружено <b>{warnings.length}</b> незаполненных полей. Продолжить генерацию паспортов?
          </p>
          <div style={{ maxHeight: 220, overflowY: 'auto', fontSize: 12, color: '#555' }}>
            <List
              size="small"
              dataSource={warnings.slice(0, 50)}
              renderItem={item => <List.Item style={{ padding: '2px 0' }}>{item}</List.Item>}
            />
            {warnings.length > 50 && (
              <div style={{ marginTop: 4, color: '#999' }}>… и ещё {warnings.length - 50}</div>
            )}
          </div>
        </div>
      ),
      okText: 'Продолжить',
      cancelText: 'Отмена',
      onOk: proceedToStep1,
      onCancel: () => {
        setXlsxFile(null);
        setValidationError(null);
      },
    });
  };

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.xlsx',
    fileList: xlsxFile ? [xlsxFile] : [],
    beforeUpload: async (file) => {
      setXlsxFile(file);
      setValidationError(null);
      setLoading(true);
      try {
        const res = await landPassportsApi.validate(file);
        const warnings = res.data.warnings || [];
        if (warnings.length > 0) {
          showWarningsModal(warnings);
        } else {
          proceedToStep1();
        }
      } catch (err) {
        const detail = err.response?.data?.detail;
        if (detail && detail.missing_columns) {
          setValidationError(`Отсутствуют обязательные колонки: ${detail.missing_columns.join(', ')}`);
        } else {
          setValidationError(typeof detail === 'string' ? detail : 'Ошибка валидации файла');
        }
      } finally {
        setLoading(false);
      }
      return false;
    },
    onRemove: () => {
      setXlsxFile(null);
      setValidationError(null);
      setStep(0);
    },
  };

  const pollProgress = async (jobId) => {
    while (true) {
      try {
        const res = await landPassportsApi.getProgress(jobId);
        const { status, progress: pct, current, total } = res.data;
        updateProgress(pct);
        setProgressText(`Генерация паспорта ${current} из ${total}…`);
        if (status === 'done') return 'done';
        if (status === 'cancelled') return 'cancelled';
        if (status === 'error') throw new Error(res.data.error || 'Ошибка генерации');
      } catch (err) {
        if (err.response?.status === 404) return 'cancelled';
        throw err;
      }
      await new Promise(r => setTimeout(r, 500));
    }
  };

  const triggerDownload = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleGenerate = async () => {
    setLoading(true);
    setProgressText('Отправка файла…');
    try {
      const startRes = await landPassportsApi.generate(xlsxFile);
      const { job_id, total } = startRes.data;
      setCurrentJobId(job_id);
      startProgress(total);

      const result = await pollProgress(job_id);
      setCurrentJobId(null);

      if (result === 'cancelled') {
        message.info('Операция отменена');
        return;
      }

      updateProgress(100);
      const dlRes = await landPassportsApi.download(job_id);
      triggerDownload(new Blob([dlRes.data]), 'паспорта_участков.zip');
      message.success('Паспорта сгенерированы');
    } catch (err) {
      const detail = err.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : err.message || 'Ошибка при генерации паспортов');
    } finally {
      setLoading(false);
      setCurrentJobId(null);
      resetProgress();
      setProgressText('');
    }
  };

  const handleCancel = async () => {
    if (currentJobId) {
      try { await landPassportsApi.cancel(currentJobId); } catch (_) {}
    }
    setLoading(false);
    setCurrentJobId(null);
    resetProgress();
    setProgressText('');
  };

  const handleReset = () => {
    setStep(0);
    setXlsxFile(null);
    setValidationError(null);
  };

  return (
    <div>
      <UserHeader title="Подготовить паспорта участков" showBackButton={true} backPath="/land-passports" />

      <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px' }}>
        <Steps
          current={step}
          items={[{ title: 'Загрузка xlsx' }, { title: 'Генерация паспортов' }]}
          style={{ marginBottom: 24 }}
        />

        {step === 0 && (
          <Card>
            <Dragger {...uploadProps} disabled={loading}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">Перетащите xlsx-файл перечня или нажмите для выбора</p>
              <p className="ant-upload-hint">
                Файл будет автоматически проверен на наличие обязательных колонок и заполненность полей.
              </p>
            </Dragger>

            {validationError && (
              <Alert
                type="error"
                message="Файл не прошёл проверку"
                description={validationError}
                style={{ marginTop: 16 }}
                showIcon
              />
            )}
          </Card>
        )}

        {step === 1 && (
          <Card>
            <Alert
              type="success"
              message="Файл проверен и готов к генерации"
              style={{ marginBottom: 16 }}
              showIcon
            />

            {loading ? (
              <>
                <Progress
                  percent={Math.round(displayProgress)}
                  status="active"
                  strokeColor={{ from: '#667eea', to: '#764ba2' }}
                  style={{ marginBottom: 4 }}
                />
                <div style={{ textAlign: 'center', color: '#666', marginBottom: 16, fontSize: 13 }}>
                  {progressText}
                </div>
                <Button danger size="large" block onClick={handleCancel}>
                  Отмена
                </Button>
              </>
            ) : (
              <>
                <Button type="primary" size="large" block onClick={handleGenerate}>
                  Сгенерировать паспорта
                </Button>
                <Button size="large" block onClick={handleReset} style={{ marginTop: 8 }}>
                  Загрузить другой файл
                </Button>
              </>
            )}
          </Card>
        )}
      </div>
    </div>
  );
};

export default PreparePassportsFlow;
