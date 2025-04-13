import React, { useState, useEffect } from 'react';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  TimeScale
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { getDeviceSensorData } from '../../api/sensors';
import './SensorCharts.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

/**
 * SensorCharts Component
 * 
 * Displays sensor data in various chart formats:
 * - Time series charts for individual devices
 * - Comparison charts between multiple devices
 * - Tabs for different measurement types
 */
const SensorCharts = ({ farmId, deviceIds, startTime, endTime }) => {
  const [chartData, setChartData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('temperature');
  const [chartType, setChartType] = useState('timeSeries');

  const measurementTypes = [
    { id: 'temperature', label: '温度' },
    { id: 'humidity', label: '湿度' },
    { id: 'pressure', label: '気圧' },
    { id: 'gas', label: 'ガス' }
  ];

  const chartTypes = [
    { id: 'timeSeries', label: '時系列' },
    { id: 'comparison', label: 'デバイス比較' }
  ];

  const deviceColors = [
    'rgba(75, 192, 192, 1)',
    'rgba(255, 99, 132, 1)',
    'rgba(54, 162, 235, 1)',
    'rgba(255, 206, 86, 1)',
    'rgba(153, 102, 255, 1)',
    'rgba(255, 159, 64, 1)'
  ];

  useEffect(() => {
    const fetchData = async () => {
      if (!farmId || !deviceIds || deviceIds.length === 0) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const params = {
          measurement_type: activeTab,
          start_time: startTime,
          end_time: endTime
        };

        const deviceDataPromises = deviceIds.map(deviceId => 
          getDeviceSensorData(farmId, deviceId, params)
        );

        const devicesData = await Promise.all(deviceDataPromises);
        
        processChartData(devicesData, deviceIds);
      } catch (err) {
        console.error('Error fetching sensor data for charts:', err);
        setError('Failed to load chart data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [farmId, deviceIds, activeTab, startTime, endTime]);

  const processChartData = (devicesData, deviceIds) => {
    if (chartType === 'timeSeries') {
      processTimeSeriesData(devicesData, deviceIds);
    } else {
      processComparisonData(devicesData, deviceIds);
    }
  };

  const processTimeSeriesData = (devicesData, deviceIds) => {
    const datasets = [];

    devicesData.forEach((deviceData, index) => {
      if (!deviceData || !deviceData.readings) return;

      const deviceId = deviceIds[index];
      const color = deviceColors[index % deviceColors.length];
      
      const sortedReadings = [...deviceData.readings].sort(
        (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
      );

      datasets.push({
        label: `デバイス ${deviceId}`,
        data: sortedReadings.map(reading => ({
          x: new Date(reading.timestamp),
          y: reading.value
        })),
        borderColor: color,
        backgroundColor: color.replace('1)', '0.2)'),
        tension: 0.1
      });
    });

    setChartData({
      datasets
    });
  };

  const processComparisonData = (devicesData, deviceIds) => {
    const labels = deviceIds.map(id => `デバイス ${id}`);
    const data = devicesData.map(deviceData => {
      if (!deviceData || !deviceData.readings || deviceData.readings.length === 0) {
        return 0;
      }
      
      const latestReading = deviceData.readings.reduce(
        (latest, reading) => {
          const readingDate = new Date(reading.timestamp);
          const latestDate = new Date(latest.timestamp);
          return readingDate > latestDate ? reading : latest;
        },
        deviceData.readings[0]
      );
      
      return latestReading.value;
    });

    const backgroundColor = deviceIds.map((_, index) => 
      deviceColors[index % deviceColors.length].replace('1)', '0.2)')
    );
    
    const borderColor = deviceIds.map((_, index) => 
      deviceColors[index % deviceColors.length]
    );

    setChartData({
      labels,
      datasets: [{
        label: getMeasurementLabel(activeTab),
        data,
        backgroundColor,
        borderColor,
        borderWidth: 1
      }]
    });
  };

  const getMeasurementLabel = (type) => {
    const measurement = measurementTypes.find(m => m.id === type);
    return measurement ? measurement.label : type;
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
  };

  const handleChartTypeChange = (type) => {
    setChartType(type);
  };

  const getChartOptions = () => {
    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: `${getMeasurementLabel(activeTab)} データ`,
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y;
                
                if (activeTab === 'temperature') {
                  label += ' °C';
                } else if (activeTab === 'humidity') {
                  label += ' %';
                } else if (activeTab === 'pressure') {
                  label += ' hPa';
                }
              }
              return label;
            }
          }
        }
      },
    };

    if (chartType === 'timeSeries') {
      return {
        ...baseOptions,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour',
              displayFormats: {
                hour: 'MM/dd HH:mm'
              }
            },
            title: {
              display: true,
              text: '時間'
            }
          },
          y: {
            title: {
              display: true,
              text: getMeasurementUnitLabel(activeTab)
            }
          }
        }
      };
    } else {
      return {
        ...baseOptions,
        indexAxis: 'y',
        scales: {
          x: {
            title: {
              display: true,
              text: getMeasurementUnitLabel(activeTab)
            }
          }
        }
      };
    }
  };

  const getMeasurementUnitLabel = (type) => {
    switch (type) {
      case 'temperature':
        return '温度 (°C)';
      case 'humidity':
        return '湿度 (%)';
      case 'pressure':
        return '気圧 (hPa)';
      case 'gas':
        return 'ガス濃度';
      default:
        return type;
    }
  };

  if (loading) {
    return <div className="sensor-charts-loading">チャートデータを読み込み中...</div>;
  }

  if (error) {
    return <div className="sensor-charts-error">{error}</div>;
  }

  if (!deviceIds || deviceIds.length === 0) {
    return <div className="sensor-charts-empty">チャート表示用のデバイスが選択されていません。</div>;
  }

  return (
    <div className="sensor-charts-container">
      <div className="chart-controls">
        <div className="measurement-tabs">
          {measurementTypes.map(type => (
            <button
              key={type.id}
              className={`tab-button ${activeTab === type.id ? 'active' : ''}`}
              onClick={() => handleTabChange(type.id)}
            >
              {type.label}
            </button>
          ))}
        </div>
        
        <div className="chart-type-selector">
          {chartTypes.map(type => (
            <button
              key={type.id}
              className={`chart-type-button ${chartType === type.id ? 'active' : ''}`}
              onClick={() => handleChartTypeChange(type.id)}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>
      
      <div className="chart-container">
        {chartData.datasets && chartData.datasets.length > 0 ? (
          <Line data={chartData} options={getChartOptions()} />
        ) : (
          <div className="no-data-message">
            選択された期間とデバイスのデータがありません。
          </div>
        )}
      </div>
    </div>
  );
};

export default SensorCharts;
