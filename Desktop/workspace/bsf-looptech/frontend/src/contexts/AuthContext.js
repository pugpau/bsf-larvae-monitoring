/**
 * Authentication Context Provider
 * Manages authentication state and provides auth functions throughout the app
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

// Configure axios defaults
axios.defaults.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
        // Development mode: Check for demo token
        if (process.env.NODE_ENV === 'development' && token === 'demo-token') {
          // Use mock user data for development
          const mockUser = {
            id: '1',
            username: 'demo',
            role: 'admin',
            permissions: ['read', 'write', 'admin']
          };
          setUser(mockUser);
        } else {
          try {
            // Set auth header
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            
            // Get current user
            const response = await axios.get('/auth/me');
            setUser(response.data);
          } catch (err) {
            console.error('Auth check failed:', err);
            // Clear invalid token
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            delete axios.defaults.headers.common['Authorization'];
          }
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
      
      // Development mode: Allow demo login
      if (process.env.NODE_ENV === 'development' && 
          username === 'demo' && password === 'demo') {
        
        // Mock user data for development
        const mockUser = {
          id: '1',
          username: 'demo',
          role: 'admin',
          permissions: ['read', 'write', 'admin']
        };
        
        // Store mock tokens
        localStorage.setItem('accessToken', 'demo-token');
        localStorage.setItem('refreshToken', 'demo-refresh-token');
        
        setUser(mockUser);
        return { success: true };
      }
      
      // Create form data for OAuth2 compatibility
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await axios.post('/auth/login', {
        username,
        password
      });

      const { access_token, refresh_token, token_type } = response.data;

      // Store tokens
      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', refresh_token);

      // Set auth header
      axios.defaults.headers.common['Authorization'] = `${token_type} ${access_token}`;

      // Get user info
      const userResponse = await axios.get('/auth/me');
      setUser(userResponse.data);

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

    // Clear local state and storage
    setUser(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    delete axios.defaults.headers.common['Authorization'];
  };

  // Refresh token function
  const refreshAccessToken = async () => {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) {
        throw new Error('No refresh token');
      }

      const response = await axios.post('/auth/refresh', {
        refresh_token: refreshToken
      });

      const { access_token } = response.data;

      // Update token
      localStorage.setItem('accessToken', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return access_token;
    } catch (err) {
      console.error('Token refresh failed:', err);
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
  }, []);

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