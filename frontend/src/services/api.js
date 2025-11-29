// frontend/src/services/api.js
import axios from 'axios';

// Умное определение API URL
const getApiUrl = () => {
  const hostname = window.location.hostname;
  
  // Если заходим через localhost - API тоже на localhost
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // Если заходим через IP сервера - API тоже на IP сервера
  return `http://${hostname}:8000`;
};

const API_BASE_URL = getApiUrl();

console.log('🔗 API URL:', API_BASE_URL); // Для отладки

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const auth = localStorage.getItem('auth');
  if (auth) {
    const { username, password } = JSON.parse(auth);
    config.auth = { username, password };
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// ========== KAITEN API ========== //
export const kaitenApi = {
  parseApplication: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/gp/kaiten/parse-application', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  createTask: (data) => api.post('/api/gp/kaiten/create-task', data),
};

// ========== MID/MIF API ========== //
export const midmifApi = {
  /**
   * Предпросмотр координат из ЕГРН
   */
  previewCoordinates: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/gp/midmif/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  /**
   * Генерация MID/MIF файлов
   * Возвращает ZIP архив
   */
  generateMidMif: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/gp/midmif/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob' // ВАЖНО: для скачивания файла
    });
    
    return response;
  }
};

// ========== AUTH API ========== //
export const authApi = {
  checkAuth: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout'),
};