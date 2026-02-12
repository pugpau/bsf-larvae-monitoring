/**
 * Authentication Context Provider
 * Manages authentication state and provides auth functions throughout the app
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from '../utils/axiosConfig';

// Create Auth Context
const AuthContext = createContext();

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Auth Provider Component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('accessToken');
      if (token) {
        try {
          // Set auth header
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

          // Get current user
          const response = await axios.get('/auth/me');
          setUser(response.data);
        } catch (err) {
          // Clear invalid token
          localStorage.removeItem('accessToken');
          delete axios.defaults.headers.common['Authorization'];
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  // Login function
  const login = async (username, password) => {
    try {
      setError(null);

      const response = await axios.post('/auth/login', {
        username,
        password
      });

      const { access_token, token_type, user } = response.data;

      // Store access token (refresh token is in httpOnly cookie)
      localStorage.setItem('accessToken', access_token);

      // Set auth header
      axios.defaults.headers.common['Authorization'] = `${token_type} ${access_token}`;

      // Set user from login response
      setUser(user);

      return { success: true };
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Login failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // Logout function
  const logout = async () => {
    try {
      await axios.post('/auth/logout');
    } catch (err) {
      console.error('Logout error:', err);
    }

    // Clear local state and storage (refresh token cookie cleared by backend)
    setUser(null);
    localStorage.removeItem('accessToken');
    delete axios.defaults.headers.common['Authorization'];
  };

  // Refresh token function (refresh token sent via httpOnly cookie)
  const refreshAccessToken = async () => {
    try {
      const response = await axios.post('/auth/refresh');

      const { access_token } = response.data;

      // Update token
      localStorage.setItem('accessToken', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return access_token;
    } catch (err) {
      logout();
      throw err;
    }
  };

  // Setup axios interceptor for token refresh
  useEffect(() => {
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('accessToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await refreshAccessToken();
            return axios(originalRequest);
          } catch (refreshError) {
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );

    // Cleanup
    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- interceptors registered once on mount

  // Check if user has permission
  const hasPermission = (permission) => {
    if (!user) return false;
    return user.permissions?.includes(permission) || false;
  };

  // Check if user has role
  const hasRole = (role) => {
    if (!user) return false;
    return user.role === role;
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    refreshAccessToken,
    hasPermission,
    hasRole,
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;