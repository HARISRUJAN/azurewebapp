import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Handle 401 Unauthorized responses - clear invalid token
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is invalid or expired, clear it
      localStorage.removeItem('auth_token');
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const response = await axios.post(`${API_BASE_URL}/auth/login`, params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
    }
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('auth_token');
  },
  
  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

// Search API
export const searchAPI = {
  query: async (question: string, topK: number = 5) => {
    const response = await apiClient.post('/search/query', {
      question,
      top_k: topK,
    });
    return response.data;
  },
};

// Content API
export const contentAPI = {
  ingest: async (document: {
    title: string;
    source: string;
    url?: string;
    content: string;
    metadata?: Record<string, any>;
  }) => {
    const response = await apiClient.post('/content/ingest', document);
    return response.data;
  },
};

// Admin API
export const adminAPI = {
  getOrigins: async () => {
    const response = await apiClient.get('/admin/origins');
    return response.data;
  },
  
  createOrigin: async (origin: {
    name: string;
    url: string;
    frequency_hours?: number;
    enabled?: boolean;
  }) => {
    const response = await apiClient.post('/admin/origins', origin);
    return response.data;
  },
  
  updateOrigin: async (id: number, origin: {
    name?: string;
    url?: string;
    frequency_hours?: number;
    enabled?: boolean;
  }) => {
    const response = await apiClient.put(`/admin/origins/${id}`, origin);
    return response.data;
  },
  
  deleteOrigin: async (id: number) => {
    await apiClient.delete(`/admin/origins/${id}`);
  },
  
  getOriginStatus: async (id: number) => {
    const response = await apiClient.get(`/admin/origins/${id}/status`);
    return response.data;
  },
  
  getHealth: async () => {
    const response = await apiClient.get('/admin/health');
    return response.data;
  },
  
  triggerCrawl: async (originId: number) => {
    const response = await apiClient.post(`/admin/origins/${originId}/crawl`);
    return response.data;
  },
};

export default apiClient;

