// frontend/src/components/RRR/RRRCreate.jsx
import React, { useState } from 'react';
import {
  Steps, Button, Radio, Upload, Form, Input, InputNumber,
  DatePicker, message, Card, Descriptions, Space, Result, Spin, Select
} from 'antd';

import { UploadOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { rrrApi } from '../../services/api';
import ObjectTypeSelect from './ObjectTypeSelect';
import UserHeader from '../Common/UserHeader';
import './RRRCreate.css';

const { Step } = Steps;
const { Dragger } = Upload;
const { Option } = Select;

const RRRCreate = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submissionType, setSubmissionType] = useState('paper');
  const [xmlData, setXmlData] = useState(null);
  const [appData, setAppData] = useState(null);
  const [formData, setFormData] = useState({});
  const [createdId, setCreatedId] = useState(null);
  const [selectedObjectType, setSelectedObjectType] = useState(null);

  // Шаг 0: Выбор способа подачи
  const renderStep0 = () => (
    <Card title="Выберите способ подачи заявления">
      <Radio.Group
        value={submissionType}
        onChange={(e) => setSubmissionType(e.target.value)}
        size="large"
      >
        <Space direction="vertical" size="middle">
          <Radio value="paper">Бумажное заявление + XML</Radio>
          <Radio value="epgu">Через ЕПГУ (DOCX + XML)</Radio>
        </Space>
      </Radio.Group>
      <div style={{ marginTop: 24 }}>
        <Button type="primary" onClick={() => setCurrentStep(1)}>
          Далее
        </Button>
      </div>
    </Card>
  );

  // Шаг 1: Загрузка файлов
  const handleXmlUpload = async (file) => {
    setLoading(true);
    try {
      const response = await rrrApi.parseXml(file);
      if (response.data.success) {
        setXmlData(response.data.data);
        message.success('XML распознан');
      }
    } catch (error) {
      message.error('Ошибка парсинга XML');
      console.error(error);
    } finally {
      setLoading(false);
    }
    return false;
  };

  const handleDocxUpload = async (file) => {
    setLoading(true);
    try {
      const response = await rrrApi.parseApplication(file);
      if (response.data.success) {
        const d = response.data.data;
        setAppData(d);
        // Сразу кладём в formData — единственный источник правды
        setFormData(prev => ({
          ...prev,
          org_name:        d.org_name        || prev.org_name,
          org_inn:         d.inn             || prev.org_inn,
          org_ogrn:        d.ogrn            || prev.org_ogrn,
          org_address:     d.org_address     || prev.org_address,
          person_name:     d.person_name     || prev.person_name,
          person_passport: d.person_passport || prev.person_passport,
          person_address:  d.person_address  || prev.person_address,
          app_number:      d.app_number      || prev.app_number,
          app_date:        d.app_date        || prev.app_date,
          term_months:     d.term_months     || prev.term_months,
          // Авто-определяем тип: org_name → ЮЛ, иначе person_name → ФЛ
          applicant_type: prev.applicant_type || (d.org_name ? 'ЮЛ' : d.person_name ? 'ФЛ' : undefined),
        }));
        message.success('Заявление распознано');
      }
    } catch (error) {
      message.error('Ошибка парсинга заявления');
      console.error(error);
    } finally {
      setLoading(false);
    }
    return false;
  };

  const renderStep1 = () => (
    <Card title="Загрузка файлов">
      <Spin spinning={loading}>
        <div style={{ marginBottom: 24 }}>
          <h4>XML схема границ (обязательно)</h4>
          <Dragger
            accept=".xml,.zip,.gz"
            beforeUpload={handleXmlUpload}
            showUploadList={false}
            style={{ maxWidth: 500 }}
          >
            <p className="ant-upload-drag-icon"><UploadOutlined /></p>
            <p>Нажмите или перетащите XML файл</p>
          </Dragger>
          {xmlData && (
            <Descriptions column={1} size="small" style={{ marginTop: 12 }}>
              <Descriptions.Item label="Кадастровый квартал">{xmlData.cadastral_block || '-'}</Descriptions.Item>
              <Descriptions.Item label="Площадь">{xmlData.area ? `${xmlData.area} кв.м` : '-'}</Descriptions.Item>
              <Descriptions.Item label="Координаты">{xmlData.coordinates_count} точек</Descriptions.Item>
            </Descriptions>
          )}
        </div>

        {submissionType === 'epgu' && (
          <div style={{ marginBottom: 24 }}>
            <h4>Заявление DOCX (из ЕПГУ)</h4>
            <Dragger
              accept=".docx,.doc"
              beforeUpload={handleDocxUpload}
              showUploadList={false}
              style={{ maxWidth: 500 }}
            >
              <p className="ant-upload-drag-icon"><UploadOutlined /></p>
              <p>Нажмите или перетащите DOCX файл</p>
            </Dragger>
            {appData && (
              <Descriptions column={1} size="small" style={{ marginTop: 12 }}>
                <Descriptions.Item label="Вх. номер">{appData.app_number || '-'}</Descriptions.Item>
                <Descriptions.Item label="Дата заявления">{appData.app_date_text || appData.app_date || '-'}</Descriptions.Item>
                <Descriptions.Item label="Заявитель">{appData.org_name || appData.person_name || '-'}</Descriptions.Item>
                <Descriptions.Item label="ИНН">{appData.inn || '-'}</Descriptions.Item>
                <Descriptions.Item label="ОГРН">{appData.ogrn || '-'}</Descriptions.Item>
                <Descriptions.Item label="Срок (мес.)">{appData.term_months || '-'}</Descriptions.Item>
              </Descriptions>
            )}
          </div>
        )}

        <Space>
          <Button onClick={() => setCurrentStep(0)}>Назад</Button>
          <Button
            type="primary"
            disabled={!xmlData}
            onClick={() => {
              if (submissionType === 'epgu' && !formData.submission_method) {
                setFormData(prev => ({ ...prev, submission_method: 'ЕПГУ' }));
              }
              setCurrentStep(2);
            }}
          >
            Далее
          </Button>
        </Space>
      </Spin>
    </Card>
  );

  // Шаг 2: Проверка данных и ручной ввод
  const handleRegister = async () => {
    setLoading(true);
    try {
      const payload = {
        // Из XML
        area: xmlData?.area,
        location: xmlData?.note || xmlData?.cadastral_block,
        coordinates: xmlData?.coordinates,
        // Данные заявителя
        org_name:        formData.org_name,
        org_inn:         formData.org_inn,
        org_ogrn:        formData.org_ogrn,
        org_address:     formData.org_address,
        person_name:     formData.person_name,
        person_passport: formData.person_passport,
        person_address:  formData.person_address,
        app_number:      formData.app_number,
        app_date:        formData.app_date,
        term_months:     formData.term_months,
        // Вручную (обязательно)
        object_type: formData.object_type,
        object_name: formData.object_name,
        applicant_type: formData.applicant_type,
        submission_method: formData.submission_method || (submissionType === 'epgu' ? 'ЕПГУ' : null),
        // Рассчитанные
        service_deadline_days: selectedObjectType?.deadline_days,
      };

      const response = await rrrApi.create(payload);
      if (response.data.success) {
        const newId = response.data.data.id;
        setCreatedId(newId);

        // Запускаем пространственный анализ
        try {
          await rrrApi.spatialAnalysis({ permit_id: newId });
        } catch (analysisError) {
          console.error('Ошибка пространственного анализа:', analysisError);
        }

        setCurrentStep(3);
        message.success('Заявление зарегистрировано');
      }
    } catch (error) {
      message.error('Ошибка регистрации: ' + (error.response?.data?.detail || error.message));
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const renderStep2 = () => {
    const isLegal = formData.applicant_type === 'ЮЛ';
    const isPhysical = formData.applicant_type === 'ФЛ';
    const typeNotChosen = !formData.applicant_type;

    return (
      <Card title="Проверка данных и заполнение полей">
        <Spin spinning={loading}>
          <Form layout="vertical" style={{ maxWidth: 700 }}>

            <h4>Объект (обязательно)</h4>
            <Form.Item label="Вид объекта" required>
              <ObjectTypeSelect
                value={formData.object_type}
                onChange={(value, typeObj) => {
                  setFormData({ ...formData, object_type: value });
                  setSelectedObjectType(typeObj);
                }}
              />
            </Form.Item>
            <Form.Item label="Наименование объекта" required>
              <Input
                value={formData.object_name || ''}
                onChange={(e) => setFormData({ ...formData, object_name: e.target.value })}
                placeholder="Газопровод низкого давления"
              />
            </Form.Item>

            <h4>Заявитель</h4>
            <Form.Item label="Тип заявителя" required>
              <Radio.Group
                value={formData.applicant_type}
                onChange={(e) => setFormData({ ...formData, applicant_type: e.target.value })}
              >
                <Radio value="ЮЛ">Юридическое лицо</Radio>
                <Radio value="ФЛ">Физическое лицо</Radio>
              </Radio.Group>
            </Form.Item>

            {(isLegal || typeNotChosen) && (
              <>
                <Form.Item label="Наименование организации">
                  <Input
                    value={formData.org_name || ''}
                    onChange={(e) => setFormData({ ...formData, org_name: e.target.value })}
                    placeholder="ООО «Название»"
                  />
                </Form.Item>
                <Form.Item label="ИНН">
                  <Input
                    value={formData.org_inn || ''}
                    onChange={(e) => setFormData({ ...formData, org_inn: e.target.value })}
                  />
                </Form.Item>
                <Form.Item label="ОГРН">
                  <Input
                    value={formData.org_ogrn || ''}
                    onChange={(e) => setFormData({ ...formData, org_ogrn: e.target.value })}
                  />
                </Form.Item>
                <Form.Item label="Адрес">
                  <Input
                    value={formData.org_address || ''}
                    onChange={(e) => setFormData({ ...formData, org_address: e.target.value })}
                  />
                </Form.Item>
              </>
            )}

            {(isPhysical || typeNotChosen) && (
              <>
                <Form.Item label="ФИО">
                  <Input
                    value={formData.person_name || ''}
                    onChange={(e) => setFormData({ ...formData, person_name: e.target.value })}
                  />
                </Form.Item>
                <Form.Item label="Паспорт">
                  <Input
                    value={formData.person_passport || ''}
                    onChange={(e) => setFormData({ ...formData, person_passport: e.target.value })}
                  />
                </Form.Item>
                <Form.Item label="Адрес регистрации">
                  <Input
                    value={formData.person_address || ''}
                    onChange={(e) => setFormData({ ...formData, person_address: e.target.value })}
                  />
                </Form.Item>
              </>
            )}

            <h4>Заявление</h4>
            <Form.Item label="Входящий номер">
              <Input
                value={formData.app_number || ''}
                onChange={(e) => setFormData({ ...formData, app_number: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="Входящая дата">
              <Input
                value={formData.app_date || ''}
                onChange={(e) => setFormData({ ...formData, app_date: e.target.value })}
                placeholder="ГГГГ-ММ-ДД"
              />
            </Form.Item>
            <Form.Item label="Срок действия (месяцы)">
              <InputNumber
                value={formData.term_months}
                onChange={(value) => setFormData({ ...formData, term_months: value })}
                min={1}
                max={600}
                style={{ width: 200 }}
              />
            </Form.Item>

            <Form.Item label="Способ подачи" required>
              <Select
                value={formData.submission_method}
                onChange={(value) => setFormData({ ...formData, submission_method: value })}
                placeholder="Выберите способ"
                style={{ width: 220 }}
              >
                <Option value="ЕПГУ">ЕПГУ</Option>
                <Option value="МФЦ">МФЦ</Option>
                <Option value="Личный прием">Личный прием</Option>
              </Select>
            </Form.Item>

            <Space>
              <Button onClick={() => setCurrentStep(1)}>Назад</Button>
              <Button
                type="primary"
                onClick={handleRegister}
                disabled={!formData.object_type || !formData.object_name || !formData.applicant_type || !formData.submission_method}
                loading={loading}
              >
                Зарегистрировать
              </Button>
            </Space>
          </Form>
        </Spin>
      </Card>
    );
  };

  // Шаг 3: Успех
  const renderStep3 = () => (
    <Result
      status="success"
      title="Заявление зарегистрировано"
      subTitle={`ID: ${createdId}`}
      extra={[
        <Button type="primary" key="card" onClick={() => navigate(`/rrr/${createdId}`)}>
          Открыть карточку
        </Button>,
        <Button key="new" onClick={() => navigate('/rrr/new')}>
          Создать ещё
        </Button>,
        <Button key="list" onClick={() => navigate('/rrr')}>
          К списку
        </Button>,
      ]}
    />
  );

  const steps = [
    { title: 'Способ подачи' },
    { title: 'Загрузка файлов' },
    { title: 'Проверка данных' },
    { title: 'Готово' },
  ];

  const stepRenderers = [renderStep0, renderStep1, renderStep2, renderStep3];

  return (
    <div className="rrr-create-container">
      <UserHeader title="РРР — Новое заявление" />

      <div className="rrr-create-content">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/rrr')}
          style={{ marginBottom: 16 }}
        >
          К списку
        </Button>

        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          {steps.map((s, i) => (
            <Step key={i} title={s.title} />
          ))}
        </Steps>

        {stepRenderers[currentStep]()}
      </div>
    </div>
  );
};

export default RRRCreate;
