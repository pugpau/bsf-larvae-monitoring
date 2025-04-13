import React, { useState, useEffect } from 'react';
import { getAllSensorData } from '../../api/sensors';
import { SensorCharts } from './index';
import './SensorReadingsList.css';

/**
 * SensorReadingsList Component
 * 
 * Displays a list of sensor readings with filtering options
 * and visualization capabilities.
 */
const SensorReadingsList = ({ farmId }) => {
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [filters, setFilters] = useState({
    deviceId: '',
    deviceType: '',
    measurementType: '',
    startTime: '',
    endTime: ''
  });
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [uniqueDevices, setUniqueDevices] = useState([]);

  useEffect(() => {
    const fetchReadings = async () => {
      setLoading(true);
      setError(null);

      try {
        const params = {
          farm_id: farmId,
          device_id: filters.deviceId || undefined,
          device_type: filters.deviceType || undefined,
          measurement_type: filters.measurementType || undefined,
          start_time: filters.startTime || undefined,
          end_time: filters.endTime || undefined
        };

        const data = await getAllSensorData(params);
        setReadings(data);

        const devices = [...new Set(data.map(reading => reading.device_id))];
        setUniqueDevices(devices);
      } catch (err) {
        console.error('Error fetching sensor readings:', err);
        setError('Failed to load sensor readings. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchReadings();
  }, [farmId, filters]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDeviceSelection = (deviceId) => {
    setSelectedDevices(prev => {
      if (prev.includes(deviceId)) {
        return prev.filter(id => id !== deviceId);
      } else {
        return [...prev, deviceId];
      }
    });
  };

  const handleViewModeChange = (mode) => {
    setViewMode(mode);
  };

  const handleResetFilters = () => {
    setFilters({
      deviceId: '',
      deviceType: '',
      measurementType: '',
      startTime: '',
      endTime: ''
    });
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('ja-JP');
  };

  if (loading) {
    return <div className="sensor-readings-loading">センサーデータを読み込み中...</div>;
  }

  if (error) {
    return <div className="sensor-readings-error">{error}</div>;
  }

  return (
    <div className="sensor-readings-container">
      <div className="readings-header">
        <h2>センサー測定値</h2>
        <div className="view-mode-selector">
          <button 
            className={`view-mode-button ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => handleViewModeChange('table')}
          >
            テーブル表示
          </button>
          <button 
            className={`view-mode-button ${viewMode === 'chart' ? 'active' : ''}`}
            onClick={() => handleViewModeChange('chart')}
          >
            グラフ表示
          </button>
        </div>
      </div>

      <div className="filter-section">
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="deviceId">デバイスID</label>
            <input
              type="text"
              id="deviceId"
              name="deviceId"
              value={filters.deviceId}
              onChange={handleFilterChange}
            />
          </div>
          
          <div className="filter-group">
            <label htmlFor="deviceType">デバイスタイプ</label>
            <select
              id="deviceType"
              name="deviceType"
              value={filters.deviceType}
              onChange={handleFilterChange}
            >
              <option value="">すべて</option>
              <option value="temperature">温度センサー</option>
              <option value="humidity">湿度センサー</option>
              <option value="pressure">気圧センサー</option>
              <option value="gas">ガスセンサー</option>
              <option value="multi">マルチセンサー</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label htmlFor="measurementType">測定タイプ</label>
            <select
              id="measurementType"
              name="measurementType"
              value={filters.measurementType}
              onChange={handleFilterChange}
            >
              <option value="">すべて</option>
              <option value="temperature">温度</option>
              <option value="humidity">湿度</option>
              <option value="pressure">気圧</option>
              <option value="gas">ガス濃度</option>
            </select>
          </div>
        </div>
        
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="startTime">開始時間</label>
            <input
              type="datetime-local"
              id="startTime"
              name="startTime"
              value={filters.startTime}
              onChange={handleFilterChange}
            />
          </div>
          
          <div className="filter-group">
            <label htmlFor="endTime">終了時間</label>
            <input
              type="datetime-local"
              id="endTime"
              name="endTime"
              value={filters.endTime}
              onChange={handleFilterChange}
            />
          </div>
          
          <div className="filter-actions">
            <button className="reset-button" onClick={handleResetFilters}>
              フィルターをリセット
            </button>
          </div>
        </div>
      </div>

      {viewMode === 'table' ? (
        <div className="readings-table-container">
          <table className="readings-table">
            <thead>
              <tr>
                <th>選択</th>
                <th>デバイスID</th>
                <th>デバイスタイプ</th>
                <th>測定タイプ</th>
                <th>測定値</th>
                <th>単位</th>
                <th>タイムスタンプ</th>
              </tr>
            </thead>
            <tbody>
              {readings.length === 0 ? (
                <tr>
                  <td colSpan="7" className="no-data">データがありません</td>
                </tr>
              ) : (
                readings.map((reading, index) => (
                  <tr key={index}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedDevices.includes(reading.device_id)}
                        onChange={() => handleDeviceSelection(reading.device_id)}
                      />
                    </td>
                    <td>{reading.device_id}</td>
                    <td>{reading.device_type}</td>
                    <td>{reading.measurement_type}</td>
                    <td>{reading.value}</td>
                    <td>{reading.unit || '-'}</td>
                    <td>{formatTimestamp(reading.timestamp)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="chart-view-container">
          {selectedDevices.length === 0 ? (
            <div className="no-devices-selected">
              グラフを表示するデバイスを選択してください。テーブル表示に切り替えて、デバイスを選択できます。
            </div>
          ) : (
            <SensorCharts
              farmId={farmId}
              deviceIds={selectedDevices}
              startTime={filters.startTime}
              endTime={filters.endTime}
            />
          )}
        </div>
      )}

      <div className="readings-summary">
        <p>
          {readings.length} 件の測定値が見つかりました
          {filters.startTime && filters.endTime && ` (${formatTimestamp(filters.startTime)} から ${formatTimestamp(filters.endTime)} まで)`}
        </p>
      </div>
    </div>
  );
};

export default SensorReadingsList;
