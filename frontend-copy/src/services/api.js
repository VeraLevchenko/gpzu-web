import axios from 'axios';

// Умное определение API URL
const getApiUrl = () => {
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return `http://${hostname}:8000`;
};

const API_BASE_URL = getApiUrl();

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

// ========================================
// ОБЩИЕ ПАРСЕРЫ (используются всеми модулями)
// ========================================
export const parsersApi = {
  // Парсинг заявления (DOCX)
  parseApplication: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/parsers/application', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // Парсинг ЕГРН (XML)
  parseEgrn: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/parsers/egrn', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // Пространственный анализ
  spatialAnalysis: (data) => {
    return api.post('/api/parsers/spatial', data);
  }
};

// ========================================
// МОДУЛЬ: KAITEN
// ========================================
export const kaitenApi = {
  // ИСПОЛЬЗУЕТ: parsersApi.parseApplication
  parseApplication: (file) => parsersApi.parseApplication(file),
  
  createTask: (data) => api.post('/api/gp/kaiten/create-task', data),
};

// ========================================
// МОДУЛЬ: MID/MIF
// ========================================
export const midmifApi = {
  // ИСПОЛЬЗУЕТ: parsersApi.parseEgrn
  previewCoordinates: (file) => parsersApi.parseEgrn(file),
  
  generateMidMif: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/gp/midmif/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob'
    });
    return response;
  }
};

// ========================================
// МОДУЛЬ: ТУ (Технические условия)
// ========================================
export const tuApi = {
  // ИСПОЛЬЗУЕТ: parsersApi.parseApplication
  parseApplication: (file) => parsersApi.parseApplication(file),

  // ИСПОЛЬЗУЕТ: parsersApi.parseEgrn
  parseEgrn: (file) => parsersApi.parseEgrn(file),

  generateTu: async (data) => {
    const formData = new FormData();
    formData.append('cadnum', data.cadnum);
    formData.append('address', data.address);
    formData.append('area', data.area);
    formData.append('vri', data.vri);
    formData.append('app_number', data.app_number);
    formData.append('app_date', data.app_date);
    formData.append('applicant', data.applicant);

    const response = await api.post('/api/gp/tu/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
    });
    
    return response;
  }
};

// ========================================
// МОДУЛЬ: ГРАДПЛАН
// ========================================
export const gradplanApi = {
  // ИСПОЛЬЗУЕТ: parsersApi.parseEgrn
  parseEgrn: (file) => parsersApi.parseEgrn(file),

  // ИСПОЛЬЗУЕТ: parsersApi.spatialAnalysis
  spatialAnalysis: (data) => parsersApi.spatialAnalysis(data),

  generate: async (data) => {
    const response = await api.post('/api/gp/gradplan/generate', data, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response;
  },

  download: async (filename) => {
    const response = await api.get(`/api/gp/gradplan/download/${filename}`, {
      responseType: 'blob'
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    
    return response;
  }
};

// ========================================
// АУТЕНТИФИКАЦИЯ
// ========================================
export const authApi = {
  checkAuth: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout'),
};
