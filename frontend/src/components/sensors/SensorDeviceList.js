import React, { useState, useEffect } from 'react';
import { getLatestSensorData } from '../../api/sensors';

/**
 * Component to display a list of sensor devices
 */
const SensorDeviceList = () => {
  const [loading, setLoading] = useState(true);
  const [sensorData, setSensorData] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getLatestSensorData();
        setSensorData(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load sensor data');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div>Loading sensor data...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="sensor-device-list">
      <h2>Sensor Devices</h2>
      {/* Display sensor data here */}
      <div className="sensor-list">
        {Object.keys(sensorData).length === 0 ? (
          <p>No sensor devices found</p>
        ) : (
          <p>Sensor data would be displayed here</p>
        )}
      </div>
    </div>
  );
};

export default SensorDeviceList;
