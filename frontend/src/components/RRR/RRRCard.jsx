// frontend/src/components/RRR/RRRCard.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Descriptions, Button, Tag, Space, message, Spin,
  Collapse, Table, Input, InputNumber, Select, Modal, Empty,
  Popconfirm, Form, Divider, Alert, Tabs, Switch, Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined, ReloadOutlined, DeleteOutlined,
  EditOutlined, SaveOutlined, CloseOutlined,
  FileWordOutlined, SendOutlined, EnvironmentOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { rrrApi } from '../../services/api';
import ObjectTypeSelect from './ObjectTypeSelect';
import UserHeader from '../Common/UserHeader';
import './RRRCard.css';

const { Panel } = Collapse;
const { Option } = Select;

const RRRCard = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [permit, setPermit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [actionLoading, setActionLoading] = useState({});
  const [objectTypes, setObjectTypes] = useState([]);

  // Загрузка справочника типов объектов
  useEffect(() => {
    rrrApi.getObjectTypes().then(res => {
      if (res.data?.data) setObjectTypes(res.data.data);
    }).catch(() => {});
  }, []);

  // Определение конфига типа объекта по строке
  const getTypeConfig = useCallback((objectTypeStr) => {
    if (!objectTypeStr || objectTypes.length === 0) return null;
    const match = objectTypeStr.match(/^п+\.?\s*(\d+(?:\.\d+)?)/);
    if (match) {
      return objectTypes.find(t => t.number === match[1]) || null;
    }
    return null;
  }, [objectTypes]);

  // Автоопределение платности
  const autoDetectPayment = useCallback((objectTypeStr, objectName) => {
    const cfg = getTypeConfig(objectTypeStr);
    if (!cfg) return true; // По умолчанию платный

    const number = cfg.number;
    const name = (objectName || '').toLowerCase();

    // п.4 — платно если «парковка», «стоянка», «автостоянка» (любой падеж)
    if (number === '4' && cfg.payment_by_name) {
      return /парковк|стоянк|автостоянк/i.test(name);
    }
    // п.6 — платно только для нефтепроводов (любой падеж)
    if (number === '6' && cfg.payment_by_name_oil) {
      return /нефтепровод/i.test(name);
    }
    // п.19 — платно если «кафе» или «общественное питание» (любой падеж)
    if (number === '19' && cfg.payment_by_name_cafe) {
      return /кафе|общественн\w*\s+питани\w*|питани\w*\s+общественн/i.test(name);
    }
    return cfg.has_payment_default !== false;
  }, [getTypeConfig]);

  const loadPermit = useCallback(async () => {
    setLoading(true);
    try {
      const response = await rrrApi.get(id);
      setPermit(response.data);
    } catch (error) {
      message.error('Ошибка загрузки карточки');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadPermit();
  }, [loadPermit]);

  // ============================
  // Вспомогательные функции
  // ============================

  const getRemainingDays = () => {
    if (!permit?.service_deadline_date) return null;
    const deadline = new Date(permit.service_deadline_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.ceil((deadline - today) / (1000 * 60 * 60 * 24));
  };

  const getRemainingColor = (days) => {
    if (days === null) return '#8c8c8c';
    if (days < 3) return '#ff4d4f';
    if (days <= 10) return '#faad14';
    return '#52c41a';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'зарегистрировано': return 'blue';
      case 'в работе': return 'orange';
      case 'завершено': return 'green';
      default: return 'default';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('ru-RU');
  };

  const formatArea = (area) => {
    if (area === null || area === undefined) return '-';
    return `${area.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} кв.м`;
  };

  // ============================
  // Редактирование
  // ============================

  const startEdit = () => {
    setEditData({
      status: permit.status,
      org_name: permit.org_name || '',
      org_inn: permit.org_inn || '',
      org_ogrn: permit.org_ogrn || '',
      org_address: permit.org_address || '',
      person_name: permit.person_name || '',
      person_passport: permit.person_passport || '',
      person_address: permit.person_address || '',
      applicant_type: permit.applicant_type || '',
      submission_method: permit.submission_method || '',
      app_number: permit.app_number || '',
      app_date: permit.app_date || '',
      object_type: permit.object_type || '',
      object_name: permit.object_name || '',
      term_months: permit.term_months,
      decision_number: permit.decision_number || '',
      decision_date: permit.decision_date || '',
      end_date: permit.end_date || '',
      has_payment: permit.has_payment,
      payment_amount: permit.payment_amount,
      proezd_agreement: permit.proezd_agreement || '',
      notes: permit.notes || '',
    });
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setEditData({});
  };

  const saveEdit = async () => {
    setActionLoading(prev => ({ ...prev, save: true }));
    try {
      const response = await rrrApi.update(id, editData);
      if (response.data.success) {
        message.success('Данные сохранены');
        setEditing(false);
        loadPermit();
      }
    } catch (error) {
      message.error('Ошибка сохранения: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(prev => ({ ...prev, save: false }));
    }
  };

  // ============================
  // Действия
  // ============================

  const handleSpatialAnalysis = async () => {
    setActionLoading(prev => ({ ...prev, spatial: true }));
    try {
      await rrrApi.spatialAnalysis({ permit_id: parseInt(id) });
      message.success('Пространственный анализ выполнен');
      loadPermit();
    } catch (error) {
      message.error('Ошибка анализа: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(prev => ({ ...prev, spatial: false }));
    }
  };

  const handleDelete = async () => {
    setActionLoading(prev => ({ ...prev, delete: true }));
    try {
      await rrrApi.delete(id);
      message.success('Заявление удалено');
      navigate('/rrr');
    } catch (error) {
      message.error('Ошибка удаления');
    } finally {
      setActionLoading(prev => ({ ...prev, delete: false }));
    }
  };

  const handleKaiten = async () => {
    setActionLoading(prev => ({ ...prev, kaiten: true }));
    try {
      const response = await rrrApi.createKaitenCard({ permit_id: parseInt(id) });
      if (response.data.success) {
        message.success('Карточка создана в Kaiten');
        if (response.data.card_url) {
          window.open(response.data.card_url, '_blank');
        }
      }
    } catch (error) {
      message.error('Ошибка Kaiten: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(prev => ({ ...prev, kaiten: false }));
    }
  };

  const handleMapInfo = async () => {
    setActionLoading(prev => ({ ...prev, mapinfo: true }));
    try {
      const response = await rrrApi.addToMapInfo({ permit_id: parseInt(id) });
      if (response.data.success) {
        message.success('Объект добавлен в MapInfo');
      }
    } catch (error) {
      message.error('Ошибка MapInfo: ' + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(prev => ({ ...prev, mapinfo: false }));
    }
  };

  const handleGenerateDecision = async () => {
    setActionLoading(prev => ({ ...prev, decision: true }));
    try {
      const response = await rrrApi.generateDecision(parseInt(id));
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const applicant = permit.org_name || permit.person_name || 'unknown';
      link.download = `Решение_РРР_${permit.app_number || permit.id}_${applicant.slice(0, 30)}.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('Решение сформировано');
    } catch (error) {
      message.error('Ошибка генерации решения');
    } finally {
      setActionLoading(prev => ({ ...prev, decision: false }));
    }
  };

  // ============================
  // Валидация кнопок интеграций
  // ============================

  const getKaitenMissing = () => {
    const missing = [];
    if (!permit?.org_name && !permit?.person_name) missing.push('Наименование заявителя');
    if (!permit?.applicant_type) missing.push('Тип заявителя (ЮЛ/ФЛ)');
    if (!permit?.submission_method) missing.push('Способ подачи');
    if (!permit?.app_number) missing.push('Вх. номер');
    if (!permit?.app_date) missing.push('Вх. дата');
    if (!permit?.object_type) missing.push('Вид объекта');
    return missing;
  };

  const getMapInfoMissing = () => {
    const missing = [];
    if (!permit?.org_name && !permit?.person_name) missing.push('Заявитель');
    if (!permit?.area) missing.push('Площадь');
    if (!permit?.app_number) missing.push('Вх. номер');
    if (!permit?.app_date) missing.push('Вх. дата');
    if (!permit?.object_type) missing.push('Вид объекта');
    if (!permit?.object_name) missing.push('Наименование объекта');
    if (!permit?.coordinates || permit.coordinates.length === 0) missing.push('Координаты');
    return missing;
  };

  const getDecisionMissing = () => {
    const missing = [];
    if (!permit?.decision_number) missing.push('Номер решения');
    if (!permit?.decision_date) missing.push('Дата решения');
    return missing;
  };

  // ============================
  // Рендер пространственного анализа
  // ============================

  const renderJsonTable = (data, columns) => {
    if (!data || data.length === 0) {
      return <span className="rrr-empty-text">нет пересечений</span>;
    }
    return (
      <Table
        dataSource={data.map((item, i) => ({ ...item, key: i }))}
        columns={columns}
        size="small"
        pagination={false}
        bordered
      />
    );
  };

  const renderSpatialAnalysis = () => {
    if (!permit) return null;

    const sections = [
      {
        key: 'sheets_500',
        label: 'Планшеты 1:500',
        render: () => {
          const sheets = permit.sheets_500;
          if (!sheets || sheets.length === 0) return <span className="rrr-empty-text">нет данных</span>;
          return <span>{sheets.join(', ')}</span>;
        },
      },
      {
        key: 'quarters',
        label: 'Кадастровые кварталы',
        render: () => <span>{permit.quarters || <span className="rrr-empty-text">нет данных</span>}</span>,
      },
      {
        key: 'capital_objects',
        label: 'Объекты капитального строительства (ОКС)',
        render: () => renderJsonTable(permit.capital_objects, [
          { title: 'Кадастровый номер', dataIndex: 'cadnum', key: 'cadnum' },
          { title: 'Вид объекта', dataIndex: 'type', key: 'type' },
          { title: 'Адрес', dataIndex: 'address', key: 'address' },
        ]),
      },
      {
        key: 'zouit',
        label: 'ЗОУИТ',
        render: () => renderJsonTable(permit.zouit, [
          { title: 'Реестровый номер', dataIndex: 'registry_number', key: 'registry_number' },
          { title: 'Наименование', dataIndex: 'name', key: 'name' },
        ]),
      },
      {
        key: 'red_lines',
        label: 'Красные линии',
        render: () => (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Площадь внутри красных линий">
              {permit.red_lines_inside_area !== null ? formatArea(permit.red_lines_inside_area) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Площадь за красными линиями">
              {permit.red_lines_outside_area !== null ? formatArea(permit.red_lines_outside_area) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Описание">
              {permit.red_lines_description || '-'}
            </Descriptions.Item>
          </Descriptions>
        ),
      },
      {
        key: 'ppipm',
        label: 'Проекты планировки и межевания (ППиПМ)',
        render: () => renderJsonTable(permit.ppipm, [
          { title: 'Наименование проекта', dataIndex: 'project_name', key: 'project_name' },
          { title: 'Примечание', dataIndex: 'note', key: 'note' },
        ]),
      },
      {
        key: 'prev_decisions',
        label: 'Ранее выданные решения РРР (Разрешение на использование ЗУ)',
        render: () => renderJsonTable(permit.prev_decisions, [
          { title: 'Вид объекта',   dataIndex: 'object_type',     key: 'object_type' },
          { title: 'Номер решения', dataIndex: 'decision_number', key: 'decision_number' },
          { title: 'Дата решения',  dataIndex: 'decision_date',   key: 'decision_date' },
          { title: 'Срок до',       dataIndex: 'end_date',        key: 'end_date' },
          { title: 'Заявитель',     dataIndex: 'applicant',       key: 'applicant' },
        ]),
      },
      {
        key: 'rrr',
        label: 'Заявления РРР (входящие)',
        render: () => renderJsonTable(permit.rrr, [
          { title: 'Вх. номер', dataIndex: 'incoming_number', key: 'incoming_number' },
          { title: 'Вх. дата', dataIndex: 'incoming_date', key: 'incoming_date' },
          { title: 'Заявитель', dataIndex: 'applicant', key: 'applicant' },
          { title: 'Наименование', dataIndex: 'name', key: 'name' },
        ]),
      },
      {
        key: 'preliminary_approval',
        label: 'Предварительное согласование',
        render: () => renderJsonTable(permit.preliminary_approval, [
          { title: 'Дата решения', dataIndex: 'decision_date', key: 'decision_date' },
          { title: 'Номер протокола', dataIndex: 'protocol_number', key: 'protocol_number' },
          { title: 'Объект', dataIndex: 'object', key: 'object' },
          { title: 'Местоположение', dataIndex: 'location', key: 'location' },
        ]),
      },
      {
        key: 'preliminary_approval_kumi',
        label: 'Предварительное согласование КУМИ',
        render: () => renderJsonTable(permit.preliminary_approval_kumi, [
          { title: 'Дата решения', dataIndex: 'decision_date', key: 'decision_date' },
          { title: 'Номер решения', dataIndex: 'decision_number', key: 'decision_number' },
          { title: 'Кадастровый номер', dataIndex: 'cadnum', key: 'cadnum' },
          { title: 'Местоположение', dataIndex: 'location', key: 'location' },
        ]),
      },
      {
        key: 'scheme_location',
        label: 'Схема расположения',
        render: () => renderJsonTable(permit.scheme_location, [
          { title: 'Распоряжение', dataIndex: 'order', key: 'order' },
          { title: 'Местоположение', dataIndex: 'location', key: 'location' },
          { title: 'Разрешенное использование', dataIndex: 'usage', key: 'usage' },
        ]),
      },
      {
        key: 'scheme_location_kumi',
        label: 'Схема расположения КУМИ',
        render: () => renderJsonTable(permit.scheme_location_kumi, [
          { title: 'Дата решения', dataIndex: 'decision_date', key: 'decision_date' },
          { title: 'Номер решения', dataIndex: 'decision_number', key: 'decision_number' },
          { title: 'Местоположение', dataIndex: 'location', key: 'location' },
          { title: 'Разрешенное использование', dataIndex: 'usage', key: 'usage' },
        ]),
      },
      {
        key: 'scheme_nto',
        label: 'Схема НТО',
        render: () => renderJsonTable(permit.scheme_nto, [
          { title: 'Порядковый номер', dataIndex: 'number', key: 'number' },
          { title: 'Адресный ориентир', dataIndex: 'address', key: 'address' },
        ]),
      },
      {
        key: 'advertising',
        label: 'Рекламные конструкции',
        render: () => renderJsonTable(permit.advertising, [
          { title: 'Номер', dataIndex: 'number', key: 'number' },
          { title: 'Адрес', dataIndex: 'address', key: 'address' },
          { title: 'Вид', dataIndex: 'type', key: 'type' },
        ]),
      },
      {
        key: 'land_bank',
        label: 'Банк ЗУ (многодетные)',
        render: () => renderJsonTable(permit.land_bank, [
          { title: 'Кадастровый номер', dataIndex: 'cadnum', key: 'cadnum' },
          { title: 'Местоположение', dataIndex: 'location', key: 'location' },
        ]),
      },
    ];

    const hasData = (key) => {
      if (key === 'quarters') return !!permit.quarters;
      if (key === 'red_lines') {
        return permit.red_lines_inside_area !== null || permit.red_lines_outside_area !== null;
      }
      const val = permit[key];
      return val && Array.isArray(val) && val.length > 0;
    };

    return (
      <Collapse defaultActiveKey={sections.filter(s => hasData(s.key)).map(s => s.key)}>
        {sections.map((section) => {
          const has = hasData(section.key);
          return (
            <Panel
              key={section.key}
              header={
                <span>
                  {section.label}
                  {has
                    ? <Tag color="blue" style={{ marginLeft: 8 }}>есть</Tag>
                    : <Tag style={{ marginLeft: 8 }}>пусто</Tag>
                  }
                </span>
              }
            >
              {section.render()}
            </Panel>
          );
        })}
      </Collapse>
    );
  };

  // ============================
  // Рендер формы редактирования
  // ============================


  // ============================
  // Основной рендер
  // ============================

  if (loading && !permit) {
    return (
      <div className="rrr-card-container">
        <UserHeader title="РРР — Карточка заявления" />
        <div className="rrr-card-content">
          <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
        </div>
      </div>
    );
  }

  if (!permit) {
    return (
      <div className="rrr-card-container">
        <UserHeader title="РРР — Карточка заявления" />
        <div className="rrr-card-content">
          <Empty description="Заявление не найдено" />
          <Button onClick={() => navigate('/rrr')} style={{ marginTop: 16 }}>К списку</Button>
        </div>
      </div>
    );
  }

  const remainingDays = getRemainingDays();
  const kaitenMissing = getKaitenMissing();
  const mapInfoMissing = getMapInfoMissing();
  const decisionMissing = getDecisionMissing();

  return (
    <div className="rrr-card-container">
      <UserHeader title="РРР — Карточка заявления" />

      <div className="rrr-card-content">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/rrr')}
          style={{ marginBottom: 16 }}
        >
          К списку
        </Button>

        {/* === ЗАГОЛОВОК === */}
        <Card className="rrr-card-header">
          <div className="rrr-card-header-row">
            <div>
              <h2 style={{ margin: 0 }}>
                Заявление {permit.app_number ? `№${permit.app_number}` : `#${permit.id}`}
                {permit.app_date && ` от ${formatDate(permit.app_date)}`}
              </h2>
              <Space style={{ marginTop: 8 }}>
                <Tag color={getStatusColor(permit.status)}>{permit.status || 'без статуса'}</Tag>
                {remainingDays !== null && (
                  <span style={{ color: getRemainingColor(remainingDays), fontWeight: 600 }}>
                    Осталось: {remainingDays} дн.
                  </span>
                )}
              </Space>
            </div>
          </div>
        </Card>

        {/* === ДЕЙСТВИЯ === */}
        <Card style={{ marginBottom: 16 }}>
          <Space wrap size="middle">
            <Button
              type="primary"
              icon={<FileWordOutlined />}
              loading={actionLoading.decision}
              onClick={handleGenerateDecision}
              disabled={decisionMissing.length > 0}
            >
              Сформировать решение
            </Button>
            {decisionMissing.length > 0 && (
              <span className="rrr-missing-text">
                Не хватает: {decisionMissing.join(', ')}
              </span>
            )}
            <Button disabled>
              Сформировать отказ (в разработке)
            </Button>
            <Divider type="vertical" />
            <Button
              icon={<SendOutlined />}
              loading={actionLoading.kaiten}
              onClick={handleKaiten}
              disabled={kaitenMissing.length > 0}
            >
              Kaiten
            </Button>
            {kaitenMissing.length > 0 && (
              <span className="rrr-missing-text">
                Не хватает: {kaitenMissing.join(', ')}
              </span>
            )}
            <Button
              icon={<EnvironmentOutlined />}
              loading={actionLoading.mapinfo}
              onClick={handleMapInfo}
              disabled={mapInfoMissing.length > 0}
            >
              MapInfo
            </Button>
            {mapInfoMissing.length > 0 && (
              <span className="rrr-missing-text">
                Не хватает: {mapInfoMissing.join(', ')}
              </span>
            )}
          </Space>
        </Card>

        {/* === ПРЕДУПРЕЖДЕНИЯ === */}
        {permit.warnings && (
          <Alert
            message="Предупреждения при анализе"
            description={permit.warnings}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* === ВКЛАДКИ === */}
        <Tabs defaultActiveKey="info" items={[
          {
            key: 'info',
            label: 'Карточка',
            children: (() => {
              const showLegal = editing
                ? editData.applicant_type !== 'ФЛ'
                : permit.applicant_type !== 'ФЛ';
              const showPhysical = editing
                ? editData.applicant_type !== 'ЮЛ'
                : permit.applicant_type !== 'ЮЛ';

              return (
                <>
                  {/* ── БЛОК 1: ЗАЯВИТЕЛЬ ── */}
                  <Card
                    className="rrr-section-card"
                    title="Заявитель"
                    style={{ marginBottom: 16 }}
                    extra={
                      editing ? (
                        <Space>
                          <Button icon={<SaveOutlined />} type="primary" onClick={saveEdit} loading={actionLoading.save}>Сохранить</Button>
                          <Button icon={<CloseOutlined />} onClick={cancelEdit}>Отмена</Button>
                        </Space>
                      ) : (
                        <Button icon={<EditOutlined />} onClick={startEdit}>Редактировать</Button>
                      )
                    }
                  >
                    {/* Вх. номер и дата */}
                    <Descriptions column={2} bordered size="small" style={{ marginBottom: 0 }}>
                      <Descriptions.Item label="Вх. номер">
                        {editing
                          ? <Input value={editData.app_number} onChange={(e) => setEditData({ ...editData, app_number: e.target.value })} />
                          : (permit.app_number || '-')}
                      </Descriptions.Item>
                      <Descriptions.Item label="Вх. дата">
                        {editing
                          ? <Input value={editData.app_date} onChange={(e) => setEditData({ ...editData, app_date: e.target.value })} />
                          : formatDate(permit.app_date)}
                      </Descriptions.Item>
                    </Descriptions>

                    {/* Тип заявителя — выбор в режиме редактирования */}
                    {editing && (
                      <div className="rrr-type-selector">
                        <span className="rrr-type-label">Тип заявителя:</span>
                        <Select
                          value={editData.applicant_type || undefined}
                          onChange={(value) => setEditData({ ...editData, applicant_type: value })}
                          placeholder="Выберите тип"
                          style={{ width: 220 }}
                          allowClear
                        >
                          <Option value="ЮЛ">Юридическое лицо</Option>
                          <Option value="ФЛ">Физическое лицо</Option>
                        </Select>
                      </div>
                    )}

                    {/* Данные юрлица */}
                    {showLegal && (
                      <>
                        <Divider orientation="left" className="rrr-block-divider">
                          Юридическое лицо
                        </Divider>
                        <Descriptions column={2} bordered size="small">
                          <Descriptions.Item label="Организация" span={2}>
                            {editing
                              ? <Input value={editData.org_name} onChange={(e) => setEditData({ ...editData, org_name: e.target.value })} />
                              : (permit.org_name || '-')}
                          </Descriptions.Item>
                          <Descriptions.Item label="ИНН">
                            {editing
                              ? <Input value={editData.org_inn} onChange={(e) => setEditData({ ...editData, org_inn: e.target.value })} />
                              : (permit.org_inn || '-')}
                          </Descriptions.Item>
                          <Descriptions.Item label="ОГРН">
                            {editing
                              ? <Input value={editData.org_ogrn} onChange={(e) => setEditData({ ...editData, org_ogrn: e.target.value })} />
                              : (permit.org_ogrn || '-')}
                          </Descriptions.Item>
                          <Descriptions.Item label="Адрес" span={2}>
                            {editing
                              ? <Input value={editData.org_address} onChange={(e) => setEditData({ ...editData, org_address: e.target.value })} />
                              : (permit.org_address || '-')}
                          </Descriptions.Item>
                        </Descriptions>
                      </>
                    )}

                    {/* Данные физлица */}
                    {showPhysical && (
                      <>
                        <Divider orientation="left" className="rrr-block-divider">
                          Физическое лицо
                        </Divider>
                        <Descriptions column={2} bordered size="small">
                          <Descriptions.Item label="ФИО" span={2}>
                            {editing
                              ? <Input value={editData.person_name} onChange={(e) => setEditData({ ...editData, person_name: e.target.value })} />
                              : (permit.person_name || '-')}
                          </Descriptions.Item>
                          <Descriptions.Item label="Паспорт" span={2}>
                            {editing
                              ? <Input value={editData.person_passport} onChange={(e) => setEditData({ ...editData, person_passport: e.target.value })} />
                              : (permit.person_passport || '-')}
                          </Descriptions.Item>
                          <Descriptions.Item label="Адрес" span={2}>
                            {editing
                              ? <Input value={editData.person_address} onChange={(e) => setEditData({ ...editData, person_address: e.target.value })} />
                              : (permit.person_address || '-')}
                          </Descriptions.Item>
                        </Descriptions>
                      </>
                    )}

                  </Card>

                  {/* ── БЛОК 2: ОБЪЕКТ ── */}
                  <Card className="rrr-section-card" title="Объект" style={{ marginBottom: 16 }}>
                    <Descriptions column={2} bordered size="small">
                      <Descriptions.Item label="Вид объекта" span={2}>
                        {editing
                          ? <ObjectTypeSelect value={editData.object_type} onChange={(value) => setEditData({ ...editData, object_type: value })} />
                          : (permit.object_type || '-')}
                      </Descriptions.Item>
                      <Descriptions.Item label="Наименование" span={2}>
                        {editing
                          ? <Input value={editData.object_name} onChange={(e) => setEditData({ ...editData, object_name: e.target.value })} />
                          : (permit.object_name || '-')}
                      </Descriptions.Item>
                      <Descriptions.Item label="Местоположение" span={2}>
                        {permit.location || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Площадь">
                        {formatArea(permit.area)}
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>

                  {/* ── БЛОК 3: СРОКИ И ПОДАЧА ── */}
                  <Card className="rrr-section-card" title="Сроки и подача" style={{ marginBottom: 16 }}>
                    <Descriptions column={2} bordered size="small">
                      <Descriptions.Item label="Срок оказания услуги">
                        {permit.service_deadline_days ? `${permit.service_deadline_days} раб. дн.` : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Срок действия">
                        {editing
                          ? <InputNumber value={editData.term_months} onChange={(value) => setEditData({ ...editData, term_months: value })} min={1} max={600} style={{ width: '100%' }} />
                          : (permit.term_months ? `${permit.term_months} мес.` : '-')}
                      </Descriptions.Item>
                      <Descriptions.Item label="Способ подачи" span={2}>
                        {editing
                          ? (
                            <Select
                              value={editData.submission_method || undefined}
                              onChange={(value) => setEditData({ ...editData, submission_method: value })}
                              placeholder="Выберите способ"
                              style={{ width: '100%' }}
                              allowClear
                            >
                              <Option value="ЕПГУ">ЕПГУ</Option>
                              <Option value="МФЦ">МФЦ</Option>
                              <Option value="Личный прием">Личный прием</Option>
                            </Select>
                          )
                          : (permit.submission_method || '-')}
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>

                  {/* ── БЛОК 4: РЕШЕНИЕ ── */}
                  <Card className="rrr-section-card" title="Решение" style={{ marginBottom: 16 }}>
                    <Descriptions column={{ xs: 2, md: 4 }} bordered size="small">
                      <Descriptions.Item label="Номер решения">
                        {editing
                          ? <Input value={editData.decision_number} onChange={(e) => setEditData({ ...editData, decision_number: e.target.value })} />
                          : (permit.decision_number || '-')}
                      </Descriptions.Item>
                      <Descriptions.Item label="Дата решения">
                        {editing
                          ? <Input value={editData.decision_date} onChange={(e) => setEditData({ ...editData, decision_date: e.target.value })} />
                          : formatDate(permit.decision_date)}
                      </Descriptions.Item>
                      <Descriptions.Item label="Период до">
                        {editing
                          ? <Input value={editData.end_date} onChange={(e) => setEditData({ ...editData, end_date: e.target.value })} placeholder="ГГГГ-ММ-ДД" />
                          : formatDate(permit.end_date)}
                      </Descriptions.Item>
                      <Descriptions.Item label="Сумма">
                        {permit.has_payment === false
                          ? <Tag color="green">Бесплатно</Tag>
                          : permit.payment_amount
                            ? <><Tag color="red">Платно</Tag> {permit.payment_amount.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} руб.</>
                            : <Tag>Не рассчитано</Tag>}
                      </Descriptions.Item>
                    </Descriptions>

                    {/* Оплата — редактирование */}
                    {editing && (
                      <div className="rrr-payment-edit">
                        <span className="rrr-type-label">Оплата:</span>
                        <Switch
                          checked={editData.has_payment !== null && editData.has_payment !== undefined
                            ? editData.has_payment
                            : autoDetectPayment(editData.object_type, editData.object_name)}
                          onChange={(checked) => setEditData({ ...editData, has_payment: checked })}
                          checkedChildren="Платно"
                          unCheckedChildren="Бесплатно"
                        />
                        <Tooltip title="Определить автоматически по виду объекта и наименованию">
                          <Button size="small" onClick={() => {
                            const auto = autoDetectPayment(editData.object_type, editData.object_name);
                            setEditData({ ...editData, has_payment: auto });
                          }}>Авто</Button>
                        </Tooltip>
                      </div>
                    )}
                  </Card>

                  {/* ── ДОПОЛНИТЕЛЬНО ── */}
                  <Card className="rrr-section-card" title="Дополнительно" style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 6 }}>
                      Согласование примыкания (п.12)
                    </div>
                    {editing
                      ? <Input.TextArea
                          value={editData.proezd_agreement}
                          onChange={(e) => setEditData({ ...editData, proezd_agreement: e.target.value })}
                          rows={5}
                          placeholder="Текст согласования на примыкание к автодороге"
                        />
                      : <div style={{ whiteSpace: 'pre-wrap' }}>{permit.proezd_agreement || '—'}</div>
                    }
                  </Card>
                </>
              );
            })(),
          },
          {
            key: 'spatial',
            label: 'Пространственный анализ',
            children: (
              <>
                <div style={{ marginBottom: 16 }}>
                  <Button
                    icon={<ReloadOutlined />}
                    loading={actionLoading.spatial}
                    onClick={handleSpatialAnalysis}
                  >
                    Пересчитать пространственный анализ
                  </Button>
                </div>
                {renderSpatialAnalysis()}
              </>
            ),
          },
        ]} />
      </div>
    </div>
  );
};

export default RRRCard;
