/**
 * Authentication Context Provider
 * Manages authentication state and provides auth functions throughout the app
 */

import React, { createContext, useState, useContext, useEffect, type ReactNode } from 'react';
import axios from '../utils/axiosConfig';
import type { UserProfile, LoginResult, AuthContextValue } from '../types/api';

// Create Auth Context
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Custom hook to use auth context
export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

// Auth Provider Component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        } catch {
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
  const login = async (username: string, password: string): Promise<LoginResult> => {
    try {
      setError(null);

      const response = await axios.post('/auth/login', {
        username,
        password
      });

      const { access_token, token_type, user: loginUser } = response.data;

      // Store access token (refresh token is in httpOnly cookie)
      localStorage.setItem('accessToken', access_token);

      // Set auth header
      axios.defaults.headers.common['Authorization'] = `${token_type} ${access_token}`;

      // Set user from login response
      setUser(loginUser);

      return { success: true };
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const errorMessage = axiosErr.response?.data?.detail || 'Login failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      await axios.post('/auth/logout');
    } catch {
      // Logout error is non-critical
    }

    // Clear local state and storage (refresh token cookie cleared by backend)
    setUser(null);
    localStorage.removeItem('accessToken');
    delete axios.defaults.headers.common['Authorization'];
  };

  // Refresh token function (refresh token sent via httpOnly cookie)
  const refreshAccessToken = async (): Promise<string> => {
    try {
      const response = await axios.post('/auth/refresh');

      const { access_token } = response.data;

      // Update token
      localStorage.setItem('accessToken', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return access_token;
    } catch (err) {
      await logout();
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
  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    return user.permissions?.includes(permission) || false;
  };

  // Check if user has role
  const hasRole = (role: string): boolean => {
    if (!user) return false;
    return user.role === role;
  };

  const value: AuthContextValue = {
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
