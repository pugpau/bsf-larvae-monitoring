import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getLatestFarmData } from '../../api/sensors';

const SensorList = () => {
  const [loading, setLoading] = useState(true);
  const [sensorData, setSensorData] = useState({});
  const [error, setError] = useState(null);
  
  // Default farm ID - in a real app, this would come from user selection or auth
  const farmId = 'farm-001';

  useEffect(() => {
    const fetchSensorData = async () => {
      try {
        setLoading(true);
        const response = await getLatestFarmData(farmId);
        setSensorData(response);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching sensor data:', err);
        setError('センサーデータの取得中にエラーが発生しました。');
        setLoading(false);
      }
    };

    fetchSensorData();
  }, [farmId]);

  if (loading) {
    return <div>センサーデータを読み込み中...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div>
      <h1>センサーデバイス一覧</h1>
      
      {Object.keys(sensorData).length === 0 ? (
        <p>センサーデバイスが見つかりません</p>
      ) : (
        <div className="sensor-list">
          {Object.entries(sensorData).map(([deviceId, data]) => (
            <div key={deviceId} className="sensor-card">
              <h2>{deviceId}</h2>
              <p>タイプ: {data.device_type}</p>
              <p>最終更新: {new Date(data.last_updated).toLocaleString()}</p>
              
              <h3>測定値</h3>
              <ul>
                {Object.entries(data.measurements || {}).map(([key, value]) => (
                  <li key={key}>
                    {key}: {value}
                  </li>
                ))}
              </ul>
              
              <Link to={`/sensors/${deviceId}`} className="button">
                詳細を表示
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SensorList;
