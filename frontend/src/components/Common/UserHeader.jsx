// frontend/src/components/Common/UserHeader.jsx
import React, { useState, useEffect } from 'react';
import { UserOutlined, LogoutOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../../services/api';
import './UserHeader.css';

/**
 * Компонент шапки с отображением текущего пользователя и кнопкой выхода
 * 
 * Props:
 * - title: заголовок страницы (опционально)
 * - showBackButton: показывать ли кнопку "Назад" (по умолчанию false)
 * - onBack: обработчик кнопки "Назад" (если не указан - возврат на главную)
 */
const UserHeader = ({ title, showBackButton = false, onBack }) => {
  const [username, setUsername] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Загружаем имя пользователя из localStorage
    const auth = localStorage.getItem('auth');
    if (auth) {
      try {
        const { username: storedUsername } = JSON.parse(auth);
        setUsername(storedUsername || 'Пользователь');
      } catch (error) {
        console.error('Ошибка загрузки данных пользователя:', error);
        setUsername('Пользователь');
      }
    }
  }, []);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.log('Logout error:', error);
    } finally {
      localStorage.removeItem('auth');
      navigate('/login');
    }
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate('/');
    }
  };

  return (
    <div className="user-header">
      <div className="user-header-content">
        {/* Левая часть - кнопка назад и заголовок */}
        <div className="user-header-left">
          {showBackButton && (
            <button className="back-btn" onClick={handleBack}>
              ← Назад
            </button>
          )}
          {title && <h1 className="user-header-title">{title}</h1>}
        </div>

        {/* Правая часть - информация о пользователе */}
        <div className="user-header-right">
          <div className="user-info">
            <UserOutlined className="user-icon" />
            <span className="user-name">{username}</span>
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            <LogoutOutlined /> Выйти
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserHeader;