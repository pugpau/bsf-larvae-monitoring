import React, { useState, useEffect } from 'react';
import { getLatestFarmData } from '../../api/sensors';
import { getSubstrateBatches } from '../../api/substrate';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [sensorData, setSensorData] = useState({});
  const [substrateBatches, setSubstrateBatches] = useState([]);
  const [error, setError] = useState(null);
  
  // Default farm ID - in a real app, this would come from user selection or auth
  const farmId = 'farm-001';

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch latest sensor data
        const sensorResponse = await getLatestFarmData(farmId);
        setSensorData(sensorResponse);
        
        // Fetch active substrate batches
        const batchesResponse = await getSubstrateBatches(farmId, true);
        setSubstrateBatches(batchesResponse);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('データの取得中にエラーが発生しました。');
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [farmId]);

  if (loading) {
    return <div>データを読み込み中...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-card">
        <h2>センサー概要</h2>
        {Object.keys(sensorData).length === 0 ? (
          <p>センサーデータがありません</p>
        ) : (
          <div className="sensor-summary">
            <p>接続センサー数: {Object.keys(sensorData).length}</p>
            <ul>
              {Object.entries(sensorData).map(([deviceId, data]) => (
                <li key={deviceId}>
                  {deviceId}: {data.device_type} - 最終更新: {new Date(data.last_updated).toLocaleString()}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      
      <div className="dashboard-card">
        <h2>基質バッチ状況</h2>
        {substrateBatches.length === 0 ? (
          <p>アクティブな基質バッチがありません</p>
        ) : (
          <ul className="substrate-summary">
            {substrateBatches.map(batch => (
              <li key={batch.id}>
                {batch.name || batch.id} - ステータス: {batch.status}
              </li>
            ))}
          </ul>
        )}
      </div>
      
      <div className="dashboard-card">
        <h2>アラート</h2>
        <p>アラートはありません</p>
      </div>
      
      <div className="dashboard-card">
        <h2>システム状態</h2>
        <p>すべてのシステムは正常に動作しています</p>
      </div>
    </div>
  );
};

export default Dashboard;
