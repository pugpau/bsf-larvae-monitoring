/**
 * Custom React hook for WebSocket connection management.
 * Provides real-time data streaming, connection management, and message handling.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

// WebSocket connection states
export const CONNECTION_STATES = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
  RECONNECTING: 'reconnecting'
};

// Message types from backend
export const MESSAGE_TYPES = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  HEARTBEAT: 'heartbeat',
  ERROR: 'error',
  SENSOR_DATA: 'sensor_data',
  DEVICE_STATUS: 'device_status',
  ALERT: 'alert',
  SYSTEM_STATUS: 'system_status',
  SUBSCRIBE: 'subscribe',
  UNSUBSCRIBE: 'unsubscribe'
};

/**
 * Custom hook for WebSocket connection management
 * @param {string} url - WebSocket URL
 * @param {Object} options - Configuration options
 * @returns {Object} WebSocket state and methods
 */
export const useWebSocket = (url, options = {}) => {
  const {
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000,
    onConnect = () => {},
    onDisconnect = () => {},
    onError = () => {},
    onMessage = () => {},
    autoConnect = true
  } = options;
  
  const { isAuthenticated } = useAuth();

  // State management
  const [connectionState, setConnectionState] = useState(CONNECTION_STATES.DISCONNECTED);
  const [lastMessage, setLastMessage] = useState(null);
  const [messageHistory, setMessageHistory] = useState([]);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    messagesReceived: 0,
    messagesSent: 0,
    connectionAttempts: 0,
    lastConnectedAt: null,
    lastDisconnectedAt: null
  });

  // Refs for WebSocket and intervals
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const mountedRef = useRef(true);

  // Message handlers storage
  const messageHandlersRef = useRef(new Map());

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, []);

  // Auto-connect on mount if authenticated
  useEffect(() => {
    if (autoConnect && url && isAuthenticated) {
      connect();
    } else if (!isAuthenticated && wsRef.current) {
      disconnect();
    }
  }, [url, autoConnect, isAuthenticated]);

  /**
   * Establish WebSocket connection
   */
  const connect = useCallback(() => {
    if (!url || !mountedRef.current || !isAuthenticated) return;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.warn('WebSocket is already connected');
      return;
    }

    // Skip WebSocket connection in development mode if demo token
    const token = localStorage.getItem('accessToken');
    if (process.env.NODE_ENV === 'development' && token === 'demo-token') {
      console.log('Skipping WebSocket connection in demo mode');
      setConnectionState(CONNECTION_STATES.DISCONNECTED);
      return;
    }

    setConnectionState(CONNECTION_STATES.CONNECTING);
    setError(null);

    try {
      // Add auth token to WebSocket URL
      const wsUrl = token ? `${url}?token=${token}` : url;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = (event) => {
        if (!mountedRef.current) return;

        console.log('WebSocket connected:', url);
        setConnectionState(CONNECTION_STATES.CONNECTED);
        setStats(prev => ({
          ...prev,
          connectionAttempts: prev.connectionAttempts + 1,
          lastConnectedAt: new Date()
        }));

        reconnectAttemptsRef.current = 0;
        startHeartbeat();
        onConnect(event);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;

        try {
          const messageData = JSON.parse(event.data);
          
          setLastMessage(messageData);
          setMessageHistory(prev => {
            const newHistory = [...prev, { ...messageData, receivedAt: new Date() }];
            // Keep only last 100 messages to prevent memory issues
            return newHistory.slice(-100);
          });

          setStats(prev => ({
            ...prev,
            messagesReceived: prev.messagesReceived + 1
          }));

          // Handle heartbeat responses
          if (messageData.type === MESSAGE_TYPES.HEARTBEAT) {
            console.debug('Heartbeat received');
            return;
          }

          // Call global message handler
          onMessage(messageData);

          // Call type-specific handlers
          const handlers = messageHandlersRef.current.get(messageData.type) || [];
          handlers.forEach(handler => {
            try {
              handler(messageData);
            } catch (error) {
              console.error('Error in message handler:', error);
            }
          });

        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setError(`Message parsing error: ${error.message}`);
        }
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;

        console.log('WebSocket disconnected:', event.code, event.reason);
        setConnectionState(CONNECTION_STATES.DISCONNECTED);
        setStats(prev => ({
          ...prev,
          lastDisconnectedAt: new Date()
        }));

        stopHeartbeat();
        onDisconnect(event);

        // Attempt reconnection if enabled and not a normal closure
        if (reconnect && event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          attemptReconnect();
        }
      };

      ws.onerror = (event) => {
        if (!mountedRef.current) return;

        console.error('WebSocket error:', event);
        setConnectionState(CONNECTION_STATES.ERROR);
        setError('WebSocket connection error');
        onError(event);
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setConnectionState(CONNECTION_STATES.ERROR);
      setError(`Connection error: ${error.message}`);
      onError(error);
    }
  }, [url, onConnect, onDisconnect, onError, onMessage, reconnect, maxReconnectAttempts, isAuthenticated]);

  /**
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopHeartbeat();

    if (wsRef.current) {
      wsRef.current.close(1000, 'Normal closure');
      wsRef.current = null;
    }

    setConnectionState(CONNECTION_STATES.DISCONNECTED);
  }, []);

  /**
   * Attempt to reconnect with exponential backoff
   */
  const attemptReconnect = useCallback(() => {
    if (!reconnect || !mountedRef.current) return;

    reconnectAttemptsRef.current += 1;
    const delay = Math.min(reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1), 30000);

    console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts}) in ${delay}ms`);
    setConnectionState(CONNECTION_STATES.RECONNECTING);

    reconnectTimeoutRef.current = setTimeout(() => {
      if (mountedRef.current) {
        connect();
      }
    }, delay);
  }, [connect, reconnect, reconnectInterval, maxReconnectAttempts]);

  /**
   * Send message through WebSocket
   */
  const sendMessage = useCallback((message) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected. Cannot send message:', message);
      return false;
    }

    try {
      const messageString = typeof message === 'string' ? message : JSON.stringify(message);
      wsRef.current.send(messageString);
      
      setStats(prev => ({
        ...prev,
        messagesSent: prev.messagesSent + 1
      }));

      console.debug('Message sent:', message);
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      setError(`Send error: ${error.message}`);
      return false;
    }
  }, []);

  /**
   * Subscribe to specific message types or data streams
   */
  const subscribe = useCallback((subscriptionData) => {
    const subscribeMessage = {
      type: MESSAGE_TYPES.SUBSCRIBE,
      data: subscriptionData,
      timestamp: new Date().toISOString()
    };

    return sendMessage(subscribeMessage);
  }, [sendMessage]);

  /**
   * Add message handler for specific message type
   */
  const addMessageHandler = useCallback((messageType, handler) => {
    if (!messageHandlersRef.current.has(messageType)) {
      messageHandlersRef.current.set(messageType, []);
    }
    messageHandlersRef.current.get(messageType).push(handler);

    // Return cleanup function
    return () => {
      const handlers = messageHandlersRef.current.get(messageType) || [];
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    };
  }, []);

  /**
   * Start heartbeat to keep connection alive
   */
  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }

    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendMessage({
          type: MESSAGE_TYPES.HEARTBEAT,
          timestamp: new Date().toISOString()
        });
      }
    }, heartbeatInterval);
  }, [sendMessage, heartbeatInterval]);

  /**
   * Stop heartbeat
   */
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  /**
   * Clear message history
   */
  const clearHistory = useCallback(() => {
    setMessageHistory([]);
    setLastMessage(null);
  }, []);

  /**
   * Get connection info
   */
  const getConnectionInfo = useCallback(() => {
    return {
      url,
      state: connectionState,
      readyState: wsRef.current?.readyState,
      reconnectAttempts: reconnectAttemptsRef.current,
      error,
      stats
    };
  }, [url, connectionState, error, stats]);

  return {
    // Connection state
    connectionState,
    isConnected: connectionState === CONNECTION_STATES.CONNECTED,
    isConnecting: connectionState === CONNECTION_STATES.CONNECTING,
    isReconnecting: connectionState === CONNECTION_STATES.RECONNECTING,
    error,

    // Data
    lastMessage,
    messageHistory,
    stats,

    // Methods
    connect,
    disconnect,
    sendMessage,
    subscribe,
    addMessageHandler,
    clearHistory,
    getConnectionInfo
  };
};

/**
 * Hook for farm-specific WebSocket connection
 */
export const useFarmWebSocket = (farmId, options = {}) => {
  const url = farmId ? `ws://localhost:8000/ws/farm/${farmId}` : null;
  return useWebSocket(url, options);
};

/**
 * Hook for device-specific WebSocket connection
 */
export const useDeviceWebSocket = (deviceId, options = {}) => {
  const url = deviceId ? `ws://localhost:8000/ws/device/${deviceId}` : null;
  return useWebSocket(url, options);
};

export default useWebSocket;