/**
 * Real-time sensor data display component.
 * Uses WebSocket to show live sensor readings with automatic updates.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useFarmWebSocket, MESSAGE_TYPES } from '../../hooks/useWebSocket';
import './SensorRealTimeDisplay.css';

const SensorRealTimeDisplay = ({ farmId, deviceFilter = null, showAlerts = true }) => {
  const [sensorData, setSensorData] = useState(new Map());
  const [alerts, setAlerts] = useState([]);
  const [deviceStatus, setDeviceStatus] = useState({});
  const [lastUpdate, setLastUpdate] = useState(null);

  // WebSocket connection for the farm
  const {
    isConnected,
    connectionState,
    error,
    addMessageHandler,
    subscribe
  } = useFarmWebSocket(farmId, {
    onConnect: () => {
      console.log(`Connected to farm ${farmId} WebSocket`);
      // Subscribe to sensor data and alerts for this farm
      subscribe({
        types: [MESSAGE_TYPES.SENSOR_DATA, MESSAGE_TYPES.ALERT, MESSAGE_TYPES.DEVICE_STATUS],
        farm_id: farmId,
        device_filter: deviceFilter
      });
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    }
  });

  // Handle incoming sensor data
  const handleSensorData = useCallback((message) => {
    const { data } = message;
    
    // Apply device filter if specified
    if (deviceFilter && data.device_id !== deviceFilter) {
      return;
    }

    // Update sensor data
    setSensorData(prev => {
      const newData = new Map(prev);
      const key = `${data.device_id}_${data.measurement_type}`;
      
      newData.set(key, {
        ...data,
        receivedAt: new Date()
      });
      
      return newData;
    });

    setLastUpdate(new Date());
  }, [deviceFilter]);

  // Handle incoming alerts
  const handleAlert = useCallback((message) => {
    const { data } = message;
    
    // Apply device filter if specified
    if (deviceFilter && data.device_id !== deviceFilter) {
      return;
    }

    setAlerts(prev => {
      const newAlerts = [data, ...prev.slice(0, 9)]; // Keep last 10 alerts
      return newAlerts;
    });
  }, [deviceFilter]);

  // Handle device status updates
  const handleDeviceStatus = useCallback((message) => {
    const { data } = message;
    
    setDeviceStatus(prev => ({
      ...prev,
      [data.farm_id]: data
    }));
  }, []);

  // Set up message handlers
  useEffect(() => {
    const cleanupHandlers = [
      addMessageHandler(MESSAGE_TYPES.SENSOR_DATA, handleSensorData),
      addMessageHandler(MESSAGE_TYPES.ALERT, handleAlert),
      addMessageHandler(MESSAGE_TYPES.DEVICE_STATUS, handleDeviceStatus)
    ];

    return () => {
      cleanupHandlers.forEach(cleanup => cleanup());
    };
  }, [addMessageHandler, handleSensorData, handleAlert, handleDeviceStatus]);

  // Group sensor data by device
  const groupedData = React.useMemo(() => {
    const groups = {};
    
    for (const [key, data] of sensorData) {
      if (!groups[data.device_id]) {
        groups[data.device_id] = {
          device_id: data.device_id,
          device_type: data.device_type,
          location: data.location,
          measurements: {}
        };
      }
      
      groups[data.device_id].measurements[data.measurement_type] = data;
    }
    
    return groups;
  }, [sensorData]);

  // Connection status indicator
  const ConnectionStatus = () => (
    <div className={`connection-status ${connectionState}`}>
      <div className="status-indicator"></div>
      <span className="status-text">
        {isConnected ? 'Connected' : connectionState}
      </span>
      {error && <span className="error-text">({error})</span>}
    </div>
  );

  // Measurement value display with status
  const MeasurementValue = ({ measurement }) => {
    const isStale = new Date() - new Date(measurement.timestamp) > 60000; // 1 minute
    
    return (
      <div className={`measurement-value ${isStale ? 'stale' : 'fresh'}`}>
        <div className="value">
          {measurement.value.toFixed(2)}
          <span className="unit">{measurement.unit}</span>
        </div>
        <div className="type">{measurement.measurement_type}</div>
        <div className="timestamp">
          {new Date(measurement.timestamp).toLocaleTimeString()}
        </div>
      </div>
    );
  };

  // Device card component
  const DeviceCard = ({ device }) => (
    <div className="device-card">
      <div className="device-header">
        <h3>{device.device_id}</h3>
        <span className="device-type">{device.device_type}</span>
        {device.location && <span className="location">{device.location}</span>}
      </div>
      
      <div className="measurements-grid">
        {Object.values(device.measurements).map(measurement => (
          <MeasurementValue 
            key={`${measurement.device_id}_${measurement.measurement_type}`}
            measurement={measurement} 
          />
        ))}
      </div>
    </div>
  );

  // Alert component
  const AlertItem = ({ alert }) => (
    <div className={`alert-item ${alert.severity}`}>
      <div className="alert-header">
        <span className="severity">{alert.severity.toUpperCase()}</span>
        <span className="device">{alert.device_id}</span>
        <span className="time">
          {new Date(alert.created_at).toLocaleTimeString()}
        </span>
      </div>
      <div className="alert-message">{alert.message}</div>
    </div>
  );

  return (
    <div className="sensor-realtime-display">
      <div className="display-header">
        <h2>Real-time Sensor Data - Farm {farmId}</h2>
        <ConnectionStatus />
        {lastUpdate && (
          <div className="last-update">
            Last update: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </div>

      {deviceStatus[farmId] && (
        <div className="farm-status">
          <div className="status-item">
            <span className="label">Online Devices:</span>
            <span className="value">{deviceStatus[farmId].online_devices}</span>
          </div>
          <div className="status-item">
            <span className="label">Offline Devices:</span>
            <span className="value">{deviceStatus[farmId].offline_devices}</span>
          </div>
          <div className="status-item">
            <span className="label">Total Devices:</span>
            <span className="value">{deviceStatus[farmId].total_devices}</span>
          </div>
        </div>
      )}

      <div className="content-grid">
        <div className="devices-section">
          <h3>Devices</h3>
          <div className="devices-grid">
            {Object.values(groupedData).length > 0 ? (
              Object.values(groupedData).map(device => (
                <DeviceCard key={device.device_id} device={device} />
              ))
            ) : (
              <div className="no-data">
                {isConnected ? 'No sensor data received yet' : 'Connecting to real-time data...'}
              </div>
            )}
          </div>
        </div>

        {showAlerts && (
          <div className="alerts-section">
            <h3>Recent Alerts</h3>
            <div className="alerts-list">
              {alerts.length > 0 ? (
                alerts.map((alert, index) => (
                  <AlertItem key={`${alert.id}_${index}`} alert={alert} />
                ))
              ) : (
                <div className="no-alerts">No alerts</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SensorRealTimeDisplay;