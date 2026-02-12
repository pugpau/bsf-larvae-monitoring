/**
 * Axios configuration and interceptors
 */

import axios from 'axios';

// Set base URL
axios.defaults.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Send cookies (httpOnly refresh token) with every request
axios.defaults.withCredentials = true;

// ── Shared token refresh mutex ──
// Serializes concurrent refresh requests so only one fires at a time.
let refreshPromise = null;

const refreshAccessToken = async () => {
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
const attachInterceptors = (instance) => {
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
      const originalRequest = error.config;
      if (error.response?.status === 401 && !originalRequest._retry) {
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
export const createAuthenticatedClient = (baseURL, timeout = 10000) => {
  const instance = axios.create({
    baseURL,
    timeout,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
  });

  attachInterceptors(instance);

  return instance;
};

export default axios;
