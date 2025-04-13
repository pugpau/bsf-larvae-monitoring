import React, { useState, useEffect } from 'react';
import { getLatestSensorData, getAllSensorData } from '../../api/sensors';
import './SensorDeviceList.css';

/**
 * SensorDeviceList Component
 * 
 * Displays a list of sensor devices and their most recent data.
 * Allows filtering by farm_id and refreshing the data.
 */
const SensorDeviceList = ({ farmId }) => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSensorData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let data;
      
      if (farmId) {
        data = await getLatestSensorData(farmId);
        const deviceArray = Object.entries(data).map(([deviceId, data]) => ({
          deviceId,
          deviceType: data.device_type,
          lastUpdated: new Date(data.last_updated),
          measurements: data.measurements
        }));
        setDevices(deviceArray);
      } else {
        data = await getAllSensorData();
        setDevices(data);
      }
    } catch (err) {
      console.error("Error fetching sensor data:", err);
      setError("Failed to load sensor data. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSensorData();
  }, [farmId]);

  if (loading) {
    return <div className="sensor-loading">Loading sensor data...</div>;
  }

  if (error) {
    return <div className="sensor-error">{error}</div>;
  }

  if (devices.length === 0) {
    return <div className="sensor-empty">No sensor devices found.</div>;
  }

  return (
    <div className="sensor-device-list">
      <div className="sensor-header">
        <h2>Sensor Devices</h2>
        <button onClick={fetchSensorData} className="refresh-button">
          Refresh Data
        </button>
      </div>
      
      <div className="device-grid">
        {devices.map(device => (
          <div key={device.deviceId} className="device-card">
            <div className="device-header">
              <h3>{device.deviceId}</h3>
              <span className="device-type">{device.deviceType}</span>
            </div>
            
            <div className="device-last-updated">
              Last updated: {device.lastUpdated.toLocaleString()}
            </div>
            
            <div className="measurements-container">
              {Object.entries(device.measurements || {}).map(([key, value]) => (
                <div key={key} className="measurement-item">
                  <span className="measurement-label">{key}:</span>
                  <span className="measurement-value">{value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SensorDeviceList;
