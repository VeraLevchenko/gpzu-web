import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../../services/api';
import './LoginForm.css';

const LoginForm = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      localStorage.setItem('auth', JSON.stringify({ username: values.username, password: values.password }));
      await authApi.checkAuth();
      message.success('Вход выполнен успешно');
      navigate('/');
    } catch (error) {
      message.error('Неверные учётные данные');
      localStorage.removeItem('auth');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card" title={<div className="login-title"><h2>ГПЗУ Web</h2><p>Система выдачи градостроительных планов</p></div>}>
        <Form name="login" onFinish={onFinish} autoComplete="off" size="large">
          <Form.Item name="username" rules={[{ required: true, message: 'Введите логин' }]}>
            <Input prefix={<UserOutlined />} placeholder="Логин" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: 'Введите пароль' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>Войти в систему</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default LoginForm;
