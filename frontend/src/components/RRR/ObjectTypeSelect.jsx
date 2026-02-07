// frontend/src/components/RRR/ObjectTypeSelect.jsx
import React, { useState, useEffect } from 'react';
import { Select, Tooltip } from 'antd';
import { rrrApi } from '../../services/api';

const { Option } = Select;

const ObjectTypeSelect = ({ value, onChange, style }) => {
  const [objectTypes, setObjectTypes] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadTypes = async () => {
      setLoading(true);
      try {
        const response = await rrrApi.getObjectTypes();
        setObjectTypes(response.data.data || []);
      } catch (error) {
        console.error('Ошибка загрузки справочника объектов:', error);
      } finally {
        setLoading(false);
      }
    };
    loadTypes();
  }, []);

  const handleChange = (selectedValue) => {
    const selectedType = objectTypes.find(
      (t) => `${t.number}. ${t.short_name}` === selectedValue
    );
    if (onChange) {
      onChange(selectedValue, selectedType);
    }
  };

  return (
    <Select
      showSearch
      placeholder="Выберите вид объекта"
      value={value}
      onChange={handleChange}
      loading={loading}
      style={style || { width: '100%' }}
      filterOption={(input, option) =>
        option.children
          .toString()
          .toLowerCase()
          .includes(input.toLowerCase())
      }
      allowClear
    >
      {objectTypes.map((type) => {
        const label = `${type.number}. ${type.short_name}`;
        return (
          <Option key={type.number} value={label}>
            <Tooltip title={type.full_name} placement="right">
              <span>{label}</span>
            </Tooltip>
          </Option>
        );
      })}
    </Select>
  );
};

export default ObjectTypeSelect;
