/**
 * API Configuration and Utilities
 * Provides configured axios instance with authentication and analytics API methods
 */

import axios from 'axios';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await api.post('/api/auth/refresh', {
          refresh_token: refreshToken
        });

        const { access_token } = response.data;
        localStorage.setItem('accessToken', access_token);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Analytics API service methods
 */
export const analyticsAPI = {
  // Statistics endpoints
  getStatistics: (params) => api.get('/analytics/statistics', { params }),
  getDashboardStatistics: () => api.get('/analytics/statistics/dashboard'),
  getAggregatedData: (params) => api.get('/analytics/aggregation', { params }),

  // Trend analysis endpoints
  analyzeTrend: (params) => api.get('/analytics/trends/analyze', { params }),
  detectChangePoints: (params) => api.get('/analytics/trends/change-points', { params }),
  getForecast: (params) => api.get('/analytics/trends/forecast', { params }),

  // Report generation endpoints
  generateReport: (config) => api.post('/analytics/reports/generate', config),
  getReports: (params) => api.get('/analytics/reports', { params }),
  downloadReport: (reportId, format = 'json') => 
    api.get(`/analytics/reports/${reportId}/download`, { params: { format } }),

  // Machine Learning endpoints
  trainPipeline: (config) => api.post('/analytics/ml/train-pipeline', config),
  predict: (data) => api.post('/analytics/ml/predict', data),
  detectAnomalies: (params) => api.get('/analytics/ml/detect-anomalies', { params }),
  getModelPerformance: () => api.get('/analytics/ml/performance'),
  getModels: () => api.get('/analytics/ml/models'),
  deleteModel: (modelId) => api.delete(`/analytics/ml/models/${modelId}`),

  // Feature engineering endpoints
  extractFeatures: (config) => api.post('/analytics/features/extract', config),
  getFeatureImportance: (modelId) => api.get(`/analytics/features/importance/${modelId}`)
};

/**
 * Sensor API service methods
 */
export const sensorAPI = {
  getSensors: () => api.get('/sensors'),
  getSensorData: (sensorId, params) => api.get(`/sensors/${sensorId}/data`, { params }),
  getRecentReadings: (params) => api.get('/sensors/readings/recent', { params }),
  createSensor: (data) => api.post('/sensors', data),
  updateSensor: (sensorId, data) => api.put(`/sensors/${sensorId}`, data),
  deleteSensor: (sensorId) => api.delete(`/sensors/${sensorId}`)
};

/**
 * Substrate API service methods
 */
export const substrateAPI = {
  getSubstrates: () => api.get('/substrate'),
  getSubstrateTypes: () => api.get('/substrate/types'),
  createSubstrate: (data) => api.post('/substrate', data),
  updateSubstrate: (substrateId, data) => api.put(`/substrate/${substrateId}`, data),
  deleteSubstrate: (substrateId) => api.delete(`/substrate/${substrateId}`)
};

/**
 * Utility functions for API operations
 */
export const apiUtils = {
  /**
   * Handle API errors with user-friendly messages
   */
  handleError: (error) => {
    if (error.response) {
      const status = error.response.status;
      const message = error.response.data?.message || error.message;
      
      switch (status) {
        case 400:
          return `Bad request: ${message}`;
        case 401:
          return 'Authentication required. Please log in again.';
        case 403:
          return 'Access denied. You do not have permission for this operation.';
        case 404:
          return 'Resource not found.';
        case 422:
          return `Validation error: ${message}`;
        case 500:
          return 'Server error. Please try again later.';
        default:
          return message || 'An unexpected error occurred.';
      }
    } else if (error.request) {
      return 'Network error. Please check your internet connection.';
    } else {
      return error.message || 'An unexpected error occurred.';
    }
  },

  /**
   * Format date for API requests
   */
  formatDate: (date) => {
    return date.toISOString();
  },

  /**
   * Parse API date string
   */
  parseDate: (dateString) => {
    return new Date(dateString);
  },

  /**
   * Debounce function for API calls
   */
  debounce: (func, delay) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(null, args), delay);
    };
  },

  /**
   * Retry API call with exponential backoff
   */
  retryWithBackoff: async (apiCall, maxRetries = 3, baseDelay = 1000) => {
    let lastError;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await apiCall();
      } catch (error) {
        lastError = error;
        
        if (attempt === maxRetries) {
          break;
        }
        
        // Don't retry client errors (4xx)
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          break;
        }
        
        // Calculate delay with exponential backoff
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError;
  }
};

export { api };
export default api;