import React, { useState } from 'react';
import { Button, Card, Progress, Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import UserHeader from '../Common/UserHeader';
import { landPassportsApi } from '../../services/api';
import { useSmoothProgress } from '../../hooks/useSmoothProgress';

const { Dragger } = Upload;

const PrepareListFlow = () => {
  const [fileList, setFileList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState('');
  const [currentJobId, setCurrentJobId] = useState(null);
  const { displayProgress, start: startProgress, update: updateProgress, reset: resetProgress } = useSmoothProgress();

  const uploadProps = {
    name: 'files',
    multiple: true,
    accept: '.xml,.zip',
    fileList,
    beforeUpload: (file) => {
      setFileList(prev => [...prev, file]);
      return false;
    },
    onRemove: (file) => {
      setFileList(prev => prev.filter(f => f.uid !== file.uid));
    },
  };

  const pollProgress = async (jobId) => {
    while (true) {
      try {
        const res = await landPassportsApi.getProgress(jobId);
        const { status, progress: pct, current, total } = res.data;
        updateProgress(pct);
        setProgressText(`Обрабатывается файл ${current} из ${total}…`);
        if (status === 'done') return 'done';
        if (status === 'cancelled') return 'cancelled';
        if (status === 'error') throw new Error(res.data.error || 'Ошибка обработки');
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
    if (fileList.length === 0) {
      message.warning('Добавьте хотя бы один файл ЕГРН (.xml или .zip)');
      return;
    }
    setLoading(true);
    setProgressText('Отправка файлов…');
    try {
      const startRes = await landPassportsApi.parseEgrn(fileList);
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
      triggerDownload(new Blob([dlRes.data]), 'перечень_участков.xlsx');
      message.success(`Перечень сформирован (${fileList.length} участков)`);
      setFileList([]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : err.message || 'Ошибка при формировании перечня');
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

  const fileWord = fileList.length > 4 ? 'ов' : fileList.length > 1 ? 'а' : '';

  return (
    <div>
      <UserHeader title="Подготовить перечень участков" showBackButton={true} backPath="/land-passports" />

      <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px' }}>
        <Card>
          <Dragger {...uploadProps} style={{ marginBottom: 24 }} disabled={loading}>
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">Перетащите файлы ЕГРН или нажмите для выбора</p>
            <p className="ant-upload-hint">Поддерживаются .xml и .zip файлы выписок ЕГРН. Можно загрузить несколько.</p>
          </Dragger>

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
            <Button
              type="primary"
              size="large"
              block
              onClick={handleGenerate}
              disabled={fileList.length === 0}
            >
              {`Сформировать перечень${fileList.length > 0 ? ` (${fileList.length} файл${fileWord})` : ''}`}
            </Button>
          )}
        </Card>
      </div>
    </div>
  );
};

export default PrepareListFlow;
