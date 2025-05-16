import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { getDeviceSensorData } from '../../api/sensors';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const SensorDetail = () => {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [sensorData, setSensorData] = useState([]);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('24h'); // Default to 24 hours
  
  // Default farm ID - in a real app, this would come from user selection or auth
  const farmId = 'farm-001';

  useEffect(() => {
    const fetchSensorData = async () => {
      try {
        setLoading(true);
        
        // Calculate time range
        const endTime = new Date();
        let startTime = new Date();
        
        switch (timeRange) {
          case '1h':
            startTime.setHours(startTime.getHours() - 1);
            break;
          case '6h':
            startTime.setHours(startTime.getHours() - 6);
            break;
          case '24h':
            startTime.setHours(startTime.getHours() - 24);
            break;
          case '7d':
            startTime.setDate(startTime.getDate() - 7);
            break;
          case '30d':
            startTime.setDate(startTime.getDate() - 30);
            break;
          default:
            startTime.setHours(startTime.getHours() - 24);
        }
        
        const params = {
          start_time: startTime.toISOString(),
          end_time: endTime.toISOString(),
        };
        
        const response = await getDeviceSensorData(farmId, id, params);
        setSensorData(response);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching sensor data:', err);
        setError('センサーデータの取得中にエラーが発生しました。');
        setLoading(false);
      }
    };

    fetchSensorData();
  }, [id, farmId, timeRange]);

  // Process data for chart
  const prepareChartData = () => {
    if (!sensorData || sensorData.length === 0) return null;
    
    // Group data by measurement type
    const measurementTypes = [...new Set(sensorData.map(item => item.field))];
    
    // Prepare datasets
    const datasets = measurementTypes.map(type => {
      const filteredData = sensorData
        .filter(item => item.field === type)
        .sort((a, b) => new Date(a.time) - new Date(b.time));
      
      return {
        label: type,
        data: filteredData.map(item => item.value),
        borderColor: getRandomColor(type),
        backgroundColor: getRandomColor(type, 0.2),
        fill: false,
      };
    });
    
    // Prepare labels (timestamps)
    const labels = [...new Set(sensorData.map(item => new Date(item.time).toLocaleString()))]
      .sort((a, b) => new Date(a) - new Date(b));
    
    return {
      labels,
      datasets,
    };
  };
  
  // Generate random color based on string
  const getRandomColor = (str, alpha = 1) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const r = (hash & 0xFF) % 256;
    const g = ((hash >> 8) & 0xFF) % 256;
    const b = ((hash >> 16) & 0xFF) % 256;
    
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const chartData = prepareChartData();
  
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: `センサー ${id} データ`,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: '時間',
        },
      },
      y: {
        title: {
          display: true,
          text: '値',
        },
      },
    },
  };

  if (loading) {
    return <div>センサーデータを読み込み中...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div className="sensor-detail">
      <h1>センサー {id} 詳細</h1>
      
      <div className="time-range-selector">
        <label>期間: </label>
        <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
          <option value="1h">1時間</option>
          <option value="6h">6時間</option>
          <option value="24h">24時間</option>
          <option value="7d">7日間</option>
          <option value="30d">30日間</option>
        </select>
      </div>
      
      {sensorData.length === 0 ? (
        <p>選択した期間のセンサーデータがありません</p>
      ) : (
        <>
          <div className="sensor-chart">
            {chartData && <Line data={chartData} options={chartOptions} />}
          </div>
          
          <div className="sensor-stats">
            <h2>統計情報</h2>
            {/* Group data by measurement type and calculate stats */}
            {[...new Set(sensorData.map(item => item.field))].map(type => {
              const values = sensorData
                .filter(item => item.field === type)
                .map(item => item.value);
              
              const min = Math.min(...values);
              const max = Math.max(...values);
              const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
              
              return (
                <div key={type} className="stat-item">
                  <h3>{type}</h3>
                  <p>最小値: {min.toFixed(2)}</p>
                  <p>最大値: {max.toFixed(2)}</p>
                  <p>平均値: {avg.toFixed(2)}</p>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default SensorDetail;
