/**
 * Axios configuration and interceptors
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

// Set base URL
const API_ROOT = process.env.REACT_APP_API_URL || 'http://localhost:8000';
axios.defaults.baseURL = API_ROOT;

// Send cookies (httpOnly refresh token) with every request
axios.defaults.withCredentials = true;

// Extend request config with retry flag
interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// ── Shared token refresh mutex ──
// Serializes concurrent refresh requests so only one fires at a time.
let refreshPromise: Promise<string> | null = null;

const refreshAccessToken = async (): Promise<string> => {
  if (!refreshPromise) {
    refreshPromise = axios.post('/auth/refresh')
      .then((res) => {
        const { access_token } = res.data;
        localStorage.setItem('accessToken', access_token);
        refreshPromise = null;
        return access_token;
      })
      .catch((err) => {
        refreshPromise = null;
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
        throw err;
      });
  }
  return refreshPromise;
};

/**
 * Attach auth + refresh interceptors to an axios instance.
 */
const attachInterceptors = (instance: AxiosInstance): void => {
  instance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config as RetryableRequestConfig | undefined;
      if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
        originalRequest._retry = true;
        try {
          const newToken = await refreshAccessToken();
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return instance(originalRequest);
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      }
      return Promise.reject(error);
    }
  );
};

// Apply interceptors to the global axios instance
attachInterceptors(axios);

/**
 * Factory: create an axios instance with auth + refresh interceptors.
 * Use this instead of bare axios.create() to get consistent auth behavior.
 * All instances share the same refresh mutex to prevent concurrent refresh requests.
 */
export const createAuthenticatedClient = (baseURL: string, timeout = 10000): AxiosInstance => {
  // Resolve relative paths (e.g. "/api/v1") against the backend root URL
  const resolvedURL = baseURL.startsWith('http') ? baseURL : `${API_ROOT}${baseURL}`;
  const instance = axios.create({
    baseURL: resolvedURL,
    timeout,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
  });

  attachInterceptors(instance);

  return instance;
};

export default axios;
